"""Spec, copy, fix, pick-test prompts (Shri).

The brain runs on Meta muse-spark-1.3. It never executes model output itself:
copies are scored only inside a Node sandbox (Ali's checker, or the stand-in below).

Run the whole loop on a saved trace:
    uv run python -m server.brain traces/<session>.jsonl
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
COPIES = ROOT / "copies"
SCORES = COPIES / "scores.json"
# Meta with minimal reasoning writes a copy in ~13 s; default reasoning took 4.5 min (tested 12:10).
BRAINS = [  # (name, base_url, key env var, model, extra request args)
    ("meta", "https://api.meta.ai/v1", "MODEL_API_KEY", "muse-spark-1.3", {"reasoning_effort": "minimal"}),
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY",
     "gemini-flash-lite-latest", {"reasoning_effort": "low"}),
]
FIELDS = ("display", "expression", "clear_label", "active_op")
V1_LINES = 10      # v1 sees only the first ~10 taps, so the climb is honest
MAX_ROUNDS = 4
MAX_PROMPT_LINES = 200
BANNED = re.compile(r"\b(require|import|export|process|fetch|XMLHttpRequest|WebSocket|setTimeout|setInterval|"
                    r"eval|Function|globalThis\.constructor)\b")

_clients = {}
last_brain = None  # which model answered the last call, shown on screen


def client(base_url, key_name):
    if key_name not in _clients:
        _clients[key_name] = OpenAI(base_url=base_url, api_key=os.environ[key_name], timeout=60, max_retries=0)
    return _clients[key_name]


def ask(system, user):
    """Meta first; Gemini only if Meta errors or times out."""
    global last_brain
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    errors = []
    for name, base_url, key_name, model, extra in BRAINS:
        if not os.environ.get(key_name):
            continue
        try:
            reply = client(base_url, key_name).chat.completions.create(model=model, messages=messages, **extra)
            last_brain = name
            return reply.choices[0].message.content.strip()
        except Exception as e:  # try the backup, but keep the reason
            errors.append(f"{name}: {type(e).__name__}: {e}"[:200])
    raise RuntimeError("all brains failed: " + "; ".join(errors))


def strip_fences(text):
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.S)
    return (match.group(1) if match else text).strip()


# ---------- evidence ----------

def load(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def usable(lines):
    """Lines the brain may learn from and be scored on: not suspect, not undone.
    A key "none" line is a snapshot with no press; the scorer reads the display without pressing."""
    return [l for l in lines if not l["suspect"] and not l["deleted"]]


def episodes(lines):
    """Renumber `test` so every clear back to 0 (AC, or C showing 0) starts a fresh test.
    People clear with C as often as AC, and the held-out split needs several tests.
    Caveat: C can leave a pending operator, so these ids may not match the trace file.
    Use AC between sequences in real runs."""
    out, test = [], 0
    for l in lines:
        if not out or (l["key"] in ("AC", "C") and l["display"] == "0"):
            test += 1
        out.append({**l, "test": test})
    return out


def split(lines, seed=1, held_frac=0.3):
    """Train / held-out split by test (70/30, seed 1). Returns (train_ids, held_ids)."""
    ids = sorted({l["test"] for l in lines})
    random.Random(seed).shuffle(ids)
    n_held = max(1, math.floor(len(ids) * held_frac)) if len(ids) >= 3 else 0
    return sorted(ids[n_held:]), sorted(ids[:n_held])


def fmt(lines):
    rows = ["seq|test|key|display|expression|clear_label|active_op"]
    rows += ["|".join(str(l.get(k)) for k in ("seq", "test", "key", *FIELDS)) for l in lines[-MAX_PROMPT_LINES:]]
    return "\n".join(rows)


# ---------- the three prompts ----------

def find_rules(lines):
    system = (
        "You reverse-engineer a phone calculator from observed key presses. Each test starts from a "
        "cleared calculator. Use ONLY the evidence. A rule is 'seen' if listed lines show it directly; "
        "anything from general knowledge is 'guessed'. Return JSON only: "
        '{"rules": [{"id": "R1", "rule": "...", "status": "seen", "evidence_seq": [8, 9]}]}. '
        "Cover display formatting, the expression line, the clear key label, operator highlight, "
        "repeated =, %, errors. 6-14 short rules.")
    data = json.loads(strip_fences(ask(system, fmt(lines))))
    rules = data["rules"] if isinstance(data, dict) else data
    return [{"id": str(r["id"]), "rule": str(r["rule"]),
             "status": "seen" if r.get("status") == "seen" else "guessed",
             "evidence_seq": [int(s) for s in r.get("evidence_seq", []) if str(s).isdigit()]}
            for r in rules]


COPY_RULES = (
    "Write ONE plain JavaScript file that defines:\n"
    "globalThis.Calc = { reset() {}, press(key) {}, render() { return {display, expression, clear_label, active_op}; } };\n"
    "Keys: 0-9 . + - × ÷ = % +/- AC C ⌫ (exact strings). render() returns strings exactly as the "
    "phone shows them (same commas, symbols, 'Error' text) or null for fields not shown. "
    "Only display/expression/clear_label/active_op are compared, and only where the observed value is not null. "
    "No import, require, process, fetch, timers, eval or Function. Return only the code.")


def check_code(text):
    code = strip_fences(text)
    if "globalThis.Calc" not in code:
        raise ValueError("copy does not define globalThis.Calc")
    if BANNED.search(code):
        raise ValueError(f"copy uses a banned word: {BANNED.search(code).group(0)}")
    return code


def write_copy(rules, lines):
    user = f"RULES:\n{json.dumps(rules, ensure_ascii=False)}\n\nEVIDENCE:\n{fmt(lines)}"
    return check_code(ask("You build a calculator copy from a spec. " + COPY_RULES, user))


def fix_copy(code, rules, mismatches):
    user = (f"RULES:\n{json.dumps(rules, ensure_ascii=False)}\n\nCURRENT CODE:\n{code}\n\n"
            f"MISMATCHES (expected vs got, per test from reset):\n{json.dumps(mismatches[:20], ensure_ascii=False)}")
    return check_code(ask("You fix a calculator copy so it matches observed behavior. Return the full new file. "
                          + COPY_RULES, user))


def pick_test(rules):
    system = ('Pick ONE short key sequence that would turn a guessed rule into a seen one. Return JSON only: '
              '{"rule_id": "R3", "instruction": "Press AC 2 + 3 = = "}')
    guessed = [r for r in rules if r["status"] == "guessed"] or rules
    return json.loads(strip_fences(ask(system, json.dumps(guessed, ensure_ascii=False))))


# ---------- scoring (Node sandbox) ----------

# Stand-in until Ali's checker/check.mjs lands: same input/output shape, same sandbox rules.
_SCORER = r"""
const vm = require('node:vm');
let buf = '';
process.stdin.on('data', d => buf += d).on('end', () => {
  const {code, lines, target} = JSON.parse(buf);
  if (target === 'cal') return scoreCal(code, lines);
  const fields = ['display', 'expression', 'clear_label', 'active_op'];
  const byTest = new Map();
  for (const l of lines) { if (!byTest.has(l.test)) byTest.set(l.test, []); byTest.get(l.test).push(l); }
  let matched = 0, total = 0; const tests = [], mismatches = [];
  for (const [test, rows] of byTest) {
    let pass = true;
    try {
      const ctx = vm.createContext({}, {codeGeneration: {strings: false, wasm: false}});
      vm.runInContext(code, ctx, {timeout: 1000});
      ctx.rows = rows;
      const got = JSON.parse(vm.runInContext(
        'Calc.reset(); JSON.stringify(rows.map(r => { if (r.key !== "none") Calc.press(r.key); return Calc.render(); }))',
        ctx, {timeout: 1000}));
      rows.forEach((r, i) => {
        total++;
        const g = got[i] || {};
        const bad = fields.filter(f => r[f] != null && String(g[f]) !== String(r[f]));
        if (bad.length) { pass = false; mismatches.push({test, seq: r.seq, key: r.key,
          expected: Object.fromEntries(bad.map(f => [f, r[f]])), got: Object.fromEntries(bad.map(f => [f, g[f] ?? null]))}); }
        else matched++;
      });
    } catch (e) {
      pass = false; total += rows.length;
      mismatches.push({test, seq: rows[0].seq, key: rows[0].key, expected: 'run without error', got: String(e.message || e)});
    }
    tests.push({test, pass});
  }
  process.stdout.write(JSON.stringify({match_pct: total ? Math.round(10000 * matched / total) / 100 : 0,
    matched, total, tests, mismatches}));
});

