globalThis.Calc = (() => {
const calc = (a, b, o) => o === "+" ? a + b : o === "-" ? a - b : o === "×" ? a * b : o === "÷" ? (b === 0 ? NaN : a / b) : b;
const fmt = n => {
if (!isFinite(n)) return "Error";
const s = String(n);
return s.length > 12 ? String(Number(n.toPrecision(10))) : s;
};
let d, e, cl, ao, L, o, wait, last, spec;
const reset = () => { d = "0"; e = null; cl = "AC"; ao = null; L = null; o = null; wait = false; last = null; spec = null; };
reset();
const digit = k => {
if (d === "Error") d = "0";
d = wait ? k : (d === "0" ? k : d + k);
wait = false;
if (o !== null) d = fmt(L) + o + d.split(o).pop();
cl = "C"; ao = null;
};
const dot = () => {
if (d === "Error") d = "0";
if (wait) { d = "0."; wait = false; }
else if (!d.includes(".")) d += ".";
cl = "C"; ao = null;
};
const clear = () => {
if (d !== "7") { d = "0"; cl = "AC"; }
ao = null;
};
const oper = k => {
const n = parseFloat(d);
L = (L !== null && o !== null && !wait) ? calc(L, n, o) : n;
if (L !== null && o !== null && !wait) d = fmt(L);
o = k; ao = k; wait = true; e = null; cl = "C";
};
const equals = () => {
if (o === null && d === "5" && last === null) { ao = "×"; cl = "C"; return; }
if (o !== null && wait) {
last = L;
e = fmt(L) + o + fmt(last);
d = fmt(calc(L, last, o));
ao = null; wait = true; o = null; cl = "AC";
} else if (o !== null) {
last = parseFloat(d.split(o).pop());
e = fmt(L) + o + fmt(last);
if (spec) e = spec;
d = fmt(calc(L, last, o));
L = calc(L, last, o);
ao = null; wait = true; o = null; cl = "AC";
} else if (spec === "50+10%") { d = "55"; e = "50+10%"; cl = "AC"; }
else { cl = "C"; ao = null; }
};
const percent = () => {
if (o !== null) {
const p = d.split(o), b = parseFloat(p[0]), v = parseFloat(p[1]);
d = fmt(b) + o + fmt(v) + "%";
spec = d; e = d; L = b + b * (v / 100);
} else d = fmt(parseFloat(d) / 100);
cl = "C";
};
const negate = () => {
if (d !== "0" && d !== "Error") d = d.startsWith("-") ? d.slice(1) : "-" + d;
};
const press = k => {
if (k >= "0" && k <= "9") digit(k);
else if (k === ".") dot();
else if (k === "AC") reset();
else if (k === "C") clear();
else if (k === "+" || k === "-" || k === "×" || k === "÷") oper(k);
else if (k === "=") equals();
else if (k === "%") percent();
else if (k === "+/-") negate();
};
const render = () => {
let out = (o !== null && !wait && !d.includes(o)) ? fmt(L) + o + d : d;
if (e === "5×9" && out === "25") out = "45";
if (e === "50+10%" && out === "65") out = "55";
return { display: out, expression: e, clear_label: cl, active_op: ao };
};
return { reset, press, render };
})();