globalThis.Calc = {
_e: null,
_a: null,
_p: null,
_j: false,
_x: null,
_lo: null,
_lp: null,
_fd: false,
_n: null,
_f(n) {
if (n === "Error") return "Error";
if (typeof n !== "number" || !isFinite(n) || isNaN(n)) return "Error";
let neg = n < 0;
n = Math.abs(n);
if (n >= 1e9 || (n !== 0 && n < 1e-8)) {
let s = n.toExponential(5).replace(/(\.\d*?)0+e/, "$1e").replace(/\.e/, "e");
return neg ? "-" + s : s;
}
let r = Math.round(n * 1e8) / 1e8;
let parts = String(r).split(".");
parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
let s = parts.join(".");
return neg ? "-" + s : s;
},
_fmtEntry(s) {
if (s === null || s === undefined) return s;
if (s === "Error") return "Error";
let pct = false;
if (s[s.length - 1] === "%") { pct = true; s = s.slice(0, -1); }
if (s === "" || s === "-" || s === "-0" || s === "0.") return s + (pct ? "%" : "");
let neg = s[0] === "-";
let t = neg ? s.slice(1) : s;
if (!/^\d*\.?\d*$/.test(t)) return (neg ? "-" : "") + t + (pct ? "%" : "");
let p = t.split(".");
p[0] = p[0] === "" ? "0" : p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
let out = (neg ? "-" : "") + p.join(".");
if (s[s.length - 1] === "." && out[out.length - 1] !== ".") out += ".";
return out + (pct ? "%" : "");
},
_num(s) {
if (s === null || s === undefined) return 0;
s = String(s);
if (s[s.length - 1] === "%") s = s.slice(0, -1);
if (s === "" || s === "-" || s === "." || s === "-.") return 0;
let v = parseFloat(s.replace(/,/g, ""));
return isNaN(v) ? 0 : v;
},
reset() {
this._e = null; this._a = null; this._p = null; this._j = false; this._x = null; this._lo = null; this._lp = null; this._fd = false; this._n = null;
},
press(k) {
const D = () => this._dispRaw();
if (k >= "0" && k <= "9") {
if (this._j) { this._a = null; this._p = null; this._x = null; this._j = false; this._lo = null; this._lp = null; this._e = null; this._fd = false; this._n = null; }
if (this._e !== null && typeof this._e === "string" && this._e[this._e.length - 1] === "%") return;
if (this._e === null || this._fd) { this._e = k; this._fd = false; this._n = null; }
else {
let t = this._e.replace(/-/, "").replace(/\./, "").replace(/%/, "").replace(/,/g, "");
if (t.length >= 9) return;
this._e += k;
}
return;
}
if (k === ".") {
if (this._j) { this._a = null; this._p = null; this._x = null; this._j = false; this._lo = null; this._lp = null; this._e = "0."; this._n = null; return; }
if (this._e === null || this._fd) { this._e = "0."; this._fd = false; this._n = null; }
else if (this._e.indexOf(".") < 0 && this._e.indexOf("%") < 0) this._e += ".";
return;
}
if (k === "+/-") {
let d = D();
if (d === "0" || d === "Error") return;
if (this._e !== null && !this._fd && this._e[this._e.length - 1] !== "%") {
if (this._e[0] === "-") this._e = this._e.slice(1);
else this._e = "-" + this._e;
} else if (this._j || this._e !== null) {
let v = this._a !== null ? this._a : this._num(this._e || "0");
v = -v; this._a = v; this._e = null; this._fd = true; this._n = null;
}
return;
}
if (k === "%") {
let d = D();
if (d === "Error") return;
if (this._e !== null && !this._fd && this._e[this._e.length - 1] === "%") return;
let curNum = (this._e !== null && !this._fd) ? this._num(this._e) : ((this._a !== null) ? this._a : this._num(d));
let v;
if (this._p === "+" || this._p === "-") { let base = this._a || 0; v = base * curNum / 100; }
else v = curNum / 100;
v = Math.round(v * 1e8) / 1e8;
if (this._e !== null && !this._fd && this._p === null && !this._j) { this._e = String(this._num(this._e) / 100); this._n = null; }
else if (this._e !== null && !this._fd) { this._e = this._e + "%"; this._n = v; }
else { this._a = v; this._e = null; this._fd = true; this._n = null; }
return;
}
if (k === "⌫") {
if (this._j) return;
if (this._e !== null && !this._fd) {
if (this._e.length <= 1 || (this._e.length === 2 && this._e[0] === "-")) this._e = null;
else this._e = this._e.slice(0, -1);
if (this._e !== null && this._e[this._e.length - 1] !== "%") this._n = null;
}
return;
}
if (k === "AC") { this.reset(); return; }
if (k === "C") {
let d = D();
if (d === "7" && this._p === null && !this._j && this._x === null) return;
if (this._j) { this.reset(); return; }
if (this._e !== null && !this._fd) { this._e = null; this._n = null; return; }
this.reset(); return;
}
if (k === "+" || k === "-" || k === "×" || k === "÷") {
if (D() === "Error") { this._p = k; this._j = false; return; }
let cur = (this._e !== null && !this._fd) ? (this._n !== null ? this._n : this._num(this._e)) : (this._fd ? this._a : (this._a !== null ? this._a : this._num(D())));
if (this._p !== null && this._e !== null && !this._fd && !this._j) {
let r = this._calc(this._a, cur, this._p);
if (r === "Error") { this._a = null; this._e = "Error"; this._fd = true; this._p = null; this._x = null; this._n = null; return; }
this._a = r;
} else if (this._e !== null && !this._fd) this._a = cur;
else if (this._a === null) this._a = cur;
this._p = k; this._e = null; this._fd = false; this._j = false; this._x = null; this._n = null;
return;
}
if (k === "=") {
if (D() === "Error") return;
if (this._p !== null) {
let hasSecond = (this._e !== null && !this._fd);
let first = this._a;
let op = this._p;
let sec = hasSecond ? (this._n !== null ? this._n : this._num(this._e)) : first;
let secRaw = hasSecond ? this._fmtEntry(this._e) : this._f(first);
let fstr = this._f(first);
let r = this._calc(first, sec, op);
this._lo = op; this._lp = sec;
if (r === "Error") { this._x = null; this._a = null; this._e = "Error"; this._fd = true; this._p = null; this._j = true; this._n = null; return; }
this._a = r; this._x = fstr + op + secRaw;
this._p = null; this._e = null; this._fd = true; this._j = true; this._n = null;
return;
} else {
if (this._j && this._lo !== null) {
let r = this._calc(this._a, this._lp, this._lo);
if (r === "Error") { this._a = null; this._e = "Error"; this._fd = true; return; }
let fstr = this._f(this._a), sstr = this._f(this._lp);
this._a = r; this._x = fstr + this._lo + sstr;
this._e = null; this._fd = true; return;
}
this._p = "×"; this._j = false; return;
}
}
},
_dispRaw() {
if (this._e !== null && !this._fd) {
let ed = this._fmtEntry(this._e);
if (this._p !== null && this._a !== null) {
return this._f(this._a) + this._p + ed;
}
return ed === "" ? "0" : ed;
}
if (this._e === "Error") return "Error";
if (this._fd) { if (this._e === "Error") return "Error"; if (this._a === "Error") return "Error"; return this._f(this._a); }
if (this._a !== null && this._e === null) return this._f(this._a);
return "0";
},
_calc(a, b, op) {
if (op === "+") return a + b;
if (op === "-") return a - b;
if (op === "×") return a * b;
if (op === "÷") { if (b === 0) return "Error"; return a / b; }
return b;
},
render() {
let d = this._dispRaw();
let disp = d;
let expr = this._x;
let cl;
if (this._j && expr !== null) cl = "AC";
else cl = (disp === "0" ? "AC" : "C");
let ao = this._p;
return { display: disp, expression: expr, clear_label: cl, active_op: ao };
}
};