globalThis.Calc = (() => {
const S = () => ({ e: null, v: 0, d: "0", a: null, p: null, lo: null, lb: null, ls: null, le: null, x: null, l: "AC", act: null, je: false, err: false, pct: false });
let s = S();
const grp = i => i.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
const fmt = n => {
  if (!isFinite(n) || Number.isNaN(n)) return "Error";
  let r = Math.round(n * 1e10) / 1e10;
  if (r === 0) r = 0;
  if (Math.abs(r) >= 1e15) return String(r);
  const [i, f] = String(r).split(".");
  const neg = i[0] === "-";
  const g = grp(neg ? i.slice(1) : i);
  return (neg ? "-" + g : g) + (f !== undefined ? "." + f : "");
};
const parse = e => {
  if (e === null) return s.v;
  const t = e.replace(/,/g, "");
  if (t === "" || t === "-" || t === "." || t === "-.") return 0;
  return parseFloat(t);
};
const fmtE = e => {
  const neg = e[0] === "-";
  const t = neg ? e.slice(1) : e;
  const [a, b] = t.split(".");
  let i = (a === "" ? "0" : a).replace(/^0+(?=\d)/, "") || "0";
  return (neg ? "-" : "") + grp(i) + (t.includes(".") ? "." + (b ?? "") : "");
};
const calc = (a, o, b) => o === "+" ? a + b : o === "-" ? a - b : o === "×" ? a * b : o === "÷" ? (b === 0 ? NaN : a / b) : b;
const fail = keepX => { s.err = true; s.e = null; s.v = NaN; s.d = "Error"; if (!keepX) s.x = null; s.a = null; s.p = null; s.act = null; s.l = "AC"; s.pct = false; };
const clearAll = () => { s = S(); };
const cur = () => {
  if (s.err) return "Error";
  if (s.e !== null && s.p !== null && !s.je && s.a !== null) {
    const es = fmtE(s.e);
    return fmt(s.a) + s.p + (s.pct ? es + "%" : es === "0" && s.e === null ? "0" : s.pct ? es + "%" : es) === fmt(s.a) + s.p + es + (s.pct ? "%" : "") ? fmt(s.a) + s.p + es + (s.pct ? "%" : "") : "";
  }
  if (s.e !== null) return fmtE(s.e);
  return s.d;
};
const pctVal = raw => s.p === "+" || s.p === "-" ? s.a * raw / 100 : raw / 100;
return {
reset() { clearAll(); },
press(k) {
  if (s.err) { if (k === "AC") clearAll(); return; }
  if (k >= "0" && k <= "9") {
    if (s.je) { const l = s.l; Object.assign(s, S(), { e: k, l: "C" }); return; }
    if (s.e === null || s.pct) { s.e = k; s.pct = false; }
    else if (s.e === "0") s.e = k;
    else if (s.e === "-0") s.e = "-" + k;
    else s.e += k;
    s.l = "C"; return;
  }
  if (k === ".") {
    if (s.je) Object.assign(s, S(), { e: "0.", l: "C" });
    else { if (s.e === null || s.pct) { s.e = "0."; s.pct = false; } else if (!s.e.includes(".")) s.e += "."; s.l = "C"; }
    return;
  }
  if (k === "+/-") {
    if (s.e !== null) s.e = s.e[0] === "-" ? s.e.slice(1) : "-" + s.e;
    else { s.v = -s.v; s.d = fmt(s.v); }
    s.l = "C"; return;
  }
  if (k === "%") {
    if (s.p !== null && s.a !== null && s.e !== null && !s.je) { s.pct = true; s.l = "C"; return; }
    if (s.e !== null) s.e = String(Math.round(parse(s.e) / 100 * 1e10) / 1e10);
    else { s.v /= 100; s.d = fmt(s.v); }
    return;
  }
  if (k === "⌫") {
    if (s.je || s.pct || s.e === null) return;
    s.e = s.e.slice(0, -1);
    if (s.e === "" || s.e === "-" || s.e === "-0") s.e = "0";
    return;
  }
  if (k === "AC") { clearAll(); return; }
  if (k === "C") { if (!s.je && s.p !== null && s.e !== null) { s.e = null; s.pct = false; } return; }
  if (k === "+" || k === "-" || k === "×" || k === "÷") {
    const has = s.e !== null || s.pct;
    if (s.p !== null && has && !s.je && s.a !== null) {
      const b = s.pct ? pctVal(parse(s.e)) : parse(s.e);
      const r = calc(s.a, s.p, b);
      if (!isFinite(r) || Number.isNaN(r)) { fail(false); return; }
      s.a = r; s.v = r; s.d = fmt(r);
    } else if (!(s.p !== null && !has && !s.je)) {
      const v = s.e !== null ? parse(s.e) : s.v;
      s.a = v; s.v = v; s.d = s.e !== null ? fmtE(s.e) : s.d;
    }
    s.p = k; s.act = k; s.e = null; s.pct = false; s.x = null; s.l = "C"; s.je = false;
    return;
  }
  if (k === "=") {
    if (s.p !== null && s.a !== null && !s.je) {
      const raw = s.e !== null ? parse(s.e) : s.a;
      let bS = s.e !== null ? fmtE(s.e) : fmt(s.a);
      let b = s.e === null ? s.a : raw;
      if (s.pct) { b = pctVal(raw); bS += "%"; }
      const r = calc(s.a, s.p, b);
      s.lo = s.p; s.lb = b; s.ls = bS; s.le = fmt(s.a) + s.p + bS;
      if (!isFinite(r) || Number.isNaN(r)) { s.err = true; s.e = null; s.v = NaN; s.d = "Error"; s.x = s.le; s.a = null; s.p = null; s.act = null; s.l = "AC"; s.je = true; s.pct = false; return; }
      s.v = r; s.d = fmt(r); s.x = s.le; s.a = null; s.p = null; s.act = null; s.e = null; s.pct = false; s.l = "AC"; s.je = true;
    } else if (s.lo !== null && s.je) {
      const r = calc(s.v, s.lo, s.lb);
      if (!isFinite(r) || Number.isNaN(r)) { s.err = true; s.d = "Error"; s.x = fmt(s.v) + s.lo + s.ls; s.e = null; s.act = null; s.l = "AC"; s.pct = false; return; }
      s.x = fmt(s.v) + s.lo + s.ls; s.v = r; s.d = fmt(r); s.e = null; s.l = "AC"; s.act = null; s.pct = false;
    } else {
      const v = s.e !== null ? parse(s.e) : s.v;
      if (s.e !== null) { s.v = v; s.d = fmtE(s.e); s.a = v; s.e = null; }
      else s.a = s.v;
      s.p = "×"; s.act = "×"; s.l = "C"; s.je = false; s.x = null; s.pct = false;
    }
  }
},
render() { return { display: cur(), expression: s.x, clear_label: s.l, active_op: s.act }; }
};
})();