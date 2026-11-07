// Node sandbox: load a copy, run trace lines, report match % (Ali).
//
// Usage: node checker/check.mjs <copy.js> <trace.jsonl> [--tests 1,2,3] [--mode calc|cal]
// Prints one JSON report on stdout. Exit code 0 = ran (even at 0%), 2 = could not run.
//
// Copy contract (what Shri's builder must emit): a plain JS file that defines either
//   module.exports = function createCalculator() { return { press(key), state() } }
// or a global `createCalculator`. `press(key)` takes a trace key ("AC", "2", "+", "=", ...)
// and `state()` returns { display, expression, clear_label, active_op }.
//
//
// Cal mode (traces whose lines all have source "cal", see explorer/cal_runner.py): the copy is
//   module.exports = function cal(month, year) { return "<text cal prints>" }
// (or module.exports = { cal }, or a global `cal`). Mode is picked from the trace, or forced
// with --mode calc|cal. Output is compared per line with trailing spaces and trailing blank
// lines ignored, because real cal pads its rows.
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

function runInSandbox(source) {
  // Nothing made in this (host) realm may be visible inside the sandbox: a host function's
  // .constructor is the host Function, which reaches `process` and the environment. So the
  // sandbox starts empty and module/exports/console are built inside it.
  const ctx = vm.createContext(Object.create(null), { codeGeneration: { strings: false, wasm: false } });
  vm.runInContext(
    "var module = { exports: {} }; var exports = module.exports;" +
    "var console = { log() {}, error() {}, warn() {}, info() {}, debug() {} };",
    ctx,
  );
  new vm.Script(source, { filename: "copy.js" }).runInContext(ctx, { timeout: 2000 });
  return { ctx, exported: vm.runInContext("module.exports", ctx) };
}

function loadCopy(source) {
  const { ctx, exported } = runInSandbox(source);
  const factory = typeof exported === "function" ? exported : exported?.createCalculator ?? ctx.createCalculator;
  if (typeof factory !== "function") throw new Error("copy exports no createCalculator()");
  return () => {
    const calc = factory();
    if (!calc || typeof calc.press !== "function" || typeof calc.state !== "function")
      throw new Error("createCalculator() must return { press(key), state() }");
    return calc;
  };
}

function loadCal(source) {
  const { ctx, exported } = runInSandbox(source);
  const fn = typeof exported === "function" ? exported : exported?.cal ?? ctx.cal;
  if (typeof fn !== "function") throw new Error("copy exports no cal(month, year)");
  return fn;
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

// Real cal pads every row with spaces and always prints 6 week rows; ignore both.
const calNorm = (t) => String(t ?? "").split("\n").map((r) => r.replace(/\s+$/, "")).join("\n").replace(/\n+$/, "");

function checkCal(source, lines, onlyTests) {
  const cal = loadCal(source);
  const usable = lines.filter((l) => !l.deleted && !l.suspect && (!onlyTests || onlyTests.has(l.test)));
  const skipped = lines.length - usable.length;
  let matched = 0;
  const mismatches = [], perTest = new Map();
  for (const l of usable) {
    const t = perTest.get(l.test) ?? { test: l.test, lines: 0, matched: 0 };
    perTest.set(l.test, t);
    t.lines++;
    const m = /^(\d+) (\d+)$/.exec(String(l.key));
    let error = null, got = null;
    if (!m) error = `bad cal key ${JSON.stringify(l.key)}`;
    else {
      try { got = guarded(() => cal(Number(m[1]), Number(m[2]))); } catch (e) { error = String(e.message ?? e); }
    }
    const want = calNorm(l.display);
    if (!error && calNorm(got) === want) { matched++; t.matched++; }
    else mismatches.push({ test: l.test, seq: l.seq, key: l.key, ...(error ? { error } : { diffs: [{ field: "display", expected: want, got: calNorm(got) }] }) });
  }
  const total = usable.length;
  return {
    mode: "cal",
    match_pct: total ? Math.round((matched / total) * 10000) / 100 : null,
    matched, total, skipped: skipped, tests: [...perTest.values()].sort((a, b) => a.test - b.test), mismatches,
  };
}

export function check(source, lines, onlyTests = null, mode = null) {
  mode ??= lines.length && lines.every((l) => l.source === "cal") ? "cal" : "calc";
  if (mode === "cal") return checkCal(source, lines, onlyTests);
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
    mode: "calc",
    match_pct: total ? Math.round((matched / total) * 10000) / 100 : null,
    matched, total, skipped, tests, mismatches,
  };
}

// Defence in depth: even if a copy escaped the sandbox it would find no keys here.
function scrubEnv() {
  for (const k of Object.keys(process.env)) delete process.env[k];
}

function main(argv) {
  scrubEnv();
  const [copyPath, tracePath, ...rest] = argv;
  if (!copyPath || !tracePath) {
    console.error("usage: node check.mjs <copy.js> <trace.jsonl> [--tests 1,2,3] [--mode calc|cal]");
    return 2;
  }
  let only = null;
  const i = rest.indexOf("--tests");
  if (i >= 0) only = new Set(rest[i + 1].split(",").filter(Boolean).map(Number));
  const mi = rest.indexOf("--mode");
  const mode = mi >= 0 ? rest[mi + 1] : null;
  if (mode !== null && mode !== "calc" && mode !== "cal") {
    console.log(JSON.stringify({ match_pct: null, error: `unknown mode ${JSON.stringify(mode)}` }));
    return 2;
  }
  try {
    const lines = fs.readFileSync(tracePath, "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
    const report = check(fs.readFileSync(copyPath, "utf8"), lines, only, mode);
    console.log(JSON.stringify(report));
    return 0;
  } catch (e) {
    console.log(JSON.stringify({ match_pct: null, error: String(e.message ?? e) }));
    return 2;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) process.exit(main(process.argv.slice(2)));
