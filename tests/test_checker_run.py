"""server.checker.run(): the entry point server/brain.py and agent/ call.
python -m unittest tests.test_checker_run -v
"""
import json
import os
import time
import unittest
from pathlib import Path
from unittest import mock

from server import checker

FIX = Path(__file__).parent / "fixtures"
SAMPLE = [json.loads(l) for l in checker.DEFAULT_TRACE.read_text().splitlines() if l.strip()]
FAKE = "FAKE-SECRET-do-not-leak-456"

CALC_GOOD = """globalThis.Calc = (() => {
  let display = "0", acc = null, op = null, fresh = true, active = null, dirty = false;
  const ap = (a, b, o) => (o === "+" ? a + b : o === "-" ? a - b : o === "×" ? a * b : a / b);
  return {
    reset() { display = "0"; acc = null; op = null; fresh = true; active = null; dirty = false; },
    press(k) {
      if (/^[0-9]$/.test(k)) { display = fresh || display === "0" ? k : display + k; fresh = false; active = null; dirty = true; }
      else if (k === "AC" || k === "C") this.reset();
      else if ("+-×÷".includes(k)) { acc = op && !fresh ? ap(acc, Number(display), op) : Number(display); display = String(acc); op = k; active = k; fresh = true; }
      else if (k === "=") { if (op) { display = String(ap(acc, Number(display), op)); op = null; } fresh = true; active = null; }
    },
    render() { return { display, expression: null, clear_label: dirty ? "C" : "AC", active_op: active }; },
  };
})();"""
CALC_BAD = CALC_GOOD.replace('o === "+" ? a + b', 'o === "+" ? a * b')

REAL = [json.loads(l) for l in (FIX / "cal_real.jsonl").read_text().splitlines()]
CAL_LINES = [{"seq": r["seq"], "test": r["test"], "args": [int(x) for x in r["key"].split()],
              "output": r["display"], "deleted": False} for r in REAL]


def cal_table(outputs):
    table = {f"{l['args'][0]}:{l['args'][1]}": o for l, o in zip(CAL_LINES, outputs)}
    return 'globalThis.Cal={run(m,y){const t=' + json.dumps(table) + ';return t[m+":"+y]??"";}};'


