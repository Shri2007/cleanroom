(function() {
  let display = "0";
  let expression = null;
  let clear_label = "AC";
  let active_op = null;

  let storedValue = null;
  let pendingOp = null;
  let freshEntry = true;
  let lastOp = null;
  let lastOperand = null;
  let isError = false;
  let typingSecond = false;

  globalThis.Calc = {
    reset() {
      display = "0";
      expression = null;
      clear_label = "AC";
      active_op = null;
      storedValue = null;
      pendingOp = null;
      freshEntry = true;
      lastOp = null;
      lastOperand = null;
      isError = false;
      typingSecond = false;
    },
    press(key) {
      if (isError) {
        if (key === "AC" || key === "C") {
          this.reset();
        }
        return;
      }

      if (key >= "0" && key <= "9" || key === ".") {
        active_op = null;
        clear_label = "C";
        if (freshEntry) {
          if (pendingOp !== null && !typingSecond) {
            storedValue = display;
            display = key;
            typingSecond = true;
          } else if (display === "0" && key !== ".") {
            display = key;
          } else if (key === ".") {
            if (!display.includes(".")) display += ".";
          } else {
            display += key;
          }
          freshEntry = false;
        } else {
          if (key === ".") {
            if (!display.includes(".")) display += ".";
          } else {
            display += key;
          }
        }
      } else if (key === "AC" || key === "C") {
        if (key === "C" && clear_label === "C" && pendingOp === null) {
          display = "0";
          freshEntry = true;
          typingSecond = false;
        } else {
          this.reset();
        }
      } else if (key === "+" || key === "-" || key === "×" || key === "÷") {
        if (pendingOp !== null && typingSecond && !freshEntry) {
          const res = compute(parseFloat(storedValue), parseFloat(display), pendingOp);
          storedValue = String(res);
          display = storedValue;
        } else {
          storedValue = display;
        }
        pendingOp = key;
        active_op = key;
        freshEntry = true;
        typingSecond = false;
        expression = null;
      } else if (key === "%") {
        if (pendingOp !== null) {
          const base = parseFloat(storedValue);
          const current = freshEntry ? parseFloat(display) : parseFloat(display.slice(storedValue.length + pendingOp.length));
          display = storedValue + pendingOp + current + "%";
          typingSecond = true;
        }
      } else if (key === "=") {
        if (pendingOp !== null) {
          const isPct = display.endsWith("%");
          let secVal;
          if (isPct) {
            const currentStr = display.slice(storedValue.length + pendingOp.length, -1);
            secVal = (parseFloat(storedValue) * parseFloat(currentStr)) / 100;
            expression = storedValue + pendingOp + currentStr + "%";
          } else if (typingSecond && !freshEntry) {
            secVal = parseFloat(display);
            expression = storedValue + pendingOp + secVal;
          } else if (typingSecond && freshEntry) {
            secVal = parseFloat(storedValue);
            expression = storedValue + pendingOp + secVal;
          } else {
            secVal = parseFloat(display);
            expression = display + pendingOp + secVal;
          }
          const res = compute(parseFloat(storedValue), secVal, pendingOp);
          display = String(res);
          lastOp = pendingOp;
          lastOperand = secVal;
          pendingOp = null;
          active_op = null;
          freshEntry = true;
          typingSecond = false;
          clear_label = "AC";
        } else if (lastOp !== null) {
          expression = display + " " + lastOp + " " + lastOperand;
          display = String(compute(parseFloat(display), lastOperand, lastOp));
        } else {
          active_op = null;
          clear_label = "C";
        }
      }

      if (pendingOp !== null && typingSecond) {
        const parts = display.split(pendingOp);
        if (parts.length === 1) {
          display = storedValue + pendingOp + display;
        }
      }
    },
    render() {
      return {
        display: isError ? "Error" : display,
        expression: expression,
        clear_label: clear_label,
        active_op: active_op
      };
    }
  };

  function compute(a, b, op) {
    if (op === "+") return a + b;
    if (op === "-") return a - b;
    if (op === "×") return a * b;
    if (op === "÷") {
      if (b === 0) {
        isError = true;
        return 0;
      }
      return a / b;
    }
    return b;
  }
})();