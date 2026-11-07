"""ASI:One entry point and typed, allowlisted multi-uAgent calendar workflow.

Run python -m agent.coordinator --addresses before starting the Bureau.
"""
import argparse
import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
from uuid import uuid4

from dotenv import load_dotenv
from uagents import Agent, Bureau, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent, chat_protocol_spec,
)

from agent.builder import build
from agent.compat import ROOT, need, owner_control
from agent.explorer import explore
from agent.messages import Progress, Result, Work
from agent.verifier import verify

AGENT_DIR=Path(__file__).resolve().parent
ALLOW_TARGETS={'cal','today-run'}
COMMANDS={'status','rules','score','tests','start','reset','test'}
STAGE_TIMEOUTS={'explorer':30,'builder':180,'verifier':15}


def parse_command(text, address=None, name=None):
    words=text.strip().split()
    # ASI:One includes its routing mention in TextContent. Strip only our own
    # leading mention; arbitrary prefixes and target URLs remain invalid.
    mentions={f'@{value}' for value in (address,name) if value}
    if words and words[0].rstrip(':,') in mentions:
        words=words[1:]
    if len(words)==2 and words[0]=='rebuild':
        if words[1] not in ALLOW_TARGETS:return None,'Unknown target.'
        return ('rebuild',words[1]),None
    if len(words)==1 and words[0] in COMMANDS:return (words[0],None),None
    if words and words[0]=='rebuild':return None,'Unknown target.'
    return None,'Commands: rebuild cal, rebuild today-run, status, rules, score, tests.'


class RateLimit:
    def __init__(self, clock=time.monotonic):self.clock=clock;self.senders=OrderedDict()
    def allow(self,sender):
        now=self.clock();window=self.senders.setdefault(sender,deque())
        while window and window[0]<=now-60:window.popleft()
        self.senders.move_to_end(sender)
        if len(self.senders)>10000:self.senders.popitem(last=False)
        if len(window)>=10:return False
        window.append(now);return True


def format_report(snapshot, command='status'):
    if not snapshot:return 'No completed rebuild yet. Send: rebuild cal'
    if command=='rules':
        return '\n'.join(f'{"✓ seen" if rule.get("status")=="seen" else "? guessed"}: {rule.get("rule", "")}' for rule in snapshot.get('rules',[])) or 'No rules yet.'
    if command=='tests':
        results=snapshot.get('verification',{})
        return 'Held-out tests (independent):\n'+'\n'.join(f'Test {row["test"]}: {"PASS" if row["pass"] else "FAIL"}' for row in results.get('tests',[]))
    scores=snapshot.get('scores',[])
    climb=' → '.join(f'v{row.get("version")}: {row.get("train_pct")}% train'+(' (rejected)' if not row.get('kept',True) else '') for row in scores)
    verification=snapshot.get('verification',{})
    held=f'Independent held-out: {verification.get("match_pct", "unknown")}% ({verification.get("matched",0)}/{verification.get("total",0)}), '+('PASS' if verification.get('total',0)>0 and verification.get('matched')==verification.get('total') else 'FAIL')
    if command=='score':return (climb or 'No version scores.')+'\n'+held
    sections=['Clean Room: cal rebuild', 'STUB MODE — lookup-only plumbing; not an AI reconstruction.' if snapshot.get('stub') else 'Meta calendar reconstruction.',
              climb or 'No version scores.',held,format_report(snapshot,'rules'),
              'September 1752 (observed):\n'+snapshot.get('september_1752','Unavailable'),
              'The 1752 quirk may be known to the model; held-out tests are the evidence.']
    return '\n\n'.join(sections)


def chat_message(text, end=True):
    content=[TextContent(type='text',text=text)]
    if end:content.append(EndSessionContent(type='end-session'))
    return ChatMessage(timestamp=datetime.now(timezone.utc),msg_id=uuid4(),content=content)


class StageFailure(RuntimeError):
    def __init__(self,stage,last_good):
        self.stage=stage;self.last_good=last_good
        super().__init__(f'{stage} failed after timeout/one retry. Last good version: {last_good or "none"}.')


