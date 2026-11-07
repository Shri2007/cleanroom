"""Paste this entire file into Agentverse's hosted-agent editor at the freeze.

Agentverse supplies `agent`. Locally, require CLEANROOM_HOSTED_SEED before running.
Paste actual completed results into SNAPSHOT; never paste API keys or code.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
import os
import time
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent, chat_protocol_spec,
)

SNAPSHOT = {
    'status': 'No verified result has been pasted at the freeze yet.',
    'rules': [],
    'scores': [],
    'verification': {'match_pct': None, 'matched': 0, 'total': 0, 'tests': []},
    'stub': False,
}


def snapshot_reply(text, snapshot=None, address=None, name=None):
    data=SNAPSHOT if snapshot is None else snapshot
    words=text.strip().split()
    if words and words[0].rstrip(':,') in {f'@{value}' for value in (address,name) if value}:
        words=words[1:]
    command=' '.join(words)
    if command not in {'status','rules','score','tests'}:
        return 'Read-only snapshot. Commands: status, rules, score, tests.'
    if command=='status':
        return data.get('status','Frozen results snapshot.')+(' STUB MODE.' if data.get('stub') else '')
    if command=='rules':
        return '\n'.join(f'{"✓ seen" if rule.get("status")=="seen" else "? guessed"}: {rule.get("rule", "")}' for rule in data.get('rules',[])) or 'No frozen rules.'
    if command=='tests':
        tests=data.get('verification',{}).get('tests',[])
        return '\n'.join(f'Test {row["test"]}: {"PASS" if row["pass"] else "FAIL"}' for row in tests) or 'No frozen held-out tests.'
    scores=data.get('scores',[])
    climb=' → '.join(f'v{row.get("version")}: {row.get("train_pct")}% train'+(' (rejected)' if not row.get('kept',True) else '') for row in scores)
    held=data.get('verification',{})
    return (climb or 'No frozen scores.')+f'\nIndependent held-out: {held.get("match_pct")}% ({held.get("matched",0)}/{held.get("total",0)}).'+(' STUB MODE.' if data.get('stub') else '')


def install(hosted):
    protocol=Protocol(spec=chat_protocol_spec)
    windows=defaultdict(deque)
    @protocol.on_message(model=ChatMessage)
    async def message(ctx:Context,sender:str,msg:ChatMessage):
        await ctx.send(sender,ChatAcknowledgement(timestamp=datetime.now(timezone.utc),acknowledged_msg_id=msg.msg_id))
        now=time.monotonic();window=windows[sender]
        while window and window[0]<=now-60:window.popleft()
        if len(window)>=10:
            text='Rate limit: at most 10 messages per minute.'
        else:
            window.append(now)
            text=snapshot_reply(' '.join(part.text for part in msg.content if isinstance(part,TextContent)),address=hosted.address,name=hosted.name)
        await ctx.send(sender,ChatMessage(timestamp=datetime.now(timezone.utc),msg_id=uuid4(),
                                         content=[TextContent(type='text',text=text),EndSessionContent(type='end-session')]))
    @protocol.on_message(model=ChatAcknowledgement)
    async def acknowledgement(ctx:Context,sender:str,msg:ChatAcknowledgement):pass
    hosted.include(protocol,publish_manifest=True)
    return hosted


if 'agent' in globals():
    install(agent)
elif __name__=='__main__':
    seed=os.environ.get('CLEANROOM_HOSTED_SEED')
    if not seed:raise SystemExit('Set a unique CLEANROOM_HOSTED_SEED (never commit it).')
    hosted=install(Agent(name='cleanroom-frozen-results',seed=seed,mailbox=True,publish_agent_details=True,port=8002))
    print(f'{hosted.name}: {hosted.address}')
    hosted.run()
