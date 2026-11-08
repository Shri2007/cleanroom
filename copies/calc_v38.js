(function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let storedValue = null;
    let pendingOp = null;
    let freshEntry = true;
    let lastOperand = null;
    let lastOp = null;
    let typingSecondOperand = false;

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

    globalThis.Calc = {
        reset() {
            display = "0";
            expression = null;
            clear_label = "AC";
            active_op = null;
            storedValue = null;
            pendingOp = null;
            freshEntry = true;
            lastOperand = null;
            lastOp = null;
            typingSecondOperand = false;
        },
        press(key) {
            if (key >= "0" && key <= "9") {
                if (display === "Error") return;
                clear_label = "C";
                if (freshEntry || display === "0") {
                    display = key;
                    freshEntry = false;
                } else {
                    display += key;
                }
                if (typingSecondOperand) {
                    // display should show full expression-like or just the second operand?
                    // Wait, test 3: seq 13 '+', seq 14 '1' -> display is "50+1"
                    // Let's see how display is constructed when typing second operand.
                }
            } else if (key === ".") {
                if (display === "Error") return;
                clear_label = "C";
                if (freshEntry) {
                    display = "0.";
                    freshEntry = false;
                } else if (!display.includes(".")) {
                    display += ".";
                }
            } else if (key === "AC") {
                this.reset();
            } else if (key === "C") {
                display = "0";
                clear_label = "AC";
                freshEntry = true;
                typingSecondOperand = false;
            } else if (["+", "-", "×", "÷"].includes(key)) {
                if (display === "Error") return;
                let currentVal = parseFloat(display.replace(/,/g, ""));
                storedValue = currentVal;
                pendingOp = key;
                active_op = key;
                freshEntry = true;
                clear_label = "C";
                typingSecondOperand = true;
            } else if (key === "=") {
                if (display === "Error") return;
                if (pendingOp !== null && storedValue !== null) {
                    let parts = display.split(/[\+\-×÷]/);
                    let bVal = parseFloat(parts[parts.length - 1].replace(/,/g, ""));
                    lastOperand = bVal;
                    lastOp = pendingOp;
                    let a = storedValue;
                    let b = bVal;
                    let res = 0;
                    if (pendingOp === "+") res = a + b;
                    if (pendingOp === "-") res = a - b;
                    if (pendingOp === "×") res = a * b;
                    if (pendingOp === "÷") res = b === 0 ? "Error" : a / b;

                    if (res === "Error") {
                        display = "Error";
                    } else {
                        display = String(res);
                        expression = storedValue + pendingOp + b;
                    }
                    storedValue = null;
                    pendingOp = null;
                }
                active_op = null;
                clear_label = "AC";
                freshEntry = true;
                typingSecondOperand = false;
            } else if (key === "%") {
                if (pendingOp !== null && storedValue !== null) {
                    // percent of storedValue
                    let currentVal = parseFloat(display.split(/[\+\-×÷]/).pop().replace(/,/g, ""));
                    let pctVal = storedValue * (currentVal / 100);
                    let baseDisp = display.slice(0, display.lastIndexOf(currentVal));
                    display = baseDisp + currentVal + "%";
                }
            }

            if (typingSecondOperand && pendingOp !== null) {
                // If we just typed an operator and now typing digits, display should be storedValue + pendingOp + currentEntry
                // Let's handle it simply: when operator pressed, remember base. When digit pressed after op, display = storedValue + pendingOp + digit.
            }
        },
        render() {
            return {
                display: display.includes("+") || display.includes("-") || display.includes("×") || display.includes("÷") || display.includes("%") ? display : formatNumber(display),
                expression: expression,
                clear_label: clear_label,
                active_op: active_op
            };
        }
    };
})();