class RunCalcTest(unittest.TestCase):
    def test_good_copy_scores_100_on_sample(self):
        r = checker.run("calc", CALC_GOOD, SAMPLE)
        self.assertEqual((r["match_pct"], r["matched"], r["total"]), (100.0, 5, 5))
        self.assertEqual(r["tests"], [{"test": 1, "pass": True}])
        self.assertEqual(r["mismatches"], [])

    def test_buggy_copy_scores_80_and_names_the_line(self):
        r = checker.run("calc", CALC_BAD, SAMPLE)
        self.assertEqual(r["match_pct"], 80.0)
        self.assertEqual(r["tests"], [{"test": 1, "pass": False}])
        (m,) = r["mismatches"]
        self.assertEqual((m["seq"], m["key"], m["expected"], m["got"]),
                         (5, "=", {"display": "5"}, {"display": "6"}))

    def test_null_trace_fields_are_not_compared(self):
        lines = [dict(l, clear_label=None, active_op=None) for l in SAMPLE]
        r = checker.run("calc", CALC_GOOD.replace('clear_label: dirty ? "C" : "AC"', 'clear_label: "wrong"'), lines)
        self.assertEqual(r["match_pct"], 100.0)

    def test_comparison_is_exact_not_normalised(self):
        lines = [dict(l, display="1,000" if l["seq"] == 5 else l["display"]) for l in SAMPLE]
        r = checker.run("calc", CALC_GOOD, lines)
        self.assertEqual(r["matched"], 4)

    def test_tests_filter_deleted_and_suspect(self):
        lines = [dict(l) for l in SAMPLE]
        lines[1]["deleted"] = True
        lines[2]["suspect"] = True
        r = checker.run("calc", CALC_GOOD, lines)
        self.assertEqual((r["total"], r["skipped"]), (3, 2))
        self.assertEqual(checker.run("calc", CALC_GOOD, SAMPLE, tests=[99])["total"], 0)
        self.assertEqual(checker.run("calc", CALC_GOOD, SAMPLE, tests=[99])["match_pct"], 0)

    def test_each_test_starts_from_reset(self):
        second = [dict(l, test=2, seq=l["seq"] + 5) for l in SAMPLE]
        r = checker.run("calc", CALC_GOOD, SAMPLE + second)
        self.assertEqual((r["match_pct"], len(r["tests"])), (100.0, 2))


    def three_tests_with_a_wrong_held_out(self):
        rows = [dict(r, test=n, seq=r["seq"] + 5 * (n - 1)) for n in (1, 2, 3) for r in SAMPLE]
        for r in rows:
            if r["test"] == 3 and r["key"] == "=":
                r["display"] = "99"  # only test 3, the held-out one, disagrees with the copy
        return rows

    def test_train_and_held_out_are_scored_separately(self):
        rows = self.three_tests_with_a_wrong_held_out()
        train = checker.run("calc", CALC_GOOD, rows, tests=[1, 2])
        held = checker.run("calc", CALC_GOOD, rows, tests=[3])
        self.assertEqual((train["match_pct"], train["matched"], train["total"]), (100.0, 10, 10))
        self.assertEqual((held["match_pct"], held["matched"], held["total"]), (80.0, 4, 5))
        self.assertEqual([t["test"] for t in train["tests"]], [1, 2])
        self.assertEqual([t["test"] for t in held["tests"]], [3])
        self.assertEqual(checker.run("calc", CALC_GOOD, rows)["matched"], 14)  # all three together

    def test_skipped_counts_only_deleted_and_suspect_lines_of_the_scored_tests(self):
        rows = self.three_tests_with_a_wrong_held_out()
        rows[0]["deleted"] = True
        rows[1]["suspect"] = True
        rows[7]["suspect"] = True  # a test-2 line: outside tests=[1], so not counted
        r = checker.run("calc", CALC_GOOD, rows, tests=[1])
        self.assertEqual((r["total"], r["skipped"]), (3, 2))
        self.assertEqual(checker.run("calc", CALC_GOOD, rows)["skipped"], 3)


class RunCalTest(unittest.TestCase):
    def test_exact_copy_scores_100(self):
        r = checker.run("cal", cal_table([l["output"] for l in CAL_LINES]), CAL_LINES)
        self.assertEqual((r["match_pct"], r["matched"], r["total"]), (100.0, 8, 8))

    def test_one_wrong_month_names_it(self):
        outs = [l["output"] for l in CAL_LINES]
        outs[4] = outs[4].replace("14 15", "03 04")  # September 1752 without the gap
        r = checker.run("cal", cal_table(outs), CAL_LINES)
        self.assertEqual((r["match_pct"], r["matched"]), (87.5, 7))
        (m,) = r["mismatches"]
        self.assertEqual(m["args"], [9, 1752])
        self.assertEqual(m["expected"], CAL_LINES[4]["output"])

    def test_trailing_whitespace_matters(self):
        stripped = [l["output"].rstrip() for l in CAL_LINES]
        self.assertLess(checker.run("cal", cal_table(stripped), CAL_LINES)["match_pct"], 100)

    def test_bad_args_fail_the_line_not_the_run(self):
        lines = CAL_LINES + [{"seq": 99, "test": 99, "args": [13, 2024], "output": "x", "deleted": False}]
        r = checker.run("cal", cal_table([l["output"] for l in CAL_LINES]), lines)
        self.assertEqual((r["matched"], r["total"]), (8, 9))


