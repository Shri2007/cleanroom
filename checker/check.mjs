// Node sandbox: load a copy, run trace lines, report match % (Ali).
//
// Usage: node checker/check.mjs <copy.js> <trace.jsonl> [--tests 1,2,3]
// Prints one JSON report on stdout. Exit code 0 = ran (even at 0%), 2 = could not run.
//
// Copy contract (what Shri's builder must emit): a plain JS file that defines either
//   module.exports = function createCalculator() { return { press(key), state() } }
// or a global `createCalculator`. `press(key)` takes a trace key ("AC", "2", "+", "=", ...)
// and `state()` returns { display, expression, clear_label, active_op }.
//
// The copy runs in a fresh node:vm context: no require, process, fs or network, and
// every call has a time limit. A fresh calculator is made for each trace test (each
// test starts at an AC line), so tests cannot leak state into each other.
import fs from "node:fs";
import vm from "node:vm";

const CALL_TIMEOUT_MS = 500;
// Fields compared against the trace. A null in the trace means "reader saw nothing",
// so that field is skipped for that line rather than counted wrong.
const FIELDS = ["display", "expression", "clear_label", "active_op"];

const norm = (field, v) => {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return field === "display" || field === "expression" ? s.replace(/[,\s]/g, "") : s;
};

function loadCopy(source) {
  const sandbox = { module: { exports: {} }, console: { log() {}, error() {}, warn() {} } };
  sandbox.exports = sandbox.module.exports;
  const ctx = vm.createContext(sandbox, { codeGeneration: { strings: false, wasm: false } });
  new vm.Script(source, { filename: "copy.js" }).runInContext(ctx, { timeout: 2000 });
  const factory = typeof sandbox.module.exports === "function"
    ? sandbox.module.exports
    : sandbox.module.exports?.createCalculator ?? ctx.createCalculator;
  if (typeof factory !== "function") throw new Error("copy exports no createCalculator()");
  return () => {
    const calc = factory();
    if (!calc || typeof calc.press !== "function" || typeof calc.state !== "function")
      throw new Error("createCalculator() must return { press(key), state() }");
    return calc;
  };
}

// Run a copy's method with a time limit. Functions made inside a vm context cannot be
// interrupted from outside, so wrap the call in a script that runs in that same context.
function guarded(fn, ...args) {
  const ctx = vm.createContext({ fn, args });
  return vm.runInContext("fn(...args)", ctx, { timeout: CALL_TIMEOUT_MS });
}

function compare(expected, got) {
  const diffs = [];
  for (const f of FIELDS) {
    const want = norm(f, expected[f]);
    if (want === null) continue;
    const have = norm(f, got?.[f]);
    if (want !== have) diffs.push({ field: f, expected: want, got: have });
  }
  return diffs;
}

export function check(source, lines, onlyTests = null) {
  const make = loadCopy(source);
  const usable = lines.filter((l) => !l.deleted && !l.suspect);
  const skipped = lines.length - usable.length;
  const byTest = new Map();
  for (const l of usable) {
    if (onlyTests && !onlyTests.has(l.test)) continue;
    if (!byTest.has(l.test)) byTest.set(l.test, []);
    byTest.get(l.test).push(l);
  }

  let total = 0, matched = 0;
  const tests = [], mismatches = [];
  for (const [test, tlines] of [...byTest].sort((a, b) => a[0] - b[0])) {
    let calc = null, tMatched = 0, broken = null;
    try { calc = make(); } catch (e) { broken = String(e.message ?? e); }
    for (const l of tlines) {
      total++;
      let diffs, error = null;
      if (broken) {
        error = broken;
      } else {
        try {
          if (l.key !== "none") guarded(() => calc.press(l.key));
          diffs = compare(l, guarded(() => calc.state()));
        } catch (e) {
          error = String(e.message ?? e);
          broken = error; // after a crash the rest of this test cannot be trusted
        }
      }
      if (!error && diffs.length === 0) { matched++; tMatched++; }
      else mismatches.push({ test, seq: l.seq, key: l.key, ...(error ? { error } : { diffs }) });
    }
    tests.push({ test, lines: tlines.length, matched: tMatched });
  }
  return {
    match_pct: total ? Math.round((matched / total) * 10000) / 100 : null,
    matched, total, skipped, tests, mismatches,
  };
}

function main(argv) {
  const [copyPath, tracePath, ...rest] = argv;
  if (!copyPath || !tracePath) {
    console.error("usage: node check.mjs <copy.js> <trace.jsonl> [--tests 1,2,3]");
    return 2;
  }
  let only = null;
  const i = rest.indexOf("--tests");
  if (i >= 0) only = new Set(rest[i + 1].split(",").filter(Boolean).map(Number));
  try {
    const lines = fs.readFileSync(tracePath, "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
    const report = check(fs.readFileSync(copyPath, "utf8"), lines, only);
    console.log(JSON.stringify(report));
    return 0;
  } catch (e) {
    console.log(JSON.stringify({ match_pct: null, error: String(e.message ?? e) }));
    return 2;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) process.exit(main(process.argv.slice(2)));
