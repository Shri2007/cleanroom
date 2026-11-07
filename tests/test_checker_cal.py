"""Cal mode of the checker: python -m unittest tests.test_checker_cal -v

cal_real.jsonl was recorded from the real /usr/bin/cal with explorer.cal_runner, so these
tests do not need cal installed.
"""
import json
import tempfile
import unittest
from pathlib import Path

from server import checker

FIX = Path(__file__).parent / "fixtures"
TRACE = FIX / "cal_real.jsonl"


class CheckerCalTest(unittest.TestCase):
    def test_good_copy_matches_real_cal(self):
        r = checker.check(FIX / "cal_good.js", TRACE)
        self.assertEqual((r["mode"], r["match_pct"], r["matched"], r["total"]), ("cal", 100.0, 8, 8))

    def test_september_1752_gap_is_covered(self):
        keys = [json.loads(l)["key"] for l in TRACE.read_text().splitlines()]
        self.assertIn("9 1752", keys)

    def test_wrong_copy_is_scored_down(self):
        r = checker.check(FIX / "cal_bad.js", TRACE)
        self.assertEqual(r["match_pct"], 25.0)  # only the 30-day months happen to match
        self.assertTrue(all(m["diffs"][0]["field"] == "display" for m in r["mismatches"]))

    def test_hanging_copy_cannot_stall_the_checker(self):
        r = checker.check(FIX / "cal_hang.js", TRACE)
        self.assertEqual(r["match_pct"], 0.0)
        self.assertTrue(any("timed out" in m.get("error", "") for m in r["mismatches"]))

    def test_padding_and_blank_rows_do_not_matter(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.js"
            p.write_text("const g = (()=>{const module={exports:{}};" + (FIX / "cal_good.js").read_text() +
                         ";return module.exports})(); module.exports = (m, y) => g(m, y).split('\\n').map(r => r + '   ').join('\\n') + '\\n\\n\\n';")
            r = checker.check(p, TRACE)
        self.assertEqual(r["match_pct"], 100.0)

    def test_rejected_input_lines_are_skipped_not_failed(self):
        rows = [json.loads(l) for l in TRACE.read_text().splitlines()]
        rows.append(dict(rows[0], seq=99, test=99, key="13 2024", display=None, suspect=True))
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "t.jsonl"
            t.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            r = checker.check(FIX / "cal_good.js", t)
        self.assertEqual((r["match_pct"], r["skipped"]), (100.0, 1))

    def test_train_vs_held_out_split_works_on_cal(self):
        r = checker.check_split(FIX / "cal_good.js", TRACE)
        self.assertEqual((r["train"]["match_pct"], r["held_out"]["match_pct"]), (100.0, 100.0))
        self.assertEqual(r["train"]["total"] + r["held_out"]["total"], 8)

    def test_mode_can_be_forced_and_bad_mode_errors(self):
        with self.assertRaises(checker.CheckerError):
            checker.check(FIX / "cal_good.js", TRACE, mode="nope")
        # a calculator copy forced onto a cal trace cannot match
        r = checker.check(FIX / "calc_good.js", TRACE, mode="calc")
        self.assertEqual(r["mode"], "calc")


if __name__ == "__main__":
    unittest.main()
