"""Independent held-out scorer. No expected outputs are sent to the builder."""
from agent.compat import check_cal


def verify(payload):
    rows=payload['held_out_lines']
    if not rows:raise ValueError('Independent verification needs held-out dates')
    training=set(payload['train_tests'])
    if any(row['test'] in training for row in rows):raise ValueError('Held-out test IDs overlap training')
    result=check_cal(payload['code'],rows,[row['test'] for row in rows])
    if result.get('total',0)!=len([row for row in rows if not row.get('deleted')]):
        raise ValueError('Verifier did not score every held-out date')
    return {key:result.get(key) for key in ('match_pct','matched','total','tests','mismatches')}