class RunRobustnessTest(unittest.TestCase):
    def test_syntax_error_scores_zero_without_raising(self):
        for target, lines in (("calc", SAMPLE), ("cal", CAL_LINES)):
            r = checker.run(target, "globalThis.Calc = {{{", lines)
            self.assertEqual(r["match_pct"], 0)
            self.assertEqual(len(r["mismatches"]), len(lines))

    def test_crash_fails_rest_of_that_test_only(self):
        code = CALC_GOOD.replace("press(k) {", 'press(k) { if (k === "3") throw new Error("boom");')
        r = checker.run("calc", code, SAMPLE + [dict(l, test=2, seq=l["seq"] + 5) for l in SAMPLE[:2]])
        self.assertEqual([t["pass"] for t in r["tests"]], [False, True])
        # test 1: AC, 2, + pass, then "3" crashes and "=" is not trusted; test 2: AC and 2 pass
        self.assertEqual((r["matched"], r["total"]), (3 + 2, 5 + 2))
        self.assertIn("boom", json.dumps(r["mismatches"]))

    def test_hanging_copy_returns_in_bounded_time(self):
        code = 'globalThis.Calc = {reset(){}, press(){ while (true) {} }, render(){ return {display:"0"}; }};'
        started = time.monotonic()
        r = checker.run("calc", code, SAMPLE)
        self.assertLess(time.monotonic() - started, 10)
        self.assertLess(r["match_pct"], 100)
        self.assertTrue(any("timed out" in json.dumps(m) for m in r["mismatches"]))

    def test_copy_that_hangs_at_load_fails_fast_for_every_line(self):
        for target, lines, limit in (("calc", SAMPLE, 3), ("cal", CAL_LINES * 4, 3)):
            started = time.monotonic()
            r = checker.run(target, "while (true) {}", lines)
            with self.subTest(target):
                self.assertLess(time.monotonic() - started, limit)  # one load attempt, not one per line
                self.assertEqual((r["match_pct"], len(r["mismatches"])), (0, len(lines)))
                self.assertIn("timed out", json.dumps(r["mismatches"][0]))

    def test_bad_calls_raise_value_error(self):
        with self.assertRaises(ValueError):
            checker.run("nope", "", [])
        with self.assertRaises(ValueError):
            checker.run("cal", "x" * (checker.MAX_CODE_CHARS + 1), [])
        with self.assertRaises(ValueError):
            checker.run("cal", "", [{}] * (checker.MAX_LINES + 1))


class RunSecretsTest(unittest.TestCase):
    ESCAPES = {
        "constructor": 'const p = Calc.press.constructor("return process")(); return String(p.env.GEMINI_API_KEY);',
        "this": 'const p = this.constructor.constructor("return process")(); return String(p.env.GEMINI_API_KEY);',
        "direct": 'return String(process.env.GEMINI_API_KEY);',
        "require": 'return String(require("child_process").execSync("env"));',
    }

    def test_no_escape_leaks_a_key(self):
        for name, body in self.ESCAPES.items():
            code = ('globalThis.Calc = {reset(){}, press(){}, render(){ ' + body + ' }};')
            cal = ('globalThis.Cal = {run(){ ' + body + ' }};')
            with self.subTest(name), mock.patch.dict(os.environ, {"GEMINI_API_KEY": FAKE, "MODEL_API_KEY": FAKE}):
                out = json.dumps([checker.run("calc", code, SAMPLE), checker.run("cal", cal, CAL_LINES)])
                self.assertNotIn(FAKE, out)


class RealCallersUseItTest(unittest.TestCase):
    """The agents and the brain fall back to local stand-ins only when run() is missing."""

    def test_agent_compat_uses_server_checker(self):
        from agent import compat
        compat.ANNOUNCED.clear()
        r = compat.check_cal(cal_table([l["output"] for l in CAL_LINES]), CAL_LINES, [l["test"] for l in CAL_LINES])
        self.assertEqual(r["match_pct"], 100.0)
        self.assertEqual(r["mode"], "cal")  # only the real checker adds "mode"
        self.assertFalse([m for m in compat.ANNOUNCED if "server.checker.run" in m])

    def test_brain_score_uses_server_checker(self):
        try:
            from server import brain
        except ImportError as error:
            self.skipTest(f"server.brain not importable here: {error}")
        r = brain.score(CALC_GOOD, SAMPLE, [1])
        self.assertEqual((r["match_pct"], r["mode"]), (100.0, "calc"))


if __name__ == "__main__":
    unittest.main()