// cal: one line per (month, year); Cal.run(...args) must equal the output exactly.
function scoreCal(code, lines) {
  let matched = 0; const tests = [], mismatches = [];
  let ctx = null, loadError = null;
  try {
    ctx = vm.createContext({}, {codeGeneration: {strings: false, wasm: false}});
    vm.runInContext(code, ctx, {timeout: 1000});
  } catch (e) { loadError = String(e.message || e); }
  for (const l of lines) {
    let got;
    try {
      if (loadError) throw new Error(loadError);
      ctx.args = l.args;
      got = vm.runInContext('String(Cal.run(args[0], args[1]))', ctx, {timeout: 500});
    } catch (e) { got = 'ERROR: ' + String(e.message || e); }
    const pass = got === l.output;
    if (pass) matched++; else mismatches.push({test: l.test, seq: l.seq, args: l.args, expected: l.output, got});
    tests.push({test: l.test, pass});
  }
  process.stdout.write(JSON.stringify({match_pct: lines.length ? Math.round(10000 * matched / lines.length) / 100 : 0,
    matched, total: lines.length, tests, mismatches}));
}
"""


def _score_standin(code, lines, target="calc"):
    try:
        result = subprocess.run(["node", "--permission", "-e", _SCORER],
                                input=json.dumps({"code": code, "lines": lines, "target": target}), capture_output=True,
                                text=True, timeout=2, env={"PATH": os.environ.get("PATH", "")})
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "match_pct": 0, "mismatches": []}
    if result.returncode:
        return {"error": result.stderr.strip()[:500], "match_pct": 0, "mismatches": []}
    return json.loads(result.stdout)


def score(code, lines, tests):
    subset = [l for l in lines if l["test"] in set(tests)]
    if not subset:
        return {"match_pct": None, "matched": 0, "total": 0, "mismatches": []}
    try:
        from server import checker
        if hasattr(checker, "run"):  # Ali's checker, once it lands
            return checker.run("calc", code, subset)
    except ImportError:
        pass
    return _score_standin(code, subset)


# ---------- the loop ----------

def load_history():
    history = json.loads(SCORES.read_text()) if SCORES.exists() and SCORES.read_text().strip() else {}
    return history if isinstance(history, dict) else {}


def next_version():
    """Versions keep counting across runs, so a rerun never overwrites an old copy."""
    return max((v["version"] for v in load_history().get("calc", [])), default=0) + 1


def save_version(version, code, rules, round_no, train, held, keep):
    COPIES.mkdir(exist_ok=True)
    (COPIES / f"calc_v{version}.js").write_text(code)
    history = load_history()
    history.setdefault("calc", []).append({
        "version": version, "round": round_no, "file": f"calc_v{version}.js",
        "train_pct": train["match_pct"], "held_pct": held["match_pct"], "kept": keep,
        "rules": rules, "time": time.strftime("%H:%M:%S")})
    SCORES.write_text(json.dumps(history, indent=1, ensure_ascii=False))


def run_loop(trace_path, on_event=print):
    lines = episodes(usable(load(trace_path)))
    train_ids, held_ids = split(lines)
    train = [l for l in lines if l["test"] in train_ids]
    on_event({"step": "split", "lines": len(lines), "train_tests": train_ids, "held_tests": held_ids})

    rules = find_rules(train[:V1_LINES])
    on_event({"step": "rules", "rules": rules})
    code = write_copy(rules, train[:V1_LINES])
    best = None
    first_version = next_version()
    for round_no in range(MAX_ROUNDS + 1):
        tr, he = score(code, lines, train_ids), score(code, lines, held_ids)
        improved = best is None or tr["match_pct"] > best["train"]["match_pct"]
        version = first_version + round_no
        save_version(version, code, rules, round_no, tr, he, improved)
        on_event({"step": "score", "version": version, "train_pct": tr["match_pct"],
                  "held_pct": he["match_pct"], "kept": improved, "brain": last_brain, "error": tr.get("error")})
        if improved:
            best = {"version": version, "code": code, "train": tr, "held": he, "stale": 0}
        else:
            best["stale"] += 1
        held_pass = best["held"]["match_pct"] in (None, 100)
        if (best["train"]["match_pct"] == 100 and held_pass) or best["stale"] >= 2 or round_no == MAX_ROUNDS:
            break
        if round_no == 0:  # after v1, the brain gets every training line
            rules = find_rules(train)
            on_event({"step": "rules", "rules": rules})
        try:
            code = fix_copy(best["code"], rules, best["train"]["mismatches"])
        except (ValueError, json.JSONDecodeError) as e:
            on_event({"step": "fix_failed", "error": str(e)})
            break
    on_event({"step": "done", "best_version": best["version"], "train_pct": best["train"]["match_pct"],
              "held_pct": best["held"]["match_pct"]})
    return best


# ---------- cal: the 1970s Unix calendar program ----------

CAL_COPY_RULES = (
    "Write ONE plain JavaScript file that defines:\n"
    "globalThis.Cal = { run(month, year) { return \"<exact text>\"; } };\n"
    "month is 1-12, year 1-9999. Return EXACTLY the text the program prints for that month: same header "
    "centering, same column spacing, same trailing spaces on every line, same number of lines, joined with \\n. "
    "Output is compared character by character. No import, require, process, fetch, timers, eval, Function or "
    "Date. Compute weekdays yourself. Return only the code.")


def normalize_cal(lines):
    """Contract cal lines ({args, output}) or Ali's cal_runner lines ({key: "9 1752", display})."""
    out = []
    for l in lines:
        if l.get("deleted"):
            continue
        args = l.get("args") or [int(x) for x in str(l["key"]).split()]
        output = l["output"] if "output" in l else l["display"]
        out.append({"seq": l["seq"], "test": l["test"], "args": [int(args[0]), int(args[1])], "output": output})
    return out


