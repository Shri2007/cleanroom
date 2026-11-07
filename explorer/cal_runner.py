"""Runs /usr/bin/cal M Y (ints only) -> trace lines (Ali).

The explorer for the "cal" target: instead of a camera reading a phone, we run the real
program and record exactly what it prints. Same line shape as the calculator trace
(seq, test, t, source, key, display, ..., suspect, deleted) so downstream code can treat
both alike: `key` is the input "M Y" and `display` is the full text cal printed.

    python -m explorer.cal_runner 2 2024 9 1752 > traces/cal.jsonl
"""
import json
import subprocess
import sys
import time

CAL = "/usr/bin/cal"
TIMEOUT_SECONDS = 5


def run_cal(month, year):
    """Run the real cal for one month. Ints only, so nothing user-typed reaches argv
    as a flag or a name. Returns (text, error); error is None on success."""
    if isinstance(month, bool) or isinstance(year, bool) or not isinstance(month, int) or not isinstance(year, int):
        raise TypeError("month and year must be ints")
    try:
        proc = subprocess.run(
            [CAL, str(month), str(year)],  # no shell
            capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
            env={"LC_ALL": "C", "PATH": "/usr/bin:/bin", "TERM": "dumb"},  # stable English output, no colour
        )
    except FileNotFoundError:
        raise RuntimeError(f"{CAL} not found (on Debian/Ubuntu: apt install ncal)")
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"exit {proc.returncode}"
    return proc.stdout.rstrip("\n"), None


def trace_lines(inputs, test=1, start_seq=1):
    """Turn [(month, year), ...] into trace lines, one per input.

    A run that cal rejects (month 13, year 0...) is kept as a line with display=None
    and suspect=True: the copy must be able to fail the same way, and the checker
    skips suspect lines, so these never count against a copy by accident.
    """
    started = time.monotonic()
    lines = []
    for i, (month, year) in enumerate(inputs):
        text, error = run_cal(month, year)
        lines.append({
            "seq": start_seq + i,
            "test": test,
            "t": round(time.monotonic() - started, 3),
            "source": "cal",
            "key": f"{month} {year}",
            "display": text,
            "expression": None,
            "clear_label": None,
            "active_op": None,
            "suspect": text is None,
            "deleted": False,
            **({"error": error} if error else {}),
        })
    return lines


def main(argv):
    try:
        nums = [int(a) for a in argv]
    except ValueError:
        print("usage: python -m explorer.cal_runner M Y [M Y ...]  (ints only)", file=sys.stderr)
        return 2
    if not nums or len(nums) % 2:
        print("usage: python -m explorer.cal_runner M Y [M Y ...]  (ints only)", file=sys.stderr)
        return 2
    for n, line in enumerate(trace_lines(list(zip(nums[::2], nums[1::2]))), start=1):
        line["test"] = n  # one test per input: each month is independent
        print(json.dumps(line, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
