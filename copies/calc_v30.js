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
    },
    press(key) {
      if (isError) {
        if (key === "AC" || key === "C") {
          this.reset();
        }
        return;
      }

      if (key >= "0" && key <= "9") {
        if (freshEntry) {
          display = key;
          freshEntry = false;
        } else {
          display = display === "0" ? key : display + key;
        }
        clear_label = "C";
      } else if (key === "AC" || key === "C") {
        if (key === "C" && clear_label === "C") {
          // Rule R6: Pressing C with display 7 left display at 7 (wait, evidence 2 shows C leaves display at 7 if it's C, wait evidence 10 shows C resets to 0? Let's check evidence 2: test 1, key C, display 7, label C, active None. Wait, evidence 10: test 3, key C, display 0, label AC).
          // Actually rule R5 says "Pressing C resets display to 0 and label to AC" (R5), but R6 says "Pressing C with display 7 left display at 7". Wait, standard iOS calculator: pressing C clears current entry to 0, AC clears everything. Here the key is labeled 'C' or 'AC'. If label is 'C', it acts like standard C (clears display to 0, keeps op).
          display = "0";
          clear_label = "AC";
        } else {
          this.reset();
        }
      } else if (key === "+" || key === "-" || key === "×" || key === "÷") {
        const val = parseFloat(display);
        if (pendingOp !== null && !freshEntry) {
          // compute intermediate
          storedValue = compute(storedValue, val, pendingOp);
          display = String(storedValue);
        } else {
          storedValue = val;
        }
        pendingOp = key;
        active_op = key;
        freshEntry = true;
        expression = null;
      } else if (key === "=") {
        const val = parseFloat(display);
        if (pendingOp !== null) {
          expression = storedValue + " " + pendingOp + " " + val;
          storedValue = compute(storedValue, val, pendingOp);
          display = String(storedValue);
          lastOp = pendingOp;
          lastOperand = val;
          pendingOp = null;
          active_op = null;
        } else if (lastOp !== null) {
          expression = display + " " + lastOp + " " + lastOperand;
          display = String(compute(parseFloat(display), lastOperand, lastOp));
        }
        freshEntry = true;
        clear_label = "AC";
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