def fmt_cal(lines):
    # json.dumps keeps spaces and newlines visible, which is where the exact-text rules live
    return "\n".join(json.dumps({"seq": l["seq"], "month_year": l["args"], "output": l["output"]})
                     for l in lines[-MAX_PROMPT_LINES:])


def find_rules_cal(lines):
    system = (
        "You reverse-engineer a command-line calendar program from its outputs for (month, year) inputs. Use ONLY "
        "the evidence. A rule is 'seen' if listed outputs show it directly; anything from general knowledge is "
        "'guessed'. Return JSON only: "
        '{"rules": [{"id": "R1", "rule": "...", "status": "seen", "evidence_seq": [3]}]}. '
        "Cover header format, weekday row, column widths, trailing spaces, line count, month lengths, leap years, "
        "which weekday a month starts on, and anything unusual in a specific month. 6-12 short rules.")
    data = json.loads(strip_fences(ask(system, fmt_cal(lines))))
    rules = data["rules"] if isinstance(data, dict) else data
    return [{"id": str(r["id"]), "rule": str(r["rule"]),
             "status": "seen" if r.get("status") == "seen" else "guessed",
             "evidence_seq": [int(s) for s in r.get("evidence_seq", []) if str(s).isdigit()]}
            for r in rules]


def check_cal_code(text):
    code = strip_fences(text)
    if "globalThis.Cal" not in code:
        raise ValueError("copy does not define globalThis.Cal")
    if BANNED.search(code):
        raise ValueError(f"copy uses a banned word: {BANNED.search(code).group(0)}")
    return code


