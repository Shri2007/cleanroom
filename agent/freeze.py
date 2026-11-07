"""Fill the standalone hosted source from a measured real-agent snapshot.

Usage: python -m agent.freeze agent/.runtime/.../snapshot.json
No deployment, model calls, or files outside agent/ are changed.
"""
import argparse
import ast
import json
from pathlib import Path
import pprint

from agent.coordinator import AGENT_DIR


def freeze(snapshot_path):
    path=Path(snapshot_path).resolve()
    if not path.is_relative_to(AGENT_DIR.resolve()):raise ValueError('Snapshot must be inside agent/')
    snapshot=json.loads(path.read_text())
    if snapshot.get('stub') or snapshot.get('brain_backend')!='server.brain.run_cal':
        raise ValueError('Refusing to publish a stub or unverified backend result')
    if not snapshot.get('verification',{}).get('total') or not snapshot.get('scores'):
        raise ValueError('Snapshot needs measured scores and independent held-out tests')
    allowed=('status','rules','scores','verification','stub','brain_backend','best_version',
             'held_out_dates','recorded_at','september_1752')
    frozen={key:snapshot[key] for key in allowed if key in snapshot}
    # Detailed mismatches are unnecessary for public read-only chat replies.
    frozen['verification']={key:value for key,value in frozen['verification'].items() if key!='mismatches'}
    source_path=AGENT_DIR/'hosted_agent.py'
    source=source_path.read_text();lines=source.splitlines(keepends=True)
    assignment=next(node for node in ast.parse(source).body if isinstance(node,ast.Assign)
                    and any(isinstance(target,ast.Name) and target.id=='SNAPSHOT' for target in node.targets))
    replacement='SNAPSHOT = '+pprint.pformat(frozen,width=100,sort_dicts=False)+'\n'
    source_path.write_text(''.join(lines[:assignment.lineno-1])+replacement+''.join(lines[assignment.end_lineno:]))
    ast.parse(source_path.read_text())
    print('Filled agent/hosted_agent.py from real recorded result; no deployment performed.')
    print('NEED from Shri: deploy the prepared hosted_agent.py in the Agentverse hosted editor; browser control is unavailable here.')
    return frozen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path)
    freeze(parser.parse_args().snapshot)


if __name__=='__main__':main()
