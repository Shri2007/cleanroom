"""Proves the checker works: python -m unittest tests.test_checker -v"""
import json
import tempfile
import unittest
from pathlib import Path

from server import checker

FIX = Path(__file__).parent / "fixtures"
SAMPLE = checker.DEFAULT_TRACE


class CheckerTest(unittest.TestCase):
    def test_good_copy_matches_sample_trace_fully(self):
        r = checker.check(FIX / "calc_good.js", SAMPLE)
        self.assertEqual((r["match_pct"], r["matched"], r["total"]), (100.0, 5, 5))
        self.assertEqual(r["mismatches"], [])

    def test_wrong_copy_is_scored_down_and_explained(self):
        r = checker.check(FIX / "calc_bad.js", SAMPLE)
        self.assertEqual(r["match_pct"], 80.0)  # only the "=" line differs (2*3=6, not 5)
        self.assertEqual([m["seq"] for m in r["mismatches"]], [5])
        self.assertEqual(r["mismatches"][0]["diffs"][0], {"field": "display", "expected": "5", "got": "6"})

    def test_hanging_copy_cannot_stall_the_checker(self):
        r = checker.check(FIX / "calc_hang.js", SAMPLE)
        self.assertLess(r["match_pct"], 100)
        self.assertTrue(any("timed out" in m.get("error", "") for m in r["mismatches"]))

    def test_sandbox_blocks_process_and_require(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "evil.js"
            p.write_text("module.exports = () => ({ press(){ process.exit(7) }, state(){ require('fs'); return {display:'0'} } });")
            r = checker.check(p, SAMPLE)
        self.assertEqual(r["match_pct"], 0.0)

    def test_deleted_and_suspect_lines_are_skipped(self):
        rows = [json.loads(l) for l in SAMPLE.read_text().splitlines()]
        rows[1]["deleted"] = True
        rows[2]["suspect"] = True
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "t.jsonl"
            t.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            r = checker.check(FIX / "calc_good.js", t)
        self.assertEqual((r["total"], r["skipped"]), (3, 2))

    def test_train_vs_held_out_split(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "t.jsonl"
            base = [json.loads(l) for l in SAMPLE.read_text().splitlines()]
            rows = base + [dict(r, test=2, seq=r["seq"] + 5) for r in base]
            t.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            r = checker.check_split(FIX / "calc_bad.js", t)
        self.assertEqual(r["train"]["match_pct"], 80.0)
        self.assertEqual(r["held_out"]["match_pct"], 80.0)
        self.assertEqual(checker.split_tests([1]), ([1], []))


if __name__ == "__main__":
    unittest.main()
