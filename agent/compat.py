"""Temporary adapters live here; teammate-owned modules are imported, never edited."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ANNOUNCED = set()


def need(message):
    if message not in ANNOUNCED:
        print(f'NEED from Shri: {message}', flush=True)
        ANNOUNCED.add(message)


def function(module_name, name):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        return None
    candidate = getattr(module, name, None)
    return candidate if callable(candidate) else None


def calendar(dates):
    for month, year in dates:
        if type(month) is not int or type(year) is not int or not 1 <= month <= 12 or not 1 <= year <= 9999:
            raise ValueError('Invalid calendar date')
    runner = function('explorer.cal_runner', 'run')
    if runner:
        return runner(dates)
    trace_runner = function('explorer.cal_runner', 'trace_lines')
    if trace_runner:
        rows = trace_runner(dates)
        if len(rows) != len(dates):raise ValueError('Calendar runner returned wrong row count')
        canonical = []
        for seq, (row, date) in enumerate(zip(rows, dates), 1):
            if row.get('suspect') or not isinstance(row.get('display'), str):
                raise ValueError('Calendar target read failed')
            canonical.append(dict(seq=seq, test=seq, source='text', args=list(date),
                                  output=row['display'], deleted=False))
        return canonical
    need('explorer.cal_runner.run(dates) -> list[dict]; using the agent-local calendar adapter')
    rows = []
    for seq, (month, year) in enumerate(dates, 1):
        process = subprocess.run(['/usr/bin/cal', str(month), str(year)], capture_output=True,
                                 text=True, timeout=5, check=True,
                                 env={'PATH': os.environ.get('PATH', '')})
        rows.append(dict(seq=seq, test=seq, source='text', args=[month, year],
                         output=process.stdout, deleted=False))
    return rows


def check_cal(code, lines, tests):
    runner = function('server.checker', 'run')
    if runner:
        result = runner('cal', code, lines, tests)
    elif function('server.checker', 'check'):
        # Adapt to Ali's path-based API without editing checker/ or copies/.
        folder = ROOT / 'agent' / '.runtime'
        folder.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='verify-', dir=folder) as temporary:
            path = Path(temporary)
            copy = path / 'candidate.js'
            trace = path / 'held-out.jsonl'
            bridge = '\nif (globalThis.Cal && typeof globalThis.Cal.run === "function") { module.exports = (month,year) => globalThis.Cal.run(month,year); }\n'
            copy.write_text(code + bridge)
            legacy = [dict(seq=row['seq'],test=row['test'],source='cal',
                           key=f"{row['args'][0]} {row['args'][1]}",display=row['output'],
                           suspect=False,deleted=row.get('deleted',False)) for row in lines]
            trace.write_text(''.join(json.dumps(row)+'\n' for row in legacy))
            result = function('server.checker','check')(copy, trace, tests=tests, mode='cal')
        for row in result.get('tests',[]):
            if 'pass' not in row:row['pass'] = row.get('lines',0)>0 and row.get('matched')==row['lines']
    else:
        need('server.checker.run("cal", code, lines, tests); using the agent-local isolated checker')
        process = subprocess.run(
            # read only the checker script: agent/ also holds .identity.json (the agent's key)
            ['node', '--permission', f'--allow-fs-read={ROOT / "agent/check_cal.mjs"}', str(ROOT / 'agent/check_cal.mjs')],
            input=json.dumps({'code': code, 'lines': lines, 'tests': tests}),
            capture_output=True, text=True, timeout=2,
            env={'PATH': os.environ.get('PATH', '')}, check=True,
        )
        result = json.loads(process.stdout)
    if not isinstance(result, dict) or 'error' in result or 'match_pct' not in result:
        raise RuntimeError('Calendar checker failed')
    return result


def owner_control(command):
    message = 'fixed owner-control adapter for start/reset/test (no backend control was performed)'
    need(message)
    return 'NEED from teammate: ' + message
