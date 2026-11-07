"""Runs checker/check.mjs on a copy, train vs held-out (Ali).

    python -m server.checker <copy.js> [trace.jsonl]

`check()` scores a copy against a trace. `check_split()` scores it on the train tests
and on held-out tests separately, so a copy that only memorised the lines it was shown
shows up as a gap between the two numbers.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_MJS = ROOT / "checker" / "check.mjs"
DEFAULT_TRACE = ROOT / "traces" / "sample.jsonl"
TIMEOUT_SECONDS = 10  # whole run; each call into the copy has its own 500 ms limit


class CheckerError(RuntimeError):
    pass


def test_ids(trace_path):
    """Test numbers present in a trace, ignoring deleted lines."""
    ids = set()
    for line in Path(trace_path).read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if not row.get("deleted"):
                ids.add(row["test"])
    return sorted(ids)


def check(copy_path, trace_path=DEFAULT_TRACE, tests=None, mode=None):
    """Run a copy against a trace. Returns the report dict from check.mjs.

    `tests` limits the run to those test numbers (None = all). `mode` is "calc" or "cal";
    None picks it from the trace (all lines source "cal" -> cal). match_pct is a
    percentage 0-100, or None when no lines were compared.
    """
    copy_path, trace_path = Path(copy_path).resolve(), Path(trace_path).resolve()
    # The copy is AI-written code. Node's permission model lets the process read only the
    # checker, the copy and the trace (no writes, no child processes), and it gets no
    # environment except PATH, so API keys are never visible even if the vm is escaped.
    cmd = ["node", "--permission",
           f"--allow-fs-read={CHECK_MJS.parent}", f"--allow-fs-read={copy_path}", f"--allow-fs-read={trace_path}",
           str(CHECK_MJS), str(copy_path), str(trace_path)]
    if tests is not None:
        cmd += ["--tests", ",".join(str(t) for t in tests)]
    if mode is not None:
        cmd += ["--mode", mode]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                              env={"PATH": os.environ.get("PATH", "")})
    except subprocess.TimeoutExpired:
        raise CheckerError(f"checker timed out after {TIMEOUT_SECONDS}s (copy hangs?)")
    except FileNotFoundError:
        raise CheckerError("node is not installed or not on PATH")
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise CheckerError(f"checker gave no report: {proc.stderr.strip() or proc.stdout.strip()}")
    if proc.returncode != 0:
        raise CheckerError(report.get("error", "checker failed"))
    return report


MAX_CODE_CHARS = 200_000
MAX_LINES = 5_000
JOB_TIMEOUT_SECONDS = 12  # JS stops scoring after 8 s, so this only catches a stuck node


def run(target, code, lines, tests=None):
    """Score a copy given as source text. This is what server/brain.py and agent/ call.

    target "calc": `code` defines globalThis.Calc = {reset(), press(key), render()}; `lines` are
                   calculator trace lines (key, display, ...). Null fields are not compared.
    target "cal":  `code` defines globalThis.Cal = {run(month, year)}; `lines` are
                   {seq, test, args: [month, year], output, deleted}. Output must match exactly.
    `tests` limits scoring to those test numbers (None = all). Deleted and suspect lines are skipped.

    Returns {match_pct, matched, total, skipped, tests: [{test, pass}], mismatches}. A copy that
    fails to load or crashes is scored 0 on the lines it breaks, not raised. If the checker itself
    cannot run, the result is {error, match_pct: 0, mismatches: []} so callers never crash on it.
    Raises ValueError only for a call that can never work (unknown target, oversized input).
    """
    if target not in ("calc", "cal"):
        raise ValueError(f"unknown target {target!r}")
    if not isinstance(code, str) or len(code) > MAX_CODE_CHARS:
        raise ValueError(f"code must be a string of at most {MAX_CODE_CHARS} characters")
    if len(lines) > MAX_LINES:
        raise ValueError(f"at most {MAX_LINES} lines per run")
    job = json.dumps({"target": target, "code": code, "lines": lines,
                      "tests": None if tests is None else list(tests)}, ensure_ascii=False)
    # Same lockdown as check(): read-only access to the checker itself, PATH-only environment.
    cmd = ["node", "--permission", f"--allow-fs-read={CHECK_MJS.parent}", str(CHECK_MJS), "--job"]
    try:
        proc = subprocess.run(cmd, input=job, capture_output=True, text=True,
                              timeout=JOB_TIMEOUT_SECONDS, env={"PATH": os.environ.get("PATH", "")})
    except subprocess.TimeoutExpired:
        return {"error": "checker timed out", "match_pct": 0, "mismatches": []}
    except FileNotFoundError:
        return {"error": "node is not installed or not on PATH", "match_pct": 0, "mismatches": []}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": (proc.stderr.strip() or "checker gave no report")[:500], "match_pct": 0, "mismatches": []}


def split_tests(ids, held_out=None):
    """(train, held_out). Default: every third test is held out, once there are 2+."""
    if held_out is None:
        held_out = [t for i, t in enumerate(ids) if i % 3 == 2] if len(ids) >= 2 else []
        if len(ids) >= 2 and not held_out:
            held_out = [ids[-1]]
    held = set(held_out)
    return [t for t in ids if t not in held], [t for t in ids if t in held]


def check_split(copy_path, trace_path=DEFAULT_TRACE, held_out=None):
    train_ids, held_ids = split_tests(test_ids(trace_path), held_out)
    return {
        "train": check(copy_path, trace_path, train_ids) if train_ids else None,
        "held_out": check(copy_path, trace_path, held_ids) if held_ids else None,
    }


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    copy_path = argv[0]
    trace_path = argv[1] if len(argv) > 1 else DEFAULT_TRACE
    report = check(copy_path, trace_path)
    print(f"match {report['match_pct']}%  ({report['matched']}/{report['total']} lines)")
    for m in report["mismatches"]:
        print("  mismatch", json.dumps(m, ensure_ascii=False))
    return 0 if report["match_pct"] == 100 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
