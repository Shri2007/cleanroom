// Records one trace line per key press, in the shape of traces/sample.jsonl (server/trace.py, contract v2),
// so a session played on the phone page can be scored by the checker.
//
//   const rec = TraceRecorder.create();
//   rec.record("2", { display: "2", expression: null, clear_label: "C", active_op: null });
//   rec.export();   // JSONL text: one line per press, same 11 fields in the same order as the sample
//
// Every rule below mirrors server/trace.py on purpose: the key list, the suspect check, and how tests are
// numbered (a new test starts at each AC). tests/test_play_trace.py checks this file against the real Trace.
(function (root) {
  "use strict";

  var KEYS = {};
  "0123456789.+-×÷=%".split("").concat(["+/-", "AC", "C", "⌫", "none"]).forEach(function (k) { KEYS[k] = true; });
  var DIGITS = "0123456789";
  var MAX_DIGITS = 9; // the display stops accepting digits here
  var READING_FIELDS = ["display", "expression", "clear_label", "active_op"];

  // server/trace.py is_suspect: no AI, just a sanity flag. Digits must show up at the end, AC must show 0.
  function isSuspect(key, display) {
    if (display === null) return true;
    var shown = display.replace(/[, ]/g, "");
    if (DIGITS.indexOf(key) !== -1 && key.length === 1) {
      var digitCount = 0;
      for (var i = 0; i < shown.length; i++) if (DIGITS.indexOf(shown[i]) !== -1) digitCount++;
      return !(shown.slice(-key.length) === key) && digitCount < MAX_DIGITS;
    }
    if (key === "AC") return shown !== "0";
    return false;
  }

  function text(value) { return value === null || value === undefined ? null : String(value); }

  function create(source, clock) {
    var lines = [];
    var now = clock || function () { return Date.now() / 1000; };
    var started = null;
    var label = source || "play"; // a person tapping the phone page: neither "camera" nor "screen"

    return {
      // Add one line for a key press and return it, or return null for a key that is not in the contract.
      record: function (key, reading) {
        if (!KEYS[key]) return null;
        var at = now();
        if (started === null) started = at; // the first line is t=0.0, like the sample
        reading = reading || {};
        var shown = {};
        READING_FIELDS.forEach(function (f) { shown[f] = text(reading[f]); });
        var last = lines.length ? lines[lines.length - 1] : null;
        var line = {
          seq: last ? last.seq + 1 : 1,
          test: last ? last.test + (key === "AC" ? 1 : 0) : 1,
          t: Math.round((at - started) * 10) / 10,
          source: label,
          key: key,
          display: shown.display,
          expression: shown.expression,
          clear_label: shown.clear_label,
          active_op: shown.active_op,
          suspect: isSuspect(key, shown.display),
          deleted: false,
        };
        lines.push(line);
        return line;
      },
      size: function () { return lines.length; },
      lines: function () { return lines.slice(); },
      // JSONL, field by field so `t` keeps its one decimal ("0.0", not "0") and the field order survives.
      export: function () {
        return lines.map(function (l) {
          return "{" + Object.keys(l).map(function (k) {
            return JSON.stringify(k) + ": " + (k === "t" ? l.t.toFixed(1) : JSON.stringify(l[k]));
          }).join(", ") + "}\n";
        }).join("");
      },
    };
  }

  root.TraceRecorder = { create: create, isSuspect: isSuspect, KEYS: Object.keys(KEYS) };
})(typeof globalThis !== "undefined" ? globalThis : this);
