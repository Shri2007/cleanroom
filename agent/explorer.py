"""Collect ~30 calendar observations; never expose held-out rows to the builder."""
import json
import os
import random

from agent.compat import calendar

FIXED_DATES = [
    (9,1752),(2,1752),(1,1752),(12,1752),(9,1700),(2,1700),
    (9,1751),(2,1751),(9,1753),(2,1753),(2,1900),(2,2000),
    (2,2023),(2,2024),(1,2026),(4,2026),(6,2026),(11,2026),
    (12,1999),(1,2000),(3,2000),(2,1600),(2,1800),(2,2100),
    (7,1969),(8,2026),(10,2026),(3,1752),(8,1752),(10,1752),
]
HELD_DATES = {(9,1700),(2,1700),(9,1751),(2,1751),(9,1753),(2,1753),
              (2,1900),(2,2000),(2,2023)}


def pick_dates():
    """SubQ is optional and receives no chat text, credentials, or held-out outputs."""
    if not all(os.environ.get(key) for key in ('SUBQ_API_KEY','SUBQ_BASE_URL','SUBQ_MODEL')):
        return list(FIXED_DATES)
    from openai import OpenAI
    client = OpenAI(api_key=os.environ['SUBQ_API_KEY'], base_url=os.environ['SUBQ_BASE_URL'],
                    timeout=8, max_retries=1)
    try:
        response = client.chat.completions.create(
            model=os.environ['SUBQ_MODEL'], max_tokens=300,
            messages=[{'role':'system','content':'Return JSON only: {"dates": [[month,year], ...]}. '
                       'Propose 20 varied calendar dates, months 1..12 and years 1..9999; include leap and non-leap Februaries.'},
                      {'role':'user','content':'Select calendar test inputs.'}],
        )
        proposed = json.loads(response.choices[0].message.content)['dates']
        if not isinstance(proposed,list):
            raise ValueError('Expected date list')
        dates = [(9,1752), *sorted(HELD_DATES)]
        for pair in proposed + FIXED_DATES:
            if not isinstance(pair,(list,tuple)) or len(pair)!=2:
                continue
            month, year = pair
            if type(month) is int and type(year) is int and 1<=month<=12 and 1<=year<=9999:
                date=(month,year)
                if date not in dates:dates.append(date)
            if len(dates)==30:break
        return dates
    except Exception:
        # Never log client exceptions: they can contain credential-bearing URLs.
        return list(FIXED_DATES)


def explore(payload):
    if payload.get('target') != 'cal':
        raise RuntimeError('NEED from teammate: today-run saved-trace replay adapter')
    rows = calendar(pick_dates())
    if len(rows)<20:
        raise ValueError('Too few calendar observations')
    train, held = [], []
    for row in rows:
        if set(row) != {'seq','test','source','args','output','deleted'} or row['source']!='text':
            raise ValueError('Calendar runner returned an invalid trace row')
        if not isinstance(row['output'],str):raise ValueError('Calendar output must be exact text')
        (held if tuple(row['args']) in HELD_DATES else train).append(row)
    if len(held)!=9 or not any(row['args']==[9,1752] for row in train):
        raise ValueError('Missing calendar boundary evidence')
    if len({row['test'] for row in rows})!=len(rows):raise ValueError('Tests must have unique IDs')
    return {'train_lines':train,'held_out_lines':held,
            'september_1752':next(row['output'] for row in train if row['args']==[9,1752])}
