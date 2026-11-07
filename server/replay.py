"""Replay a saved trace with zero vision calls.

A live session is: tap a key -> wait for the display -> camera frame -> vision model -> trace
line. Replay keeps the trace lines and drops the first four steps: every reading comes from a
saved JSONL file, so no camera, reader or model is involved and nothing needs an API key.
This module imports only server.trace and server.checker, neither of which touches them.

    python -m server.replay traces/sample.jsonl
    python -m server.replay traces/sample.jsonl --out /tmp/again.jsonl --copy copies/calc_v3.js

`load()` reads and validates a saved trace, `replay()` re-records it through the same
`Trace.append` a live capture uses, and `score()` runs a copy against it with the checker's
train / held-out split.
"""
import argparse
import json
import sys
from pathlib import Path

from server import checker
from server.trace import KEYS, READING_FIELDS, Trace, is_suspect

SOURCE = "replay"  # lets a replayed trace be told apart from a live "camera" one


def load(path):
    """Read a saved v2 trace. Returns its lines in file order.

    Raises FileNotFoundError for a missing file (a mistyped path must not look like an empty
    trace) and ValueError, naming the line, for bad JSON, an unknown key, or a missing reading.
    """
    path = Path(path)
    lines = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            line = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: not valid JSON ({error.msg})") from None
        if not isinstance(line, dict):
            raise ValueError(f"{path}:{number}: a trace line must be a JSON object")
        if line.get("key") not in KEYS:
            raise ValueError(f"{path}:{number}: unknown key {line.get('key')!r}")
        missing = [f for f in READING_FIELDS if f not in line]
        if missing:
            raise ValueError(f"{path}:{number}: missing reading field(s): {', '.join(missing)}")
        lines.append(line)
    return lines


def usable(lines):
    """Lines a replay re-records: not undone by the operator and not suspect.

    A line is left out if it is deleted, if the saved file flags it suspect, or if the sanity rule
    (`server.trace.is_suspect`) flags it now, so a replayed trace never contains a suspect line,
    whatever the saved flag says. This is the same set of lines the checker scores.
    """
    return [line for line in lines
            if not line.get("deleted") and not line.get("suspect")
            and not is_suspect(line["key"], line["display"])]


def replay(saved, out_path):
    """Re-record a saved trace into a new file through `Trace.append`, with no vision.

    `saved` is a path or a list of lines from `load()`. Deleted and suspect lines are dropped (see
    `usable`), so seq numbers restart at 1 and stay contiguous; test numbers are rebuilt from the AC
    keys exactly as in a live run. Every kept line has suspect false and deleted false. Returns the
    new Trace. Refuses to touch an existing file (a Trace would append to it) or the file it is
    replaying.

    Dropping a suspect AC line (the AC key is what starts a new test) merges that test into the one
    before it, so the copy is not reset between them. The checker skips a suspect line too.
    """
    out_path = Path(out_path)
    if not isinstance(saved, list):
        if out_path.resolve() == Path(saved).resolve():
            raise ValueError("--out must not be the trace being replayed")
        saved = load(saved)
    if out_path.exists():
        raise FileExistsError(f"{out_path} already exists; a replay never appends to or overwrites a trace")
    trace = Trace(out_path, source=SOURCE)
    for line in usable(saved):
        trace.append(line["key"], {field: line[field] for field in READING_FIELDS})
    return trace


def score(copy_path, trace_path, held_out=None):
    """Run a copy against a saved trace using the checker contract.

    Returns {"all": report, "train": report | None, "held_out": report | None}, each report as
    returned by server.checker (match_pct, matched, total, mismatches...). A single-test trace
    has nothing to hold out, so "held_out" is None.
    """
    return {"all": checker.check(copy_path, trace_path),
            **checker.check_split(copy_path, trace_path, held_out)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", type=Path, help="saved v2 JSONL trace")
    parser.add_argument("--out", type=Path, help="re-record the replay to this new file")
    parser.add_argument("--copy", type=Path, help="a copy (.js) to score against the trace")
    args = parser.parse_args(argv)
    try:
        saved = load(args.trace)
    except (OSError, ValueError) as error:
        print(f"replay: {error}", file=sys.stderr)
        return 2
    keep = usable(saved)
    tests = len({line["test"] for line in keep})
    print(f"{args.trace}: {len(saved)} lines, {len(keep)} replayed, {tests} test(s); "
          "no camera, reader or vision model is used")
    if args.out:
        try:
            trace = replay(saved, args.out)
        except (OSError, ValueError) as error:
            print(f"replay: {error}", file=sys.stderr)
            return 2
        print(f"re-recorded {len(trace.lines)} lines to {args.out}")
    if args.copy:
        try:
            result = score(args.copy, args.out if args.out else args.trace)
        except checker.CheckerError as error:
            print(f"replay: checker failed: {error}", file=sys.stderr)
            return 2
        for name in ("all", "train", "held_out"):
            report = result[name]
            if report is None:
                print(f"{name}: none (not enough tests to split)")
            else:
                print(f"{name}: {report['match_pct']}% ({report['matched']}/{report['total']})")
        for mismatch in result["all"]["mismatches"]:
            print("  mismatch", json.dumps(mismatch, ensure_ascii=False))
        return 0 if result["all"]["match_pct"] == 100 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