class Coordinator:
    def __init__(self, addresses, owner='', timeouts=None, address=None, name=None):
        self.address=address;self.name=name
        self.addresses=addresses;self.owner=owner;self.timeouts=timeouts or STAGE_TIMEOUTS
        self.snapshot={};self.events=[];self.last_good=None;self.busy=False
        self.rate=RateLimit();self.tasks=set();self.active_job=None
        self.seen_messages=OrderedDict()

    async def request(self,ctx,stage,payload):
        message=Work(job_id=self.active_job,stage=stage,payload=json.dumps(payload))
        for attempt in range(2):
            try:
                response,_=await asyncio.wait_for(
                    ctx.send_and_receive(self.addresses[stage],message,Result,timeout=self.timeouts[stage]),
                    timeout=self.timeouts[stage]+1,
                )
                if isinstance(response,Result) and response.job_id==message.job_id and response.stage==stage and response.ok:
                    return json.loads(response.payload)
            except Exception:
                pass
        raise StageFailure(stage,self.last_good)

    async def workflow(self,ctx):
        evidence=await self.request(ctx,'explorer',{'target':'cal'})
        # Held-out outputs are never included in the builder request.
        result=await self.request(ctx,'builder',{'train_lines':evidence['train_lines']})
        self.last_good=result['best_version']
        verification=await self.request(ctx,'verifier',{
            'code':result['code'],'held_out_lines':evidence['held_out_lines'],
            'train_tests':[row['test'] for row in evidence['train_lines']],
        })
        snapshot={key:value for key,value in result.items() if key!='code'}
        snapshot.update(scores=[event for event in result.pop('_events',self.events) if event.get('step')=='score'],
                        verification=verification,september_1752=evidence['september_1752'])
        self.snapshot=snapshot
        snapshot['status']='Completed cal rebuild: independently verified held-out dates.'
        folder=AGENT_DIR/'.runtime';folder.mkdir(exist_ok=True)
        temporary=folder/'snapshot.tmp'
        temporary.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False))
        temporary.replace(folder/'snapshot.json')
        return format_report(snapshot)

    async def finish(self,ctx,sender):
        try:
            text=await self.workflow(ctx)
        except StageFailure as error:
            text=str(error)
        except Exception as error:
            # Avoid leaking model exceptions, URLs, credentials, or raw code into chat.
            text=f'Workflow failed ({type(error).__name__}). Last good version: {self.last_good or "none"}.'
        finally:
            self.busy=False
        await ctx.send(sender,chat_message(text))

    async def handle_chat(self,ctx,sender,message):
        await ctx.send(sender,ChatAcknowledgement(timestamp=datetime.now(timezone.utc),acknowledged_msg_id=message.msg_id))
        message_key=(sender,str(message.msg_id))
        if message_key in self.seen_messages:return
        self.seen_messages[message_key]=None
        if len(self.seen_messages)>1000:self.seen_messages.popitem(last=False)
        if not self.rate.allow(sender):
            await ctx.send(sender,chat_message('Rate limit: at most 10 messages per minute.'));return
        text=' '.join(part.text for part in message.content if isinstance(part,TextContent))
        if len(text)>256:
            await ctx.send(sender,chat_message('Command too long.'));return
        parsed,error=parse_command(text,self.address,self.name)
        if error:
            await ctx.send(sender,chat_message(error));return
        command,target=parsed
        if command in {'start','reset','test'}:
            if not self.owner or sender!=self.owner:
                await ctx.send(sender,chat_message('Owner only.'));return
            if self.busy:
                await ctx.send(sender,chat_message('A rebuild is already running.'));return
            await ctx.send(sender,chat_message(owner_control(command)));return
        if command!='rebuild':
            text=('Rebuild running. Last good version: '+str(self.last_good or 'none')) if self.busy and command=='status' else format_report(self.snapshot,command)
            await ctx.send(sender,chat_message(text));return
        if target=='today-run':
            need('today-run saved-trace replay adapter')
            await ctx.send(sender,chat_message('NEED from teammate: today-run saved-trace replay adapter. No replay was performed.'));return
        if self.busy:
            await ctx.send(sender,chat_message('A rebuild is already running. Send status.'));return
        self.busy=True;self.events=[];self.active_job=str(uuid4())
        await ctx.send(sender,chat_message('Rebuilding cal: explorer → builder → independent verifier.',end=False))
        task=asyncio.create_task(self.finish(ctx,sender));self.tasks.add(task);task.add_done_callback(self.tasks.discard)

    async def progress(self,ctx,sender,message):
        if sender!=self.addresses['builder'] or message.job_id!=self.active_job:return
        try:event=json.loads(message.event)
        except ValueError:return
        if event.get('step') not in {'split','rules','score','done'}:return
        self.events.append(event)
        if event.get('step')=='score' and event.get('kept'):
            self.last_good=event.get('version',self.last_good)


@dataclass
class Runtime:
    bureau: Bureau
    agents: dict
    coordinator: Coordinator
    handlers: dict


