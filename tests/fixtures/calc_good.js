// Reference calculator copy used to prove the checker works (iPhone-style behaviour).
module.exports = function createCalculator() {
  let display = "0", acc = null, op = null, fresh = true, activeOp = null, dirty = false;
  const apply = (a, b, o) => (o === "+" ? a + b : o === "-" ? a - b : o === "×" ? a * b : b === 0 ? NaN : a / b);
  return {
    press(key) {
      if (/^[0-9]$/.test(key)) {
        display = fresh || display === "0" ? key : display + key;
        fresh = false; activeOp = null; dirty = true;
      } else if (key === "AC" || key === "C") {
        display = "0"; acc = null; op = null; fresh = true; activeOp = null; dirty = false;
      } else if ("+-×÷".includes(key)) {
        if (op && !fresh) acc = apply(acc, Number(display), op); else acc = Number(display);
        display = String(acc); op = key; activeOp = key; fresh = true;
      } else if (key === "=") {
        if (op) { display = String(apply(acc, Number(display), op)); op = null; acc = null; }
        fresh = true; activeOp = null;
      }
    },
    state() {
      return { display, expression: null, clear_label: dirty ? "C" : "AC", active_op: activeOp };
    },
  };
};
