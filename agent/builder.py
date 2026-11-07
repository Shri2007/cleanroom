"""Build with the real teammate calendar brain; stub is never selected implicitly."""
import json
import re

from agent.compat import ROOT, check_cal, function, need


def stub_builder(lines, on_event):
    """Real replay scores, not a learned controller or independent reconstruction."""
    need('server.brain.run_cal(lines, on_event); using the labeled lookup-only builder stub')
    rules = [{'id':'calendar-1752','rule':'September 1752 output jumps from 2 to 14.',
              'status':'seen','evidence_seq':[row['seq'] for row in lines if row['args']==[9,1752]]}]
    september = next((row['output'] for row in lines if row['args']==[9,1752]), '')
    days=[int(word) for word in september.split() if word.isdigit()][1:]
    if not (2 in days and 14 in days and all(day not in days for day in range(3,14))):
        rules[0].update(rule='The calendar boundary rule needs more evidence.',status='guessed',evidence_seq=[])
    on_event({'step':'split','train_tests':[row['test'] for row in lines], 'held_tests':[]})
    on_event({'step':'rules','rules':rules})
    for version, evidence in [(1,lines[:10]),(2,lines)]:
        table={f'{row["args"][0]}:{row["args"][1]}':row['output'] for row in evidence}
        code='globalThis.Cal={run(month,year){const rows='+json.dumps(table)+';return rows[month+":"+year]??"";}};'
        score=check_cal(code,lines,[row['test'] for row in lines])
        on_event({'step':'score','version':version,'train_pct':score['match_pct'],
                  'held_pct':None,'kept':True,'stub':True})
    result={'best_version':2,'train_pct':score['match_pct'],'held_pct':None,
            'rules':rules,'code':code,'stub':True}
    on_event({'step':'done',**{key:value for key,value in result.items() if key!='code'}})
    return result


def build(payload, on_event):
    lines=payload['train_lines']
    runner=function('server.brain','run_cal')
    if runner is None:
        need('server.brain.run_cal(lines, on_event) is unavailable; restart after it lands')
        raise RuntimeError('Real calendar brain unavailable; stub mode is disabled')
    print('Builder backend: server.brain.run_cal (real)',flush=True)
    result=runner(lines,on_event)
    if not isinstance(result,dict):raise ValueError('Brain returned an invalid result')
    if not {'best_version','train_pct','held_pct','rules'} <= result.keys():
        raise ValueError('Brain result must include best_version, train_pct, held_pct, rules')
    code=result.get('code')
    if code is None:
        match=re.fullmatch(r'(?:cal_)?v?(\d+)(?:\.js)?',str(result['best_version']))
        if not match:raise ValueError('Brain returned an invalid calendar version')
        path=ROOT/'copies'/f'cal_v{int(match.group(1))}.js'
        code=path.read_text()
    if not isinstance(code,str) or not code.strip():raise ValueError('No final copy source')
    if not isinstance(result['rules'],list):raise ValueError('Brain rules must be a list')
    result['stub']=False
    result['brain_backend']='server.brain.run_cal'
    result['code']=code
    return result
