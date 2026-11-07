"""Runs checker/check.mjs on a copy, train vs held-out (Ali).

    python -m server.checker <copy.js> [trace.jsonl]

`check()` scores a copy against a trace. `check_split()` scores it on the train tests
and on held-out tests separately, so a copy that only memorised the lines it was shown
shows up as a gap between the two numbers.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_MJS = ROOT / "checker" / "check.mjs"
DEFAULT_TRACE = ROOT / "traces" / "sample.jsonl"
TIMEOUT_SECONDS = 20  # whole run; each call into the copy has its own 500 ms limit


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
    cmd = ["node", str(CHECK_MJS), str(copy_path), str(trace_path)]
    if tests is not None:
        cmd += ["--tests", ",".join(str(t) for t in tests)]
    if mode is not None:
        cmd += ["--mode", mode]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
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
