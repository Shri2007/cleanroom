globalThis.Calc = (() => {
  let entry = null;
  let displayVal = 0;
  let displayStr = "0";
  let acc = null;
  let pending = null;
  let lastOp = null;
  let lastOperand = null;
  let lastOperandStr = null;
  let lastExpr = null;
  let expr = null;
  let label = "AC";
  let active = null;
  let justEq = false;
  let error = false;
  let pct = false;
  function fmtNum(n) {
    if (!isFinite(n) || isNaN(n)) return "Error";
    let r = Math.round(n * 1e10) / 1e10;
    if (r === 0) r = 0;
    if (Math.abs(r) >= 1e15) return String(r);
    let parts = String(r).split(".");
    let int = parts[0];
    let neg = int.startsWith("-");
    if (neg) int = int.slice(1);
    int = int.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    if (neg) int = "-" + int;
    if (parts.length > 1) return int + "." + parts[1];
    return int;
  }
  function parseEntry(s) {
    if (s === null) return displayVal;
    let t = s.replace(/,/g, "");
    if (t === "" || t === "-" || t === "." || t === "-.") return 0;
    return parseFloat(t);
  }
  function formatEntry(s) {
    let neg = s.startsWith("-");
    let t = neg ? s.slice(1) : s;
    let parts = t.split(".");
    let int = parts[0] === "" ? "0" : parts[0];
    int = int.replace(/^0+(?=\d)/, "");
    if (int === "") int = "0";
    int = int.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    let out = (neg ? "-" : "") + int;
    if (t.includes(".")) out += "." + (parts[1] !== undefined ? parts[1] : "");
    return out;
  }
  function accStr(v) { return fmtNum(v); }
  function compute(a, op, b) {
    if (op === "+") return a + b;
    if (op === "-") return a - b;
    if (op === "×") return a * b;
    if (op === "÷") { if (b === 0) return NaN; return a / b; }
    return b;
  }
  function secondDisplay() {
    const aS = accStr(acc);
    const eS = entry !== null ? formatEntry(entry) : "0";
    if (pct && entry !== null) return aS + pending + eS + "%";
    if (entry !== null) return aS + pending + eS;
    return aS + pending + "0";
  }
  function curStr() {
    if (error) return "Error";
    if (entry !== null && pending !== null && !justEq && acc !== null) {
      return secondDisplay();
    }
    if (entry !== null) return formatEntry(entry);
    if (pending !== null && acc !== null && !justEq) {
      return accStr(acc) + pending + "0";
    }
    return displayStr;
  }
  return {
    reset() {
      entry = null; displayVal = 0; displayStr = "0";
      acc = null; pending = null; lastOp = null; lastOperand = null;
      lastOperandStr = null; lastExpr = null;
      expr = null; label = "AC"; active = null; justEq = false; error = false; pct = false;
    },
    press(key) {
      if (error) {
        if (key === "AC") {
          entry = null; displayVal = 0; displayStr = "0";
          acc = null; pending = null; lastOp = null; lastOperand = null;
          lastOperandStr = null; lastExpr = null;
          expr = null; label = "AC"; active = null; justEq = false; error = false; pct = false;
        }
        return;
      }
      if (key >= "0" && key <= "9") {
        if (justEq) {
          acc = null; pending = null; lastOp = null; lastOperand = null;
          lastOperandStr = null; lastExpr = null;
          expr = null; active = null; justEq = false; error = false; pct = false;
          entry = key;
        } else {
          if (entry === null) { entry = key; pct = false; }
          else {
            if (pct) { pct = false; entry = key; }
            else if (entry === "0") entry = key;
            else if (entry === "-0") entry = "-" + key;
            else entry += key;
          }
        }
        label = "C";
        return;
      }
      if (key === ".") {
        if (justEq) {
          acc = null; pending = null; lastOp = null; lastOperand = null;
          lastOperandStr = null; lastExpr = null;
          expr = null; active = null; justEq = false; pct = false;
          entry = "0.";
        } else {
          if (entry === null) entry = "0.";
          else if (pct) { entry = "0."; pct = false; }
          else if (!entry.includes(".")) entry += ".";
        }
        label = "C";
        return;
      }
      if (key === "+/-") {
        if (entry !== null) {
          if (entry.startsWith("-")) entry = entry.slice(1);
          else entry = "-" + entry;
        } else {
          displayVal = -displayVal;
          displayStr = fmtNum(displayVal);
        }
        label = "C";
        return;
      }
      if (key === "%") {
        if (pending !== null && acc !== null && entry !== null && !justEq) {
          pct = true;
          label = "C";
          return;
        }
        if (entry !== null) {
          let v = parseEntry(entry) / 100;
          entry = String(Math.round(v * 1e10) / 1e10);
        } else {
          displayVal = displayVal / 100;
          displayStr = fmtNum(displayVal);
        }
        return;
      }
      if (key === "⌫") {
        if (justEq) return;
        if (entry !== null && !pct) {
          entry = entry.slice(0, -1);
          if (entry === "" || entry === "-" || entry === "-0") entry = "0";
        }
        return;
      }
      if (key === "AC") {
        entry = null; displayVal = 0; displayStr = "0";
        acc = null; pending = null; lastOp = null; lastOperand = null;
        lastOperandStr = null; lastExpr = null;
        expr = null; label = "AC"; active = null; justEq = false; error = false; pct = false;
        return;
      }
      if (key === "C") {
        if (justEq) return;
        if (pending !== null && entry !== null) {
          if (pct) { pct = false; entry = null; return; }
          let e = entry.slice(0, -1);
          if (e === "" || e === "-" || e === "-0" || e === "0") {
            if (entry.length <= 1) entry = null;
            else {
              if (e === "" || e === "-") entry = null;
              else entry = e;
            }
            if (entry !== null && (entry === "" || entry === "-")) entry = null;
          } else {
            entry = e;
          }
          return;
        }
        return;
      }
      if (key === "+" || key === "-" || key === "×" || key === "÷") {
        let hasSecond = (entry !== null || pct);
        if (pending !== null && hasSecond && !justEq && acc !== null) {
          let rawB = entry !== null ? parseEntry(entry) : 0;
          let b = rawB;
          if (pct) {
            if (pending === "+" || pending === "-") b = acc * rawB / 100;
            else b = rawB / 100;
          }
          let r = compute(acc, pending, b);
          if (!isFinite(r) || isNaN(r)) {
            error = true; expr = null; active = null; label = "AC";
            entry = null; displayVal = NaN; displayStr = "Error";
            acc = null; pending = null; pct = false;
            return;
          }
          acc = r; displayVal = r; displayStr = fmtNum(r);
        } else if (pending !== null && !hasSecond && !justEq) {
        } else {
          let v = entry !== null ? parseEntry(entry) : displayVal;
          let vS = entry !== null ? formatEntry(entry) : displayStr;
          acc = v; displayVal = v; displayStr = vS;
        }
        pending = key; active = key; entry = null; pct = false;
        expr = null; label = "C"; justEq = false;
        return;
      }
      if (key === "=") {
        if (pending !== null && acc !== null && !justEq) {
          let rawB = entry !== null ? parseEntry(entry) : acc;
          let bS = entry !== null ? formatEntry(entry) : accStr(acc);
          let b = rawB;
          let isPct = pct;
          if (isPct) {
            if (pending === "+" || pending === "-") b = acc * rawB / 100;
            else b = rawB / 100;
            bS = bS + "%";
          } else if (entry === null) {
            b = acc;
          }
          let aS = accStr(acc);
          let r = compute(acc, pending, b);
          lastOp = pending; lastOperand = b; lastOperandStr = bS;
          lastExpr = aS + pending + bS;
          if (!isFinite(r) || isNaN(r)) {
            error = true; entry = null; displayVal = NaN; displayStr = "Error";
            expr = lastExpr; acc = null; pending = null; active = null; label = "AC"; justEq = true; pct = false;
            return;
          }
          displayVal = r; displayStr = fmtNum(r);
          expr = lastExpr;
          acc = null; pending = null; active = null; entry = null; pct = false;
          label = "AC"; justEq = true;
        } else {
          if (lastOp !== null && justEq) {
            let a = displayVal;
            let r = compute(a, lastOp, lastOperand);
            if (!isFinite(r) || isNaN(r)) {
              error = true; displayStr = "Error"; expr = accStr(a) + lastOp + lastOperandStr;
              entry = null; active = null; label = "AC"; pct = false;
              return;
            }
            let aS = accStr(a);
            displayVal = r; displayStr = fmtNum(r);
            expr = aS + lastOp + lastOperandStr;
            entry = null; label = "AC"; active = null; pct = false;
          } else {
            let v = entry !== null ? parseEntry(entry) : displayVal;
            let vS = entry !== null ? formatEntry(entry) : displayStr;
            if (entry !== null) { displayVal = v; displayStr = vS; acc = v; entry = null; }
            else { acc = displayVal; }
            pending = "×"; active = "×"; label = "C"; justEq = false; expr = null; pct = false;
          }
        }
        return;
      }
    },
    render() {
      let d = error ? "Error" : curStr();
      return { display: d, expression: expr, clear_label: label, active_op: active };
    }
  };
})();