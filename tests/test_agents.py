"""Exercise the real uAgent handlers with a local typed-message transport.

No model calls, credentials, registration, camera access, or external messages.
"""
import asyncio
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timezone

from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, TextContent
from agent.builder import build, stub_builder
from agent.coordinator import Coordinator, RateLimit, StageFailure, chat_message, make_runtime, parse_command
from agent.explorer import FIXED_DATES, HELD_DATES, explore
from agent.hosted_agent import snapshot_reply
from agent.messages import Progress, Result, Work
from agent.verifier import verify


class Transport:
    """Dispatch typed Work through the same handlers registered on real Agents."""
    def __init__(self,runtime):self.runtime=runtime;self.sent=[];self.calls=[]
    def context(self,role):
        transport=self
        class Context:
            async def send(self,destination,message):
                transport.sent.append((role,destination,message))
                if isinstance(message,Progress):
                    await transport.runtime.coordinator.progress(transport.context('coordinator'),transport.runtime.agents[role].address,message)
            async def send_and_receive(self,destination,message,response_type,timeout):
                worker=next(role for role,agent in transport.runtime.agents.items() if agent.address==destination)
                transport.calls.append((worker,json.loads(message.payload)))
                before=len(transport.sent)
                await transport.runtime.handlers[worker](transport.context(worker),transport.runtime.agents['coordinator'].address,message)
                responses=[msg for _,_,msg in transport.sent[before:] if isinstance(msg,Result)]
                return (responses[-1] if responses else None),None
        return Context()


