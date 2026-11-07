"""python -m unittest tests.test_cal_runner -v  (needs /usr/bin/cal)"""
import json
import subprocess
import sys
import unittest

from explorer import cal_runner


class CalRunnerTest(unittest.TestCase):
    def test_feb_2024_is_a_leap_month(self):
        (line,) = cal_runner.trace_lines([(2, 2024)])
        self.assertEqual(line["key"], "2 2024")
        self.assertIn("February 2024", line["display"])
        self.assertIn("29", line["display"].split("\n")[-1] + line["display"])
        self.assertFalse(line["suspect"])

    def test_1752_skips_eleven_days(self):
        (line,) = cal_runner.trace_lines([(9, 1752)])
        self.assertIn(" 2 14 15", line["display"])  # 2 Sep is followed by 14 Sep

    def test_rejected_input_is_kept_as_suspect(self):
        lines = cal_runner.trace_lines([(13, 2024), (2, 0)])
        for line in lines:
            self.assertIsNone(line["display"])
            self.assertTrue(line["suspect"])
            self.assertIn("error", line)

    def test_ints_only(self):
        for bad in [("2", 2024), (2.0, 2024), (True, 2024), ("-h", 1)]:
            with self.assertRaises(TypeError):
                cal_runner.run_cal(*bad)

    def test_cli_emits_jsonl_one_test_per_input(self):
        out = subprocess.run([sys.executable, "-m", "explorer.cal_runner", "1", "2000", "2", "2000"],
                             capture_output=True, text=True, check=True).stdout
        rows = [json.loads(l) for l in out.splitlines()]
        self.assertEqual([(r["seq"], r["test"]) for r in rows], [(1, 1), (2, 2)])

    def test_cli_rejects_non_ints(self):
        r = subprocess.run([sys.executable, "-m", "explorer.cal_runner", "feb", "2024"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