def write_cal_copy(rules, lines):
    user = f"RULES:\n{json.dumps(rules, ensure_ascii=False)}\n\nEVIDENCE:\n{fmt_cal(lines)}"
    return check_cal_code(ask("You build a calendar program copy from a spec. " + CAL_COPY_RULES, user))


def fix_cal_copy(code, rules, mismatches):
    user = (f"RULES:\n{json.dumps(rules, ensure_ascii=False)}\n\nCURRENT CODE:\n{code}\n\n"
            f"MISMATCHES (expected vs got, exact text):\n{json.dumps(mismatches[:6], ensure_ascii=False)}")
    return check_cal_code(ask("You fix a calendar program copy so its output matches exactly. Return the full new "
                              "file. " + CAL_COPY_RULES, user))


def save_cal_version(version, code, rules, round_no, train, keep):
    COPIES.mkdir(exist_ok=True)
    (COPIES / f"cal_v{version}.js").write_text(code)
    history = load_history()
    history.setdefault("cal", []).append({
        "version": version, "round": round_no, "file": f"cal_v{version}.js", "train_pct": train["match_pct"],
        "held_pct": None, "kept": keep, "rules": rules, "time": time.strftime("%H:%M:%S")})
    SCORES.write_text(json.dumps(history, indent=1, ensure_ascii=False))


