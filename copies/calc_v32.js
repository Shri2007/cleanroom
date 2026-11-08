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
  let secondOperand = null;

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
      secondOperand = null;
    },
    press(key) {
      if (isError) {
        if (key === "AC" || key === "C") {
          this.reset();
        }
        return;
      }

      if (key >= "0" && key <= "9") {
        active_op = null;
        if (freshEntry || display === "0" || (pendingOp !== null && secondOperand === null)) {
          display = key;
          freshEntry = false;
        } else {
          display += key;
        }
        if (pendingOp !== null) {
          secondOperand = display;
        }
        clear_label = "C";
      } else if (key === "AC" || key === "C") {
        if (key === "C" && clear_label === "C") {
          display = "0";
          freshEntry = true;
        } else {
          this.reset();
        }
      } else if (key === "+" || key === "-" || key === "×" || key === "÷") {
        if (pendingOp !== null && secondOperand !== null) {
          const res = compute(parseFloat(storedValue), parseFloat(secondOperand), pendingOp);
          storedValue = res;
          display = String(res);
          secondOperand = null;
        } else {
          storedValue = display;
        }
        pendingOp = key;
        active_op = key;
        freshEntry = true;
        expression = null;
      } else if (key === "%") {
        if (pendingOp !== null && secondOperand !== null) {
          const base = parseFloat(storedValue);
          const pct = (base * parseFloat(secondOperand)) / 100;
          secondOperand = String(pct);
          display = storedValue + pendingOp + secondOperand + "%";
          active_op = null;
        }
      } else if (key === "=") {
        if (pendingOp !== null) {
          const sec = secondOperand !== null ? secondOperand : display;
          const isPct = display.endsWith("%");
          let opVal = parseFloat(sec);
          if (isPct && secondOperand !== null) {
            opVal = (parseFloat(storedValue) * parseFloat(secondOperand)) / 100;
          } else if (pendingOp !== null && secondOperand === null) {
            opVal = parseFloat(display);
          }
          
          expression = storedValue + pendingOp + (isPct ? secondOperand + "%" : sec);
          const res = compute(parseFloat(storedValue), opVal, pendingOp);
          display = String(res);
          lastOp = pendingOp;
          lastOperand = opVal;
          pendingOp = null;
          active_op = null;
          freshEntry = true;
          clear_label = "AC";
          secondOperand = null;
        } else if (lastOp !== null) {
          expression = display + " " + lastOp + " " + lastOperand;
          display = String(compute(parseFloat(display), lastOperand, lastOp));
        } else {
          active_op = "×";
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