"""Real-brain local uAgent round-trip; explicitly NOT an ASI:One transcript.

Uses real calendar observations, real server.brain.run_cal and independent checker.
Run python -m agent.smoke; artifacts stay inside ignored agent/.runtime/.
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import secrets

from dotenv import load_dotenv
from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, EndSessionContent

from agent.compat import ROOT
from agent.coordinator import AGENT_DIR, chat_message, identity_seed, make_runtime


async def main():
    load_dotenv(ROOT/'.env')
    runtime=make_runtime(seed=identity_seed(),online=False)
    runtime.coordinator.artifacts=AGENT_DIR/'.runtime'/('local-real-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    client=Agent(name='cleanroom-local-verifier',seed=secrets.token_urlsafe(48),report_events=False,publish_agent_details=False)
    replies=asyncio.Queue()
    @client.on_message(model=ChatMessage)
    async def receive(ctx:Context,sender:str,message:ChatMessage):
        if sender==runtime.agents['coordinator'].address and any(isinstance(item,EndSessionContent) for item in message.content):
            await replies.put('\n'.join(item.text for item in message.content if hasattr(item,'text')))
    @client.on_message(model=ChatAcknowledgement)
    async def acknowledge(ctx:Context,sender:str,message:ChatAcknowledgement):pass
    agents=[*runtime.agents.values(),client]
    tasks_before=set(asyncio.all_tasks())
    try:
        for agent in agents:
            agent.include(agent._protocol)
            agent.start_message_dispenser()
            agent.start_message_receivers()
        address=runtime.agents['coordinator'].address
        for command in ['rebuild cal','status','rules','score','tests','rebuild unknown']:
            print('LOCAL USER:',command,flush=True)
            await client._build_context().send(address,chat_message('@'+address+' '+command))
            response=await asyncio.wait_for(replies.get(),timeout=420)
            print('LOCAL AGENT:\n'+response,flush=True)
            if command=='rebuild cal':
                snapshot=runtime.coordinator.snapshot
                if snapshot.get('stub') or snapshot.get('brain_backend')!='server.brain.run_cal':
                    raise RuntimeError('Real brain rebuild did not finish; see transcript above')
            if command=='rebuild unknown' and response!='Unknown target.':
                raise AssertionError('Unknown target contract failed')
        print('LOCAL REAL SMOKE PASSED. Not an ASI:One chat.',flush=True)
        print('Artifacts:',runtime.coordinator.artifacts,flush=True)
    finally:
        tasks=set(asyncio.all_tasks())-tasks_before
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)


if __name__=='__main__':asyncio.run(main())
