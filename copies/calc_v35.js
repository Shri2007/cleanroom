globalThis.Calc = (function() {
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
  let waitingForOperand = false;

  function reset() {
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
    waitingForOperand = false;
  }

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

  return {
    reset,
    press(key) {
      if (isError) {
        if (key === "AC" || key === "C") this.reset();
        return;
      }

      if (key >= "0" && key <= "9" || key === ".") {
        clear_label = "C";
        active_op = null;
        if (freshEntry || waitingForOperand) {
          if (waitingForOperand) {
            storedValue = display.split(/[\+\-×÷]/)[0];
            display = key === "." ? "0." : key;
            waitingForOperand = false;
          } else if (display === "0" && key !== ".") {
            display = key;
          } else if (key === ".") {
            display = "0.";
          } else {
            display = key;
          }
          freshEntry = false;
        } else {
          if (key === "." && display.includes(".")) return;
          if (display === "0" && key !== ".") {
            display = key;
          } else {
            display += key;
          }
        }
      } else if (key === "AC" || key === "C") {
        if (key === "C" && clear_label === "C" && display.length > 0 && display !== "0" && !waitingForOperand) {
          display = "0";
          freshEntry = true;
        } else {
          this.reset();
        }
      } else if (key === "+" || key === "-" || key === "×" || key === "÷") {
        if (pendingOp !== null && !waitingForOperand && !freshEntry) {
          const parts = display.split(pendingOp);
          const a = parseFloat(storedValue);
          const b = parseFloat(parts[parts.length - 1]);
          const res = compute(a, b, pendingOp);
          display = String(res) + key;
          storedValue = String(res);
        } else {
          storedValue = display;
          display = display + key;
        }
        pendingOp = key;
        active_op = key;
        waitingForOperand = true;
        freshEntry = true;
        expression = null;
      } else if (key === "%") {
        if (pendingOp !== null) {
          const parts = display.split(pendingOp);
          const base = parseFloat(storedValue);
          const currentStr = parts[parts.length - 1];
          const pctVal = (base * parseFloat(currentStr)) / 100;
          display = storedValue + pendingOp + currentStr + "%";
        }
      } else if (key === "=") {
        if (pendingOp !== null) {
          const isPct = display.endsWith("%");
          let secVal;
          const parts = display.split(pendingOp);
          const currentStr = parts[parts.length - 1];
          
          if (isPct) {
            secVal = (parseFloat(storedValue) * parseFloat(currentStr.slice(0, -1))) / 100;
            expression = display;
          } else if (waitingForOperand) {
            secVal = parseFloat(storedValue);
            expression = storedValue + pendingOp + secVal;
          } else {
            secVal = parseFloat(currentStr);
            expression = display;
          }
          const res = compute(parseFloat(storedValue), secVal, pendingOp);
          display = String(res);
          lastOp = pendingOp;
          lastOperand = secVal;
          pendingOp = null;
          active_op = null;
          freshEntry = true;
          waitingForOperand = false;
          clear_label = "AC";
        } else if (lastOp !== null) {
          expression = display + " " + lastOp + " " + lastOperand;
          display = String(compute(parseFloat(display), lastOperand, lastOp));
        } else {
          active_op = null;
          clear_label = "C";
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
})();