def run_cal(lines, on_event=print):
    """Rebuild cal from TRAINING lines only. The verifier agent scores held-out dates on its own,
    so held_pct is None here. Returns {best_version, train_pct, held_pct, rules, code}."""
    lines = normalize_cal(lines)
    if not lines:
        raise ValueError("no cal lines to learn from")
    on_event({"step": "split", "lines": len(lines), "train_tests": sorted({l["test"] for l in lines}),
              "held_tests": []})
    first = lines[:max(3, len(lines) // 2)]  # v1 sees half the evidence, so the climb is honest
    rules = find_rules_cal(first)
    on_event({"step": "rules", "rules": rules})
    code = write_cal_copy(rules, first)
    first_version = max((v["version"] for v in load_history().get("cal", [])), default=0) + 1
    best = None
    for round_no in range(MAX_ROUNDS + 1):
        tr = _score_standin(code, lines, target="cal")
        improved = best is None or tr["match_pct"] > best["train"]["match_pct"]
        version = first_version + round_no
        save_cal_version(version, code, rules, round_no, tr, improved)
        on_event({"step": "score", "version": version, "train_pct": tr["match_pct"], "held_pct": None,
                  "kept": improved, "brain": last_brain, "error": tr.get("error")})
        if improved:
            best = {"version": version, "code": code, "train": tr, "stale": 0}
        else:
            best["stale"] += 1
        if best["train"]["match_pct"] == 100 or best["stale"] >= 2 or round_no == MAX_ROUNDS:
            break
        if round_no == 0:  # after v1, the brain sees every training date
            rules = find_rules_cal(lines)
            on_event({"step": "rules", "rules": rules})
        try:
            code = fix_cal_copy(best["code"], rules, best["train"]["mismatches"])
        except (ValueError, json.JSONDecodeError) as e:
            on_event({"step": "fix_failed", "error": str(e)})
            break
    result = {"best_version": best["version"], "train_pct": best["train"]["match_pct"], "held_pct": None,
              "rules": rules, "code": best["code"]}
    on_event({"step": "done", **{k: v for k, v in result.items() if k != "code"}})
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m server.brain traces/<session>.jsonl")

    def show(event):
        if event["step"] == "rules":
            for r in event["rules"]:
                print(f"  {'✓' if r['status'] == 'seen' else '?'} {r['id']}: {r['rule']}")
        else:
            print(json.dumps(event, ensure_ascii=False))

    run_loop(sys.argv[1], on_event=show)
