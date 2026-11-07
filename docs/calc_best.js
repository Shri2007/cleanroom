// The rebuilt calculator (Ali): one file, two homes.
//
// The checker loads it in a sandbox (`module.exports = createCalculator`), the phone
// page loads it as a plain script (the function declaration is the global). No require,
// no DOM, no globals read, so the same bytes run in both.
//
// Behaviour mirrors the phone model the camera operator checks readings against
// (tests/test_camera_operator.py: class Calculator): 9-digit entry, AC vs C, a pending
// operator that stays lit, "Error" on divide-by-zero, 9 significant digits otherwise.
// That model is what says what the camera should see, so a copy built from it is what
// the trace expects.
function createCalculator() {
  const DIGITS = "0123456789";
  const OPS = "+-×÷";
  let display = "0";
  let clearLabel = "AC";
  let activeOp = null;
  let entry = false; // the display is mid-number: the next digit appends
  let value = 0; // left side of the pending operation
  let pending = null;

  // What the screen holds as a number (the model's _number: unparseable reads as 0).
  const shown = () => {
    const n = Number(display.replace(/,/g, ""));
    return Number.isFinite(n) ? n : 0;
  };
  // The model formats integers plainly and everything else to 9 significant digits.
  const format = (v) => (Number.isInteger(v) ? String(v) : String(Number(v.toPrecision(9))));
  const apply = (a, b, op) =>
    op === "+" ? a + b : op === "-" ? a - b : op === "×" ? a * b : b === 0 ? "Error" : a / b;

  const reset = () => {
    display = "0";
    clearLabel = "AC";
    activeOp = null;
    entry = false;
    value = 0;
    pending = null;
  };

  const press = (key) => {
    if (key === "AC") {
      reset();
    } else if (key === "C") {
      // Clears the entry only: the pending operation survives. The label then falls
      // back to "AC" rather than staying "C" (the camera model keeps "C"): with the
      // entry gone there is nothing left for "C" to clear, and a label that never
      // says "AC" again would leave a stale accumulator with no way to reset.
      display = "0";
      entry = false;
      clearLabel = "AC";
    } else if (key === "⌫") {
      display = display.slice(0, -1) || "0";
      entry = display !== "0";
      clearLabel = "C";
    } else if (key === "+/-") {
      display = format(-shown());
      entry = true;
      clearLabel = "C";
      activeOp = null;
    } else if (key === "%") {
      display = format(shown() / 100);
      entry = true;
      clearLabel = "C";
      activeOp = null;
    } else if (DIGITS.includes(key) || key === ".") {
      if (!entry) {
        display = key === "." ? "0" : key;
        entry = true;
      } else if (key === ".") {
        if (!display.includes(".")) display += ".";
      } else if (display.replace(/^-/, "").replace(/\./g, "").length < 9) {
        // The phone stops taking digits at 9 (server/trace.py: MAX_DIGITS).
        display = display === "0" ? key : display + key;
      }
      clearLabel = "C";
      activeOp = null;
    } else if (OPS.includes(key)) {
      value = shown();
      pending = key;
      activeOp = key;
      entry = false;
      clearLabel = "C";
    } else if (key === "=") {
      if (pending) {
        const result = apply(value, shown(), pending);
        display = result === "Error" ? result : format(result);
        pending = null;
      }
      activeOp = null;
      entry = false;
      clearLabel = "C";
    } else {
      throw new Error("unknown key: " + JSON.stringify(key));
    }
  };

  const state = () => ({
    display,
    expression: null,
    clear_label: clearLabel,
    active_op: activeOp,
  });

  return { reset, press, state, render: state };
}

if (typeof module !== "undefined" && module.exports) module.exports = createCalculator;
// The play page and the brain/checker job contract both use globalThis.Calc.
if (typeof globalThis !== "undefined") globalThis.Calc = createCalculator();
