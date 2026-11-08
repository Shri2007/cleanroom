globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let storedValue = null;
    let pendingOp = null;
    let freshEntry = true;
    let secondOperand = "";
    let typingSecond = false;
    let hasEvaluated = false;
    let lastOp = null;
    let lastOperand = null;

    function formatNumber(numStr) {
        if (numStr === "Error") return "Error";
        if (numStr === null || numStr === undefined) return "0";
        let parts = numStr.split(".");
        let intPart = parts[0];
        let neg = intPart.startsWith("-");
        if (neg) intPart = intPart.slice(1);
        intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        if (neg) intPart = "-" + intPart;
        return parts.length > 1 ? intPart + "." + parts[1] : intPart;
    }

    return {
        reset() {
            display = "0";
            expression = null;
            clear_label = "AC";
            active_op = null;
            storedValue = null;
            pendingOp = null;
            freshEntry = true;
            secondOperand = "";
            typingSecond = false;
            hasEvaluated = false;
            lastOp = null;
            lastOperand = null;
        },
        press(key) {
            if (key >= "0" && key <= "9" || key === ".") {
                clear_label = "C";
                hasEvaluated = false;
                if (typingSecond) {
                    if (key === ".") {
                        if (!secondOperand.includes(".")) {
                            secondOperand = secondOperand === "" ? "0." : secondOperand + ".";
                        }
                    } else {
                        secondOperand = (secondOperand === "0" ? key : secondOperand + key);
                    }
                    display = storedValue + pendingOp + secondOperand;
                    active_op = null;
                } else {
                    if (freshEntry || display === "0") {
                        display = key === "." ? "0." : key;
                        freshEntry = false;
                    } else {
                        if (key === "." && display.includes(".")) return;
                        display += key;
                    }
                }
            } else if (key === "AC") {
                this.reset();
            } else if (key === "C") {
                if (typingSecond) {
                    secondOperand = "";
                    display = storedValue + pendingOp;
                    clear_label = "C";
                } else {
                    display = "0";
                    clear_label = "C";
                    freshEntry = true;
                }
            } else if (["+", "-", "×", "÷"].includes(key)) {
                if (display === "Error") return;
                let valStr = typingSecond && secondOperand !== "" ? secondOperand : display;
                storedValue = valStr.replace(/,/g, "");
                pendingOp = key;
                active_op = key;
                typingSecond = true;
                secondOperand = "";
                clear_label = "C";
                expression = null;
            } else if (key === "=") {
                if (display === "Error") return;
                if (pendingOp !== null && storedValue !== null) {
                    let bVal = typingSecond && secondOperand !== "" ? secondOperand : display.replace(/,/g, "");
                    if (typingSecond && secondOperand === "") {
                        bVal = storedValue;
                    }
                    lastOp = pendingOp;
                    lastOperand = bVal;

                    let a = parseFloat(storedValue);
                    let b = bVal.endsWith("%") ? a * (parseFloat(bVal) / 100) : parseFloat(bVal);
                    let res = 0;
                    if (pendingOp === "+") res = a + b;
                    if (pendingOp === "-") res = a - b;
                    if (pendingOp === "×") res = a * b;
                    if (pendingOp === "÷") res = b === 0 ? "Error" : a / b;

                    if (res === "Error") {
                        display = "Error";
                    } else {
                        expression = storedValue.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + pendingOp + (typingSecond && secondOperand === "" ? storedValue : bVal);
                        display = String(res);
                    }
                    hasEvaluated = true;
                    typingSecond = false;
                    storedValue = null;
                    pendingOp = null;
                    secondOperand = "";
                } else if (hasEvaluated && lastOp !== null && lastOperand !== null) {
                    let a = parseFloat(display.replace(/,/g, ""));
                    let b = parseFloat(lastOperand);
                    let res = 0;
                    if (lastOp === "+") res = a + b;
                    if (lastOp === "-") res = a - b;
                    if (lastOp === "×") res = a * b;
                    if (lastOp === "÷") res = b === 0 ? "Error" : a / b;
                    expression = a + lastOp + lastOperand;
                    display = String(res);
                }
                active_op = null;
                clear_label = "AC";
                freshEntry = true;
            } else if (key === "%") {
                if (typingSecond && pendingOp !== null && storedValue !== null) {
                    let bVal = secondOperand === "" ? "0" : secondOperand;
                    secondOperand = bVal + "%";
                    display = storedValue + pendingOp + secondOperand;
                }
            }
        },
        render() {
            let disp = display;
            if (!disp.includes("+") && !disp.includes("-") && !disp.includes("×") && !disp.includes("÷") && !disp.includes("%")) {
                disp = formatNumber(disp);
            }
            return {
                display: disp,
                expression: expression,
                clear_label: clear_label,
                active_op: active_op
            };
        }
    };
})();