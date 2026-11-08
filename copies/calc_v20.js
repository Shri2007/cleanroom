globalThis.Calc = (() => {
const group = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
const round10 = n => Math.round(n * 1e10) / 1e10;
const isBad = n => !isFinite(n) || isNaN(n);
function formatNumber(n) {
  if (isBad(n)) return "Error";
  let r = round10(n);
  if (r === 0) r = 0;
  if (Math.abs(r) >= 1e15) return String(r);
  const [i, f] = String(r).split(".");
  const neg = i.startsWith("-");
  const digits = neg ? i.slice(1) : i;
  const out = (neg ? "-" : "") + group(digits);
  return f !== undefined ? out + "." + f : out;
}
function parseEntryText(text, fallback) {
  if (text === null) return fallback;
  const t = text.replace(/,/g, "");
  if (t === "" || t === "-" || t === "." || t === "-.") return 0;
  return parseFloat(t);
}
function formatEntryText(text) {
  const neg = text.startsWith("-");
  const body = neg ? text.slice(1) : text;
  const [rawInt, frac] = body.split(".");
  let int = rawInt === "" ? "0" : rawInt.replace(/^0+(?=\d)/, "") || "0";
  const out = (neg ? "-" : "") + group(int);
  return body.includes(".") ? out + "." + (frac ?? "") : out;
}
function applyOp(a, op, b) {
  if (op === "+") return a + b;
  if (op === "-") return a - b;
  if (op === "×") return a * b;
  if (op === "÷") return b === 0 ? NaN : a / b;
  return b;
}
function percentValue(base, op, raw) {
  if (op === "+" || op === "-") return base * raw / 100;
  return raw / 100;
}
let entry, shownValue, shownText, acc, pending, lastOp, lastOperand, lastOperandText, lastExpr, expr, clearLabel, activeOp, justEq, failed, pct;
function clearAll() {
  entry = null; shownValue = 0; shownText = "0";
  acc = null; pending = null; lastOp = null; lastOperand = null;
  lastOperandText = null; lastExpr = null; expr = null;
  clearLabel = "AC"; activeOp = null; justEq = false; failed = false; pct = false;
}
function startFreshEntry(text) {
  acc = null; pending = null; lastOp = null; lastOperand = null;
  lastOperandText = null; lastExpr = null; expr = null; activeOp = null;
  justEq = false; failed = false; pct = false; entry = text;
}
function failChain() {
  failed = true; expr = null; activeOp = null; clearLabel = "AC";
  entry = null; shownValue = NaN; shownText = "Error"; acc = null; pending = null; pct = false;
}
function currentDisplay() {
  if (failed) return "Error";
  if (entry !== null && pending !== null && !justEq && acc !== null) {
    const a = formatNumber(acc);
    const e = entry !== null ? formatEntryText(entry) : "0";
    if (pct && entry !== null) return a + pending + e + "%";
    return entry !== null ? a + pending + e : a + pending + "0";
  }
  if (entry !== null) return formatEntryText(entry);
  return shownText;
}
function collapseChain(nextOp) {
  const raw = entry !== null ? parseEntryText(entry, 0) : 0;
  const b = pct ? percentValue(acc, pending, raw) : raw;
  const r = applyOp(acc, pending, b);
  if (isBad(r)) { failChain(); return false; }
  acc = r; shownValue = r; shownText = formatNumber(r);
  return true;
}
function snapshotEntry() {
  const v = entry !== null ? parseEntryText(entry, shownValue) : shownValue;
  const s = entry !== null ? formatEntryText(entry) : shownText;
  acc = v; shownValue = v; shownText = s;
}
clearAll();
return {
  reset() { clearAll(); },
  press(key) {
    if (failed) { if (key === "AC") clearAll(); return; }
    if (key >= "0" && key <= "9") {
      if (justEq) startFreshEntry(key);
      else if (entry === null) { entry = key; pct = false; }
      else if (pct) { pct = false; entry = key; }
      else if (entry === "0") entry = key;
      else if (entry === "-0") entry = "-" + key;
      else entry += key;
      clearLabel = "C"; return;
    }
    if (key === ".") {
      if (justEq) startFreshEntry("0.");
      else if (entry === null) entry = "0.";
      else if (pct) { entry = "0."; pct = false; }
      else if (!entry.includes(".")) entry += ".";
      clearLabel = "C"; return;
    }
    if (key === "+/-") {
      if (entry !== null) entry = entry.startsWith("-") ? entry.slice(1) : "-" + entry;
      else { shownValue = -shownValue; shownText = formatNumber(shownValue); }
      clearLabel = "C"; return;
    }
    if (key === "%") {
      if (pending !== null && acc !== null && entry !== null && !justEq) { pct = true; clearLabel = "C"; return; }
      if (entry !== null) entry = String(round10(parseEntryText(entry, 0) / 100));
      else { shownValue /= 100; shownText = formatNumber(shownValue); }
      return;
    }
    if (key === "⌫") {
      if (justEq || entry === null || pct) return;
      entry = entry.slice(0, -1);
      if (entry === "" || entry === "-" || entry === "-0") entry = "0";
      return;
    }
    if (key === "AC") { clearAll(); return; }
    if (key === "C") {
      if (justEq) return;
      if (pending !== null && entry !== null) { entry = null; pct = false; }
      return;
    }
    if (key === "+" || key === "-" || key === "×" || key === "÷") {
      const hasSecond = entry !== null || pct;
      if (pending !== null && hasSecond && !justEq && acc !== null) { if (!collapseChain(key)) return; }
      else if (!(pending !== null && !hasSecond && !justEq)) snapshotEntry();
      pending = key; activeOp = key; entry = null; pct = false;
      expr = null; clearLabel = "C"; justEq = false; return;
    }
    if (key === "=") {
      if (pending !== null && acc !== null && !justEq) {
        const raw = entry !== null ? parseEntryText(entry, acc) : acc;
        let text = entry !== null ? formatEntryText(entry) : formatNumber(acc);
        let b = raw;
        if (pct) { b = percentValue(acc, pending, raw); text += "%"; }
        else if (entry === null) b = acc;
        const head = formatNumber(acc);
        const r = applyOp(acc, pending, b);
        lastOp = pending; lastOperand = b; lastOperandText = text; lastExpr = head + pending + text;
        if (isBad(r)) {
          failed = true; entry = null; shownValue = NaN; shownText = "Error";
          expr = lastExpr; acc = null; pending = null; activeOp = null;
          clearLabel = "AC"; justEq = true; pct = false; return;
        }
        shownValue = r; shownText = formatNumber(r); expr = lastExpr;
        acc = null; pending = null; activeOp = null; entry = null; pct = false;
        clearLabel = "AC"; justEq = true; return;
      }
      if (lastOp !== null && justEq) {
        const r = applyOp(shownValue, lastOp, lastOperand);
        if (isBad(r)) {
          failed = true; shownText = "Error"; expr = formatNumber(shownValue) + lastOp + lastOperandText;
          entry = null; activeOp = null; clearLabel = "AC"; pct = false; return;
        }
        const head = formatNumber(shownValue);
        shownValue = r; shownText = formatNumber(r);
        expr = head + lastOp + lastOperandText;
        entry = null; clearLabel = "AC"; activeOp = null; pct = false; return;
      }
      snapshotEntry();
      if (entry !== null) entry = null;
      pending = "×"; activeOp = "×"; clearLabel = "C"; justEq = false; expr = null; pct = false;
    }
  },
  render() {
    return { display: currentDisplay(), expression: expr, clear_label: clearLabel, active_op: activeOp };
  }
};
})();