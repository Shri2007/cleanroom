"""server/replay.py: python -m unittest tests.test_replay -v

Replay must score a saved trace through the real checker and must never touch vision.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from server import replay
from server.trace import READING_FIELDS

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "traces" / "sample.jsonl"
FIX = Path(__file__).parent / "fixtures"
SAVED = [json.loads(l) for l in SAMPLE.read_text().splitlines()]


def write(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return path


class LoadTest(unittest.TestCase):
    def test_sample_loads_unchanged(self):
        self.assertEqual(replay.load(SAMPLE), SAVED)

    def test_missing_file_is_an_error_not_an_empty_trace(self):
        with self.assertRaises(FileNotFoundError):
            replay.load(ROOT / "traces" / "does-not-exist.jsonl")

    def test_bad_lines_are_named(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for label, row, fragment in [
                ("json", None, "not valid JSON"),
                ("key", dict(SAVED[0], key="nope"), "unknown key 'nope'"),
                ("reading", {k: v for k, v in SAVED[0].items() if k != "display"}, "missing reading field(s): display"),
            ]:
                path = d / f"{label}.jsonl"
                path.write_text(json.dumps(SAVED[0]) + "\n" + ("{oops\n" if row is None else json.dumps(row) + "\n"))
                with self.subTest(label), self.assertRaisesRegex(ValueError, rf"{label}\.jsonl:2: .*{re.escape(fragment)}"):
                    replay.load(path)

    def test_blank_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "t.jsonl"
            path.write_text("\n" + SAMPLE.read_text() + "\n\n")
            self.assertEqual(len(replay.load(path)), 5)


class ReplayTest(unittest.TestCase):
    def test_rerecords_the_same_readings_through_trace_append(self):
        with tempfile.TemporaryDirectory() as d:
            trace = replay.replay(SAMPLE, Path(d) / "again.jsonl")
            again = replay.load(Path(d) / "again.jsonl")
        self.assertEqual(again, trace.lines)
        for new, old in zip(again, SAVED):
            self.assertEqual((new["seq"], new["test"], new["key"]), (old["seq"], old["test"], old["key"]))
            self.assertEqual({f: new[f] for f in READING_FIELDS}, {f: old[f] for f in READING_FIELDS})
            self.assertEqual(new["source"], "replay")
            self.assertFalse(new["suspect"])

    def test_deleted_lines_are_dropped_and_seq_restarts(self):
        rows = [dict(r) for r in SAVED]
        rows[1]["deleted"] = True
        with tempfile.TemporaryDirectory() as d:
            trace = replay.replay(rows, Path(d) / "t.jsonl")
        self.assertEqual([l["key"] for l in trace.lines], ["AC", "+", "3", "="])
        self.assertEqual([l["seq"] for l in trace.lines], [1, 2, 3, 4])

    def test_tests_are_rebuilt_from_ac_keys(self):
        second = [dict(r, test=2) for r in SAVED]
        with tempfile.TemporaryDirectory() as d:
            trace = replay.replay(SAVED + second, Path(d) / "t.jsonl")
        self.assertEqual([l["test"] for l in trace.lines], [1] * 5 + [2] * 5)

    def test_saved_suspect_line_stays_excluded(self):
        rows = [dict(r) for r in SAVED]
        rows[2]["suspect"] = True  # the "+" line: flagged suspect in the saved file, reading itself looks fine
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "again.jsonl"
            trace = replay.replay(rows, out)
            on_disk = replay.load(out)
        self.assertEqual([l["key"] for l in trace.lines], ["AC", "2", "3", "="])
        self.assertEqual(on_disk, trace.lines)  # excluded in the file too, not just in memory
        self.assertFalse(any(l["suspect"] for l in trace.lines))

    def test_suspect_exclusion_survives_replaying_the_replay(self):
        rows = [dict(r) for r in SAVED]
        rows[2]["suspect"] = True
        with tempfile.TemporaryDirectory() as d:
            first = replay.replay(rows, Path(d) / "one.jsonl")
            second = replay.replay(Path(d) / "one.jsonl", Path(d) / "two.jsonl")
        self.assertEqual(
            [(l["seq"], l["test"], l["key"], l["display"]) for l in second.lines],
            [(l["seq"], l["test"], l["key"], l["display"]) for l in first.lines])
        self.assertEqual([l["key"] for l in second.lines], ["AC", "2", "3", "="])

    def test_line_the_sanity_rule_flags_is_excluded_even_if_saved_clean(self):
        rows = [dict(r) for r in SAVED]
        rows[1]["display"] = "7"      # key "2" but display "7": is_suspect says so, whatever the file says
        rows[1]["suspect"] = False
        rows[3]["display"] = None     # a failed reading
        rows[3]["suspect"] = False
        with tempfile.TemporaryDirectory() as d:
            trace = replay.replay(rows, Path(d) / "t.jsonl")
        self.assertEqual([l["key"] for l in trace.lines], ["AC", "+", "="])
        self.assertFalse(any(l["suspect"] for l in trace.lines))

    def test_replayed_lines_keep_the_agreed_trace_contract(self):
        rows = [dict(r) for r in SAVED] + [dict(r, test=2, seq=r["seq"] + 5) for r in SAVED]
        rows[1]["deleted"] = True     # dropped
        rows[4]["suspect"] = True     # dropped
        rows[7]["suspect"] = True     # dropped (the "+" of test 2)
        with tempfile.TemporaryDirectory() as d:
            trace = replay.replay(rows, Path(d) / "t.jsonl")
        types = {"seq": int, "test": int, "t": (int, float), "source": str, "key": str,
                 "display": (str, type(None)), "expression": (str, type(None)),
                 "clear_label": (str, type(None)), "active_op": (str, type(None)),
                 "suspect": bool, "deleted": bool}
        order = list(SAVED[0].keys())
        self.assertEqual(order, ["seq", "test", "t", "source", "key", "display", "expression",
                                 "clear_label", "active_op", "suspect", "deleted"])
        for line in trace.lines:
            self.assertEqual(list(line.keys()), order)             # same fields, same order as the sample
            for field, kind in types.items():
                self.assertIsInstance(line[field], kind, (field, line))
            self.assertEqual(line["source"], replay.SOURCE)
            self.assertEqual(replay.SOURCE, "replay")
            self.assertIs(line["suspect"], False)                   # no suspect line leaks in
            self.assertIs(line["deleted"], False)                   # nor a deleted one
        self.assertEqual([l["seq"] for l in trace.lines], list(range(1, len(trace.lines) + 1)))  # contiguous
        # test 1 lost its "2" (deleted) and "=" (suspect); test 2 lost its "+" (suspect)
        self.assertEqual([l["key"] for l in trace.lines], ["AC", "+", "3", "AC", "2", "3", "="])
        self.assertEqual([l["test"] for l in trace.lines], [1, 1, 1, 2, 2, 2, 2])
        # values of the kept lines are the saved values, in saved order
        kept = [r for r in rows if not r["deleted"] and not r["suspect"]]
        self.assertEqual([(l["key"], {f: l[f] for f in READING_FIELDS}) for l in trace.lines],
                         [(r["key"], {f: r[f] for f in READING_FIELDS}) for r in kept])

    def test_never_overwrites_or_appends(self):
        with tempfile.TemporaryDirectory() as d:
            existing = write(Path(d) / "keep.jsonl", SAVED)
            before = existing.read_text()
            with self.assertRaises(FileExistsError):
                replay.replay(SAMPLE, existing)
            self.assertEqual(existing.read_text(), before)
        with self.assertRaises(ValueError):
            replay.replay(SAMPLE, SAMPLE)
        self.assertEqual(replay.load(SAMPLE), SAVED)


class ScoreTest(unittest.TestCase):
    def test_reference_copy_scores_100_on_sample(self):
        r = replay.score(FIX / "calc_good.js", SAMPLE)
        self.assertEqual((r["all"]["match_pct"], r["all"]["matched"], r["all"]["total"]), (100.0, 5, 5))
        self.assertEqual((r["train"]["match_pct"], r["held_out"]), (100.0, None))

    def test_buggy_copy_scores_80_and_names_the_line(self):
        r = replay.score(FIX / "calc_bad.js", SAMPLE)
        self.assertEqual(r["all"]["match_pct"], 80.0)
        self.assertEqual([m["seq"] for m in r["all"]["mismatches"]], [5])

    def test_replayed_trace_scores_the_same_as_the_original(self):
        with tempfile.TemporaryDirectory() as d:
            replay.replay(SAMPLE, Path(d) / "again.jsonl")
            for copy in ("calc_good.js", "calc_bad.js"):
                original = replay.score(FIX / copy, SAMPLE)["all"]["match_pct"]
                again = replay.score(FIX / copy, Path(d) / "again.jsonl")["all"]["match_pct"]
                self.assertEqual(original, again, copy)

    def test_two_test_trace_gets_a_held_out_split(self):
        with tempfile.TemporaryDirectory() as d:
            path = write(Path(d) / "t.jsonl", SAVED + [dict(r, test=2, seq=r["seq"] + 5) for r in SAVED])
            r = replay.score(FIX / "calc_bad.js", path)
        self.assertEqual((r["train"]["match_pct"], r["held_out"]["match_pct"]), (80.0, 80.0))


class NoVisionTest(unittest.TestCase):
    def test_import_and_replay_load_no_camera_reader_or_model(self):
        code = (
            "import sys, tempfile, pathlib\n"
            "from server import replay\n"
            "with tempfile.TemporaryDirectory() as d:\n"
            f"    replay.replay({str(SAMPLE)!r}, pathlib.Path(d) / 'x.jsonl')\n"
            "bad = [m for m in ('cv2', 'openai', 'numpy', 'server.reader', 'server.camera', 'server.app', 'server.brain')\n"
            "       if m in sys.modules]\n"
            "print(bad)\n"
        )
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                             env={"PATH": ""})  # no keys, no PATH: replay needs neither
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "[]")


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "server.replay", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True)

    def test_summary_and_exit_codes(self):
        ok = self.run_cli(SAMPLE, "--copy", FIX / "calc_good.js")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("all: 100% (5/5)", ok.stdout)
        self.assertIn("held_out: none", ok.stdout)
        bad = self.run_cli(SAMPLE, "--copy", FIX / "calc_bad.js")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("all: 80% (4/5)", bad.stdout)

    def test_out_then_score_the_rerecording(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "again.jsonl"
            r = self.run_cli(SAMPLE, "--out", out, "--copy", FIX / "calc_good.js")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("re-recorded 5 lines", r.stdout)
            self.assertEqual(self.run_cli(SAMPLE, "--out", out).returncode, 2)  # never overwrites

    def test_missing_trace_exits_2(self):
        r = self.run_cli(ROOT / "traces" / "nope.jsonl")
        self.assertEqual(r.returncode, 2)
        self.assertIn("replay:", r.stderr)


if __name__ == "__main__":
    unittest.main()
