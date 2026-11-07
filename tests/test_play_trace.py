"""docs/trace_recorder.js must record exactly what server/trace.py would.

python -m unittest tests.test_play_trace -v

The recorder runs in Node inside an empty vm context (no document, window or fetch), so these tests also show
it needs nothing from a browser. Its output is compared with the real `Trace.append` on the same inputs.
"""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from server import checker
from server.trace import READING_FIELDS, Trace

ROOT = Path(__file__).resolve().parent.parent
RECORDER = ROOT / "docs" / "trace_recorder.js"
PAGE = ROOT / "docs" / "play.html"
SAMPLE = ROOT / "traces" / "sample.jsonl"
FIX = Path(__file__).parent / "fixtures"

DRIVER = r"""
const fs = require('node:fs'), vm = require('node:vm');
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const ctx = vm.createContext({});                      // nothing in it: no document, window, fetch or console
vm.runInContext(fs.readFileSync(job.file, 'utf8'), ctx);
let i = 0;
const rec = vm.runInContext('TraceRecorder', ctx).create(job.source, () => job.events[Math.min(i, job.events.length - 1)].at);
const returned = [];
for (i = 0; i < job.events.length; i++) returned.push(rec.record(job.events[i].key, job.events[i].reading));
console.log(JSON.stringify({ returned: returned.map(r => (r === null ? null : r.seq)), size: rec.size(), text: rec.export() }));
"""


def record(events, source=None):
    """Run docs/trace_recorder.js over [{key, reading, at}] and return (export text, parsed lines, returned seqs)."""
    out = subprocess.run(["node", "-e", DRIVER], input=json.dumps({"file": str(RECORDER), "events": events, "source": source}),
                         capture_output=True, text=True, timeout=20)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    return got["text"], [json.loads(line) for line in got["text"].splitlines()], got["returned"]


def reading(display, expression=None, clear_label="C", active_op=None):
    return {"display": display, "expression": expression, "clear_label": clear_label, "active_op": active_op}


SAMPLE_ROWS = [json.loads(line) for line in SAMPLE.read_text().splitlines()]
SAMPLE_EVENTS = [{"key": r["key"], "reading": {f: r[f] for f in READING_FIELDS}, "at": 100 + r["t"]} for r in SAMPLE_ROWS]

# Inputs the server's own suspect rule treats differently: a wrong digit, a non-zero AC, a failed reading, a long
# display, thousands commas, and every non-digit key in the contract.
EDGE = [
    ("AC", reading("0", clear_label="AC")), ("7", reading("7")), ("7", reading("8")),        # last one: wrong digit -> suspect
    ("AC", reading("5", clear_label="AC")),                                                  # AC not showing 0 -> suspect
    ("3", reading(None, None, None, None)),                                                  # failed reading -> suspect
    ("4", reading("1,234")), ("5", reading("123456789")), ("5", reading("12345678")),        # 9 digits ok; 8 and not at the end -> suspect
    ("×", reading("5", active_op="×")), ("÷", reading("5", active_op="÷")), ("-", reading("5", active_op="-")),
    ("+", reading("5", active_op="+")), ("=", reading("10", expression="5+5")), ("%", reading("0.1")),
    ("+/-", reading("-0.1")), ("⌫", reading("-0.")), (".", reading("0.")), ("C", reading("0", clear_label="AC")),
    ("none", reading("0", clear_label="AC")), ("AC", reading("0", clear_label="AC")), ("9", reading("9")),
]
EDGE_EVENTS = [{"key": k, "reading": r, "at": 50 + i * 0.37} for i, (k, r) in enumerate(EDGE)]


def real_trace(events):
    """The same events through the real server/trace.py Trace, as a list of line dicts."""
    with tempfile.TemporaryDirectory() as d:
        trace = Trace(Path(d) / "t.jsonl", source="play")
        for e in events:
            trace.append(e["key"], e["reading"])
        return [dict(line) for line in trace.lines]


def without_t(lines):
    return [{k: v for k, v in line.items() if k != "t"} for line in lines]