def identity_seed():
    configured=os.environ.get('CLEANROOM_AGENT_SEED')
    if configured:return configured
    path=AGENT_DIR/'.identity.json'
    if not path.exists():
        try:
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'w') as stream:json.dump({'seed':secrets.token_urlsafe(48)},stream)
        except FileExistsError:pass
    return json.loads(path.read_text())['seed']


def make_runtime(seed=None, *, online=True, operations=None, timeouts=None):
    # SDK 0.26.1 has no host argument; keep its ASGI listener loopback-only.
    import uagents.asgi
    uagents.asgi.HOST='127.0.0.1'
    master=seed or identity_seed()
    roles=['coordinator','explorer','builder','verifier']
    agents={role:Agent(name=f'cleanroom-{role}-{hashlib.sha256(master.encode()).hexdigest()[:6]}',
                      seed=hashlib.sha256(f'{master}:{role}'.encode()).hexdigest(),
                      port=8001,mailbox=(online and role=='coordinator'),
                      publish_agent_details=(online and role=='coordinator'),
                      enable_agent_inspector=(role=='coordinator'),report_events=False)
            for role in roles}
    coordinator=Coordinator({role:agents[role].address for role in roles if role!='coordinator'},
                            owner=os.environ.get('OWNER_ADDRESS',''),timeouts=timeouts,
                            address=agents['coordinator'].address,name=agents['coordinator'].name)
    operations=operations or {'explorer':explore,'builder':build,'verifier':verify}
    handlers={}
    for role in roles[1:]:
        worker=agents[role];cache=OrderedDict()
        def register(role,worker,cache):
            @worker.on_message(model=Work,replies={Result,Progress})
            async def receive(ctx:Context,sender:str,message:Work):
                if sender!=agents['coordinator'].address or message.stage!=role:return
                cache_key=(message.job_id,message.stage)
                if cache_key in cache:
                    await ctx.send(sender,cache[cache_key]);return
                loop=asyncio.get_running_loop();event_tasks=[];collected=[]
                def on_event(event):
                    collected.append(event)
                    def deliver():
                        event_tasks.append(asyncio.create_task(ctx.send(sender,Progress(job_id=message.job_id,event=json.dumps(event)))))
                    loop.call_soon_threadsafe(deliver)
                try:
                    payload=json.loads(message.payload)
                    operation=operations[role]
                    result=await asyncio.to_thread(operation,payload,on_event) if role=='builder' else await asyncio.to_thread(operation,payload)
                    if role=='builder':result={**result,'_events':collected}
                    await asyncio.sleep(0)
                    if event_tasks:await asyncio.gather(*event_tasks,return_exceptions=True)
                    response=Result(job_id=message.job_id,stage=role,ok=True,payload=json.dumps(result))
                except Exception as error:
                    response=Result(job_id=message.job_id,stage=role,ok=False,error=type(error).__name__)
                # Failures can be retried; successful work is idempotent for a retry.
                if response.ok:
                    cache[cache_key]=response
                    if len(cache)>32:cache.popitem(last=False)
                await ctx.send(sender,response)
            handlers[role]=receive
        register(role,worker,cache)
    chat=Protocol(spec=chat_protocol_spec)
    @chat.on_message(model=ChatMessage)
    async def receive_chat(ctx:Context,sender:str,message:ChatMessage):
        await coordinator.handle_chat(ctx,sender,message)
    @chat.on_message(model=ChatAcknowledgement)
    async def receive_ack(ctx:Context,sender:str,message:ChatAcknowledgement):pass
    agents['coordinator'].include(chat,publish_manifest=online)
    agents['coordinator'].on_message(model=Progress)(coordinator.progress)
    @agents['coordinator'].on_message(model=Result)
    async def late_result(ctx:Context,sender:str,message:Result):pass
    handlers['coordinator']=receive_chat
    bureau=Bureau(agents=list(agents.values()),port=8001,network='mainnet')
    return Runtime(bureau,agents,coordinator,handlers)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--addresses',action='store_true',help='Print identities without registering or starting services')
    args=parser.parse_args()
    load_dotenv(ROOT/'.env')
    runtime=make_runtime()
    for role,agent in runtime.agents.items():print(f'{role}: {agent.name} {agent.address}',flush=True)
    address=runtime.agents['coordinator'].address
    print(f'Inspector: https://agentverse.ai/inspect/?uri=http%3A%2F%2F127.0.0.1%3A8001&address={address}',flush=True)
    if not args.addresses:runtime.bureau.run()


if __name__=='__main__':main()
