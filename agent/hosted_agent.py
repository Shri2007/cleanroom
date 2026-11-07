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

SNAPSHOT = {'status': 'Completed cal rebuild: independently verified held-out dates.',
 'rules': [{'id': 'R1',
            'rule': 'Header line is Month-name + year centered in 22-char field with trailing '
                    'spaces',
            'status': 'seen',
            'evidence_seq': [3]},
           {'id': 'R2',
            'rule': "Second line is always 'Su Mo Tu We Th Fr Sa  '",
            'status': 'seen',
            'evidence_seq': [3]},
           {'id': 'R3',
            'rule': 'Each day uses 3-char right-aligned column, weeks start Sunday',
            'status': 'seen',
            'evidence_seq': [3]},
           {'id': 'R4',
            'rule': 'Every line padded with trailing spaces to 22 chars',
            'status': 'seen',
            'evidence_seq': [1]},
           {'id': 'R5',
            'rule': 'Output is always 8 lines: header + weekday row + 6 week rows, blanks if '
                    'unused',
            'status': 'seen',
            'evidence_seq': [1]},
           {'id': 'R6',
            'rule': '31-day months: Jan, Mar, Aug, Oct, Dec show 1-31',
            'status': 'seen',
            'evidence_seq': [3]},
           {'id': 'R7',
            'rule': '30-day months: Apr, Jun, Nov show 1-30',
            'status': 'seen',
            'evidence_seq': [16]},
           {'id': 'R8',
            'rule': 'February has 29 days in 1752, 2024, 1600 and 28 days in 1800, 2100',
            'status': 'seen',
            'evidence_seq': [2]},
           {'id': 'R9',
            'rule': 'Century leap rule: 1600 leap but 1800 and 2100 not leap',
            'status': 'seen',
            'evidence_seq': [22]},
           {'id': 'R10',
            'rule': 'Start weekday varies, e.g. Jan 1752 Wed, Nov 2026 Sun, Aug 2026 Sat',
            'status': 'seen',
            'evidence_seq': [3]},
           {'id': 'R11',
            'rule': 'September 1752 skips 3-13, goes 1 2 then 14-30',
            'status': 'seen',
            'evidence_seq': [1]}],
 'scores': [{'step': 'score',
             'version': 2,
             'train_pct': 38.1,
             'held_pct': None,
             'kept': True,
             'brain': 'meta',
             'error': None},
            {'step': 'score',
             'version': 3,
             'train_pct': 100,
             'held_pct': None,
             'kept': True,
             'brain': 'meta',
             'error': None}],
 'verification': {'match_pct': 100,
                  'matched': 9,
                  'total': 9,
                  'tests': [{'test': 5, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 6, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 7, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 8, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 9, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 10, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 11, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 12, 'lines': 1, 'matched': 1, 'pass': True},
                            {'test': 13, 'lines': 1, 'matched': 1, 'pass': True}]},
 'stub': False,
 'brain_backend': 'server.brain.run_cal',
 'best_version': 3,
 'held_out_dates': {'5': [9, 1700],
                    '6': [2, 1700],
                    '7': [9, 1751],
                    '8': [2, 1751],
                    '9': [9, 1753],
                    '10': [2, 1753],
                    '11': [2, 1900],
                    '12': [2, 2000],
                    '13': [2, 2023]},
 'recorded_at': '2026-11-07T21:28:44.467976+00:00',
 'september_1752': '   September 1752     \n'
                   'Su Mo Tu We Th Fr Sa  \n'
                   '       1  2 14 15 16  \n'
                   '17 18 19 20 21 22 23  \n'
                   '24 25 26 27 28 29 30  \n'
                   '                      \n'
                   '                      \n'
                   '                      '}


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