class RecorderMatchesTraceTest(unittest.TestCase):
    def test_the_sample_session_is_recorded_exactly_like_trace_py(self):
        _, lines, _ = record(SAMPLE_EVENTS, source="play")
        self.assertEqual(without_t(lines), without_t(real_trace(SAMPLE_EVENTS)))
        self.assertEqual([list(l) for l in lines], [list(l) for l in real_trace(SAMPLE_EVENTS)])  # same field order too

    def test_edge_cases_get_the_same_suspect_flag_and_test_numbers_as_trace_py(self):
        _, lines, _ = record(EDGE_EVENTS, source="play")
        expected = real_trace(EDGE_EVENTS)
        self.assertEqual(without_t(lines), without_t(expected))
        self.assertTrue(any(l["suspect"] for l in lines) and not all(l["suspect"] for l in lines))  # both outcomes exercised
        self.assertEqual(max(l["test"] for l in lines), 3)  # three AC keys: test 1, then one more each (C and "none" open none)

    def test_field_order_and_types_follow_the_sample(self):
        _, lines, _ = record(EDGE_EVENTS)
        order = list(SAMPLE_ROWS[0])
        for line in lines:
            self.assertEqual(list(line), order)
            self.assertIsInstance(line["t"], float)
            self.assertIsInstance(line["suspect"], bool)
            self.assertIs(line["deleted"], False)
            self.assertEqual(line["source"], "play")  # the default: a person tapping, neither "camera" nor "screen"

    def test_t_starts_at_zero_and_keeps_one_decimal_in_the_text(self):
        events = [{"key": "AC", "reading": reading("0", clear_label="AC"), "at": 1000.0},
                  {"key": "2", "reading": reading("2"), "at": 1002.26},
                  {"key": "+", "reading": reading("2", active_op="+"), "at": 1004.0}]
        text, lines, _ = record(events)
        self.assertEqual([l["t"] for l in lines], [0.0, 2.3, 4.0])
        self.assertEqual(re.findall(r'"t": ([0-9.]+)', text), ["0.0", "2.3", "4.0"])  # "0.0", never "0"

    def test_keys_outside_the_contract_are_ignored_and_use_no_seq(self):
        events = [{"key": k, "reading": reading("1"), "at": i} for i, k in enumerate(["AC", " ", "1", "enter", "2"])]
        _, lines, returned = record(events)
        self.assertEqual(returned, [1, None, 2, None, 3])
        self.assertEqual([l["seq"] for l in lines], [1, 2, 3])
        self.assertEqual([l["key"] for l in lines], ["AC", "1", "2"])

    def test_non_text_readings_are_turned_into_text_not_crashed_on(self):
        _, lines, _ = record([{"key": "5", "reading": {"display": 5, "expression": None, "clear_label": "C", "active_op": None}, "at": 0}])
        self.assertEqual((lines[0]["display"], lines[0]["suspect"]), ("5", False))

    def test_the_recorder_needs_no_document_window_or_network(self):
        source = RECORDER.read_text()
        self.assertNotRegex(source, r"https?://")
        self.assertNotRegex(source, r"\b(document|window|fetch|XMLHttpRequest|localStorage|eval)\b")
        record(SAMPLE_EVENTS)  # ran above in a vm context that has none of them


class RecordedTraceScoresThroughTheChecker(unittest.TestCase):
    def export_to_file(self, d):
        text, _, _ = record(SAMPLE_EVENTS)
        path = Path(d) / "played.jsonl"
        path.write_text(text)
        return path

    def test_an_exported_session_scores_the_same_as_the_original_trace(self):
        with tempfile.TemporaryDirectory() as d:
            played = self.export_to_file(d)
            for copy, pct in (("calc_good.js", 100), ("calc_bad.js", 80)):
                original = checker.check(FIX / copy, SAMPLE)
                exported = checker.check(FIX / copy, played)
                self.assertEqual((exported["match_pct"], exported["matched"], exported["total"]),
                                 (original["match_pct"], original["matched"], original["total"]), copy)
                self.assertEqual(exported["match_pct"], pct)

    def test_an_exported_session_survives_server_replay_style_validation(self):
        text, lines, _ = record(SAMPLE_EVENTS)
        for line in lines:  # what replay.load / the checker require of every line
            self.assertIn(line["key"], {r["key"] for r in SAMPLE_ROWS} | set("0123456789"))
            for field in READING_FIELDS:
                self.assertTrue(line[field] is None or isinstance(line[field], str))
        self.assertTrue(text.endswith("\n") and "\n\n" not in text)


class PageStillHasShrisFeaturesTest(unittest.TestCase):
    """The page on main loads the brain's best copy and runs the brain's Calc contract. Adding the recorder must not
    remove any of that (an earlier version of this change replaced the page and dropped it)."""

    def setUp(self):
        self.page = PAGE.read_text()

    def test_it_still_loads_the_best_copy_from_the_server_and_runs_the_brain_contract(self):
        for needle in ("fetch('/scores'", "'/copies/'", "keys=", "globalThis.Calc.reset()", "globalThis.Calc.press(",
                       "globalThis.Calc.render()", "calc_best.js"):
            self.assertIn(needle, self.page, needle)
        self.assertNotIn("createCalculator", self.page)  # the old, non-brain interface

    def test_the_recorder_is_optional_hidden_by_default_and_local(self):
        self.assertIn('<script src="trace_recorder.js"></script>', self.page)
        self.assertIn("globalThis.TraceRecorder ? TraceRecorder.create() : null", self.page)  # page works if the file is missing
        self.assertRegex(self.page, r'<button class="pill" id="trace"[^>]*\bhidden\b')       # hidden until #trace
        self.assertNotRegex(self.page, r"https?://")
        self.assertNotRegex(self.page, r"<script[^>]*src=[\"']https?:")


if __name__ == "__main__":
    unittest.main()
