globalThis.Calc = (() => {
  let entry = null; // string being typed, null means not typing (showing acc/result)
  let displayVal = 0; // numeric value currently shown when entry==null
  let displayStr = "0"; // exact shown string when entry==null is formatted
  let acc = null; // pending accumulator
  let pending = null; // '+','-','×','÷'
  let lastOp = null;
  let lastOperand = null;
  let expr = null;
  let label = "AC";
  let active = null;
  let justEq = false;
  let error = false;

  function fmtNum(n) {
    if (!isFinite(n) || isNaN(n)) return "Error";
    if (Math.abs(n) >= 1e12 || (n !== 0 && Math.abs(n) < 1e-9)) {
      // exponential fallback, keep short
      let s = String(n);
      return s;
    }
    // round floating errors
    let r = Math.round(n * 1e10) / 1e10;
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
    // remove commas
    let t = s.replace(/,/g, "");
    if (t === "" || t === "-" || t === "." || t === "-.") return 0;
    return parseFloat(t);
  }
  function formatEntry(s) {
    // add commas to integer part, keep typed decimals
    let neg = s.startsWith("-");
    let t = neg ? s.slice(1) : s;
    let parts = t.split(".");
    let int = parts[0] === "" ? "0" : parts[0];
    // strip leading zeros but keep one
    int = int.replace(/^0+(?=\d)/, "");
    int = int.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    let out = (neg ? "-" : "") + int;
    if (t.includes(".")) {
      out += "." + (parts[1] !== undefined ? parts[1] : "");
    }
    return out;
  }
  function curVal() {
    if (error) return NaN;
    if (entry !== null) return parseEntry(entry);
    return displayVal;
  }
  function curStr() {
    if (error) return "Error";
    if (entry !== null) return formatEntry(entry);
    return displayStr;
  }
  function accStr(v) {
    return fmtNum(v);
  }
  function compute(a, op, b) {
    if (op === "+") return a + b;
    if (op === "-") return a - b;
    if (op === "×") return a * b;
    if (op === "÷") {
      if (b === 0) return NaN;
      return a / b;
    }
    return b;
  }

  return {
    reset() {
      entry = null;
      displayVal = 0;
      displayStr = "0";
      acc = null;
      pending = null;
      lastOp = null;
      lastOperand = null;
      expr = null;
      label = "AC";
      active = null;
      justEq = false;
      error = false;
    },
    press(key) {
      if (error && key !== "AC") {
        if (key === "C") return;
        // allow AC only? iPhone allows clear; let AC reset
        return;
      }
      if (key >= "0" && key <= "9") {
        if (justEq) {
          // start new calculation
          acc = null; pending = null; lastOp = null; lastOperand = null;
          expr = null; active = null; justEq = false;
          error = false;
          entry = key;
        } else {
          if (entry === null) entry = key;
          else {
            // replace leading zero
            if (entry === "0") entry = key;
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
          expr = null; active = null; justEq = false;
          entry = "0.";
        } else {
          if (entry === null) entry = "0.";
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
          if (error) return;
          displayVal = -displayVal;
          displayStr = fmtNum(displayVal);
        }
        label = "C";
        return;
      }
      if (key === "%") {
        if (entry !== null) {
          let v = parseEntry(entry) / 100;
          // keep as typed? format
          entry = String(v);
          // avoid exponential issues: use plain
          if (entry.includes("e")) entry = String(parseFloat(entry));
        } else {
          displayVal = displayVal / 100;
          displayStr = fmtNum(displayVal);
        }
        return;
      }
      if (key === "⌫") {
        if (justEq) return;
        if (entry !== null && entry.length > 0) {
          entry = entry.slice(0, -1);
          if (entry === "" || entry === "-" || entry === "-0") entry = "0";
          // if entry becomes "0" keep typing? keep as "0"
        }
        return;
      }
      if (key === "AC") {
        entry = null;
        displayVal = 0; displayStr = "0";
        acc = null; pending = null; lastOp = null; lastOperand = null;
        expr = null; label = "AC"; active = null; justEq = false; error = false;
        return;
      }
      if (key === "C") {
        // observed: no-op (keeps display/label)
        return;
      }
      if (key === "+" || key === "-" || key === "×" || key === "÷") {
        if (error) return;
        let v = curVal();
        let vS = curStr();
        if (pending !== null && entry !== null && !justEq) {
          // chain compute
          let r = compute(acc, pending, v);
          if (!isFinite(r) || isNaN(r)) {
            error = true; expr = null; active = null; label = "AC";
            entry = null; displayVal = NaN; displayStr = "Error";
            acc = null; pending = null;
            return;
          }
          acc = r;
          displayVal = r; displayStr = fmtNum(r);
        } else if (pending !== null && entry === null && !justEq) {
          // change op, keep acc
        } else {
          acc = v;
          displayVal = v; displayStr = vS;
        }
        pending = key;
        active = key;
        entry = null;
        expr = null;
        label = "C";
        justEq = false;
        return;
      }
      if (key === "=") {
        if (error) return;
        if (pending !== null) {
          let b = curVal();
          let bS = entry !== null ? formatEntry(entry) : displayStr;
          let aS = accStr(acc);
          let r = compute(acc, pending, b);
          lastOp = pending;
          lastOperand = b;
          if (!isFinite(r) || isNaN(r)) {
            error = true;
            entry = null; displayVal = NaN; displayStr = "Error";
            expr = accStr(acc) + pending + bS;
            // expression still shown? keep it
            acc = null; pending = null; active = null; label = "AC"; justEq = true;
            return;
          }
          displayVal = r; displayStr = fmtNum(r);
          expr = aS + pending + bS;
          acc = null; pending = null; active = null;
          entry = null;
          label = "AC";
          justEq = true;
        } else {
          // no pending
          if (lastOp !== null && justEq) {
            let a = displayVal;
            let r = compute(a, lastOp, lastOperand);
            if (!isFinite(r) || isNaN(r)) {
              error = true;
              displayStr = "Error"; expr = accStr(a) + lastOp + accStr(lastOperand);
              entry = null; active = null; label = "AC";
              return;
            }
            let aS = accStr(a);
            displayVal = r; displayStr = fmtNum(r);
            expr = aS + lastOp + accStr(lastOperand);
            entry = null;
            label = "AC";
            active = null;
            // keep justEq true
          } else {
            // lone equals: set active × to match observed, keep display
            // set pending × so subsequent 9 = computes
            let v = curVal();
            let vS = curStr();
            if (entry !== null) {
              displayVal = v; displayStr = vS;
              acc = v;
              entry = null;
            } else {
              acc = displayVal;
            }
            pending = "×";
            active = "×";
            label = "C";
            justEq = false;
            expr = null;
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