class CommandTests(unittest.TestCase):
    def test_allowlist_injection_and_arity(self):
        for text in ['rebuild https://evil.example','rebuild cal;id','rebuild mac-calc','rebuild lander','rebuild cal extra']:
            self.assertEqual(parse_command(text)[1],'Unknown target.')
        self.assertEqual(parse_command('rebuild cal')[0],('rebuild','cal'))
        self.assertEqual(parse_command('rebuild today-run')[0],('rebuild','today-run'))
        self.assertIsNone(parse_command('reset now')[0])

    def test_rate_window_boundary(self):
        now=[0];limiter=RateLimit(lambda:now[0])
        self.assertTrue(all(limiter.allow('sender') for _ in range(10)))
        self.assertFalse(limiter.allow('sender'))
        self.assertTrue(limiter.allow('other'))
        now[0]=60;self.assertTrue(limiter.allow('sender'))

    def test_snapshot_is_readonly_and_honest(self):
        self.assertIn('Read-only',snapshot_reply('rebuild cal'))
        self.assertIn('No verified',snapshot_reply('status'))
        self.assertIn('No frozen',snapshot_reply('tests'))


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix='cleanroom-agent-test-')
        self.addCleanup(self.folder.cleanup)
        directory=patch('agent.coordinator.AGENT_DIR',Path(self.folder.name))
        directory.start();self.addCleanup(directory.stop)
        self.runtime=make_runtime(seed='unit-test-only-never-use-this-seed-online',online=False)
        self.transport=Transport(self.runtime);self.ctx=self.transport.context('coordinator')

    async def test_cal_pipeline_scores_real_stub_and_keeps_held_out_private(self):
        # Force the documented temporary adapters even if teammate interfaces land later.
        import agent.compat
        def functions(module,name):return None
        with patch('agent.compat.function',side_effect=functions),patch('agent.builder.function',return_value=None),patch.dict('os.environ',{'SUBQ_API_KEY':''}):
            await self.runtime.coordinator.handle_chat(self.ctx,'user',chat_message('rebuild cal'))
            await asyncio.gather(*list(self.runtime.coordinator.tasks))
        snapshot=self.runtime.coordinator.snapshot
        self.assertTrue(snapshot['stub'])
        self.assertEqual([event['train_pct'] for event in snapshot['scores']],[47.62,100])
        self.assertEqual(snapshot['verification']['match_pct'],0)
        self.assertEqual(snapshot['verification']['total'],9)
        builder_payload=next(payload for role,payload in self.transport.calls if role=='builder')
        self.assertEqual(set(builder_payload),{'train_lines'})
        self.assertTrue(all(tuple(row['args']) not in HELD_DATES for row in builder_payload['train_lines']))
        chat=[message for _,_,message in self.transport.sent if isinstance(message,ChatMessage)]
        text=chat[-1].content[0].text
        self.assertIn('STUB MODE',text);self.assertIn('47.62%',text);self.assertIn('1752',text);self.assertIn('FAIL',text)
        self.assertEqual([role for role,_ in self.transport.calls],['explorer','builder','verifier'])
        self.assertTrue(any(isinstance(msg,ChatAcknowledgement) for _,_,msg in self.transport.sent))

    async def test_owner_commands_and_invalid_target_never_dispatch(self):
        self.runtime.coordinator.owner='owner'
        for command in ['start','reset','test','rebuild https://evil.example']:
            await self.runtime.coordinator.handle_chat(self.ctx,'stranger',chat_message(command))
        self.assertEqual(self.transport.calls,[])
        replies=[msg.content[0].text for _,_,msg in self.transport.sent if isinstance(msg,ChatMessage)]
        self.assertEqual(replies[:3],['Owner only.']*3)
        self.assertEqual(replies[-1],'Unknown target.')
        with patch('agent.coordinator.owner_control',return_value='owner adapter requested') as control:
            await self.runtime.coordinator.handle_chat(self.ctx,'owner',chat_message('start'))
            control.assert_called_once_with('start')

    async def test_retry_failure_names_stage_and_last_good(self):
        state=Coordinator({'builder':'destination'},timeouts={'builder':.01});state.active_job='job';state.last_good=2
        class Dead:
            count=0
            async def send_and_receive(self,*args,**kwargs):self.count+=1;return None,None
        ctx=Dead()
        with self.assertRaises(StageFailure) as error:await state.request(ctx,'builder',{})
        self.assertEqual(ctx.count,2);self.assertIn('builder',str(error.exception));self.assertIn('2',str(error.exception))

    async def test_retry_success_and_duplicate_work_is_idempotent(self):
        count=[0]
        def explore_stub(payload):count[0]+=1;return {'ok':'yes'}
        runtime=make_runtime(seed='another-unit-test-seed',online=False,operations={'explorer':explore_stub,'builder':build,'verifier':verify})
        transport=Transport(runtime);ctx=transport.context('coordinator');runtime.coordinator.active_job='same-job'
        first=await runtime.coordinator.request(ctx,'explorer',{'target':'cal'})
        second=await runtime.coordinator.request(ctx,'explorer',{'target':'cal'})
        self.assertEqual(first,second);self.assertEqual(count[0],1)

    async def test_replay_message_is_not_executed_twice(self):
        message=chat_message('rebuild today-run')
        await self.runtime.coordinator.handle_chat(self.ctx,'user',message)
        await self.runtime.coordinator.handle_chat(self.ctx,'user',message)
        replies=[msg for _,_,msg in self.transport.sent if isinstance(msg,ChatMessage)]
        self.assertEqual(len(replies),1)

    async def test_builder_uses_real_interface_when_present(self):
        seen=[]
        def brain(lines,on_event):
            seen.extend(lines)
            return {'best_version':1,'train_pct':0,'held_pct':None,'rules':[],
                    'code':'globalThis.Cal={run(){return ""}};'}
        with patch('agent.builder.function',return_value=brain):
            result=build({'train_lines':[{'test':1}]},lambda event:None)
        self.assertEqual(seen,[{'test':1}]);self.assertFalse(result.get('stub',False))

    async def test_sdk_dispatch_without_external_registration(self):
        before=set(asyncio.all_tasks())
        for agent in self.runtime.agents.values():
            agent.include(agent._protocol)
            agent.start_message_dispenser()
            agent.start_message_receivers()
        self.runtime.coordinator.active_job='real-sdk-local-dispatch'
        try:
            with patch('agent.compat.function',return_value=None),patch('agent.builder.function',return_value=None),patch.dict('os.environ',{'SUBQ_API_KEY':''}):
                report=await asyncio.wait_for(self.runtime.coordinator.workflow(self.runtime.agents['coordinator']._build_context()),timeout=30)
            self.assertIn('STUB MODE',report)
            self.assertEqual(self.runtime.coordinator.snapshot['verification']['total'],9)
        finally:
            tasks=set(asyncio.all_tasks())-before
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)

    async def test_worker_ignores_untrusted_sender(self):
        message=Work(job_id='injection',stage='explorer',payload='{"target":"cal"}')
        await self.runtime.handlers['explorer'](self.transport.context('explorer'),'stranger',message)
        self.assertEqual(self.transport.sent,[])

    async def test_retry_succeeds_on_second_response(self):
        state=Coordinator({'explorer':'destination'},timeouts={'explorer':.01});state.active_job='job'
        class Flaky:
            count=0
            async def send_and_receive(self,destination,message,response_type,timeout):
                self.count+=1
                if self.count==1:return None,None
                return Result(job_id='job',stage='explorer',ok=True,payload='{"ok":true}'),None
        ctx=Flaky()
        self.assertTrue((await state.request(ctx,'explorer',{}))['ok']);self.assertEqual(ctx.count,2)

    async def test_verifier_rejects_overlap(self):
        with self.assertRaisesRegex(ValueError,'overlap'):
            verify({'code':'','held_out_lines':[{'test':1}], 'train_tests':[1]})


if __name__=='__main__':unittest.main()
