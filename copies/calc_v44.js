globalThis.Calc = (() => {
const grp = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
const r10 = n => Math.round(n * 1e10) / 1e10;
const fmtNum = n => {
  if (!isFinite(n) || Number.isNaN(n)) return "Error";
  let r = r10(n); if (r === 0) r = 0;
  if (Math.abs(r) >= 1e15) return String(r);
  const [a, b] = String(r).split(".");
  const m = a.startsWith("-") ? "-" + grp(a.slice(1)) : grp(a);
  return b === undefined ? m : m + "." + b;
};
const toNum = s => {
  if (s === null) return st.v;
  const t = s.replace(/,/g, "");
  if (t === "" || t === "-" || t === "." || t === "-.") return 0;
  return parseFloat(t);
};
const fmtEnt = s => {
  const neg = s.startsWith("-"), t = neg ? s.slice(1) : s, [a, b] = t.split(".");
  let i = a === "" ? "0" : a.replace(/^0+(?=\d)/, "");
  if (i === "") i = "0";
  return (neg ? "-" : "") + grp(i) + (t.includes(".") ? "." + (b ?? "") : "");
};
const apply = (a, op, b) => op === "+" ? a + b : op === "-" ? a - b : op === "×" ? a * b : op === "÷" ? (b === 0 ? NaN : a / b) : b;
const pctMix = (a, op, r) => (op === "+" || op === "-") ? a * r / 100 : r / 100;
const st = {};
const wipe = () => Object.assign(st, { e: null, v: 0, vs: "0", acc: null, pend: null, lop: null, lb: null, lbs: null, lexp: null, exp: null, lab: "AC", act: null, eq: false, err: false, pct: false });
const srcVal = () => st.e !== null ? toNum(st.e) : st.v;
const fail = keep => { st.err = true; st.e = null; st.v = NaN; st.vs = "Error"; st.acc = null; st.pend = null; st.act = null; st.lab = "AC"; st.pct = false; if (!keep) st.exp = null; };
const view = () => {
  if (st.err) return "Error";
  if (st.e !== null && st.pend !== null && !st.eq && st.acc !== null) return fmtNum(st.acc) + st.pend + (st.pct ? fmtEnt(st.e) + "%" : fmtEnt(st.e));
  if (st.e !== null) return fmtEnt(st.e);
  return st.vs;
};
wipe();
const digit = k => {
  if (st.eq) { wipe(); st.e = k; st.lab = "C"; st.eq = false; return; }
  if (st.e === null) { st.e = k; st.pct = false; }
  else if (st.pct) { st.pct = false; st.e = k; }
  else if (st.e === "0") st.e = k;
  else if (st.e === "-0") st.e = "-" + k;
  else st.e += k;
  st.lab = "C";
};
const dot = () => {
  if (st.eq) { wipe(); st.e = "0."; st.lab = "C"; return; }
  if (st.e === null) st.e = "0.";
  else if (st.pct) { st.e = "0."; st.pct = false; }
  else if (!st.e.includes(".")) st.e += ".";
  st.lab = "C";
};
const neg = () => { if (st.e !== null) st.e = st.e.startsWith("-") ? st.e.slice(1) : "-" + st.e; else { st.v = -st.v; st.vs = fmtNum(st.v); } st.lab = "C"; };
const pct = () => {
  if (st.pend !== null && st.acc !== null && st.e !== null && !st.eq) { st.pct = true; st.lab = "C"; return; }
  if (st.e !== null) st.e = String(r10(toNum(st.e) / 100)); else { st.v = st.v / 100; st.vs = fmtNum(st.v); }
};
const back = () => { if (st.eq || st.e === null || st.pct) return; st.e = st.e.slice(0, -1); if (st.e === "" || st.e === "-" || st.e === "-0") st.e = "0"; };
const op = k => {
  const has2 = st.e !== null || st.pct;
  if (st.pend !== null && has2 && !st.eq && st.acc !== null) {
    const raw = st.e !== null ? toNum(st.e) : 0, b = st.pct ? pctMix(st.acc, st.pend, raw) : raw, r = apply(st.acc, st.pend, b);
    if (!isFinite(r) || Number.isNaN(r)) { fail(false); return; }
    st.acc = r; st.v = r; st.vs = fmtNum(r);
  } else if (!(st.pend !== null && !has2 && !st.eq)) { const v = srcVal(); st.acc = v; st.v = v; st.vs = st.e !== null ? fmtEnt(st.e) : st.vs; }
  st.pend = k; st.act = k; st.e = null; st.pct = false; st.exp = null; st.lab = "C"; st.eq = false;
};
const eq = () => {
  if (st.pend !== null && st.acc !== null && !st.eq) {
    const raw = st.e !== null ? toNum(st.e) : st.acc;
    let bs = st.e !== null ? fmtEnt(st.e) : fmtNum(st.acc), b = raw;
    if (st.pct) { b = pctMix(st.acc, st.pend, raw); bs += "%"; } else if (st.e === null) b = st.acc;
    const as = fmtNum(st.acc), r = apply(st.acc, st.pend, b);
    st.lop = st.pend; st.lb = b; st.lbs = bs; st.lexp = as + st.pend + bs;
    if (!isFinite(r) || Number.isNaN(r)) { st.err = true; st.e = null; st.v = NaN; st.vs = "Error"; st.exp = st.lexp; st.acc = null; st.pend = null; st.act = null; st.lab = "AC"; st.eq = true; st.pct = false; return; }
    st.v = r; st.vs = fmtNum(r); st.exp = st.lexp; st.acc = null; st.pend = null; st.act = null; st.e = null; st.pct = false; st.lab = "AC"; st.eq = true;
  } else if (st.lop !== null && st.eq) {
    const a = st.v, r = apply(a, st.lop, st.lb);
    if (!isFinite(r) || Number.isNaN(r)) { st.err = true; st.vs = "Error"; st.exp = fmtNum(a) + st.lop + st.lbs; st.e = null; st.act = null; st.lab = "AC"; st.pct = false; return; }
    st.exp = fmtNum(a) + st.lop + st.lbs; st.v = r; st.vs = fmtNum(r); st.e = null; st.lab = "AC"; st.act = null; st.pct = false;
  } else { const v = srcVal(), s = st.e !== null ? fmtEnt(st.e) : st.vs; if (st.e !== null) { st.v = v; st.vs = s; st.acc = v; st.e = null; } else st.acc = st.v; st.pend = "×"; st.act = "×"; st.lab = "C"; st.eq = false; st.exp = null; st.pct = false; }
};
return {
  reset: wipe,
  press(k) {
    if (st.err) { if (k === "AC") wipe(); return; }
    if (k >= "0" && k <= "9") return digit(k);
    if (k === ".") return dot();
    if (k === "+/-") return neg();
    if (k === "%") return pct();
    if (k === "⌫") return back();
    if (k === "AC") return wipe();
    if (k === "C") { if (st.eq) return; if (st.pend !== null && st.e !== null) { st.e = null; st.pct = false; } return; }
    if (k === "+" || k === "-" || k === "×" || k === "÷") return op(k);
    if (k === "=") return eq();
  },
  render() { return { display: view(), expression: st.exp, clear_label: st.lab, active_op: st.act }; }
};
})();