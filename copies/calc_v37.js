(function() {
    let display = "0";
    let expression = "";
    let clear_label = "AC";
    let active_op = null;

    let storedValue = null;
    let pendingOp = null;
    let freshEntry = true;
    let lastOperand = null;
    let lastOp = null;

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
            expression = "";
            clear_label = "AC";
            active_op = null;
            storedValue = null;
            pendingOp = null;
            freshEntry = true;
            lastOperand = null;
            lastOp = null;
        },
        press(key) {
            if (key >= "0" && key <= "9") {
                if (display === "Error") return;
                if (freshEntry || display === "0") {
                    display = key;
                    freshEntry = false;
                } else {
                    display += key;
                }
                clear_label = "C";
            } else if (key === ".") {
                if (display === "Error") return;
                if (freshEntry) {
                    display = "0.";
                    freshEntry = false;
                } else if (!display.includes(".")) {
                    display += ".";
                }
                clear_label = "C";
            } else if (key === "AC") {
                this.reset();
            } else if (key === "C") {
                display = "0";
                clear_label = "AC";
                freshEntry = true;
            } else if (["+", "-", "×", "÷"].includes(key)) {
                if (display === "Error") return;
                let currentVal = parseFloat(display.replace(/,/g, ""));
                if (storedValue !== null && pendingOp !== null && !freshEntry) {
                    let a = storedValue;
                    let b = currentVal;
                    let res = 0;
                    if (pendingOp === "+") res = a + b;
                    if (pendingOp === "-") res = a - b;
                    if (pendingOp === "×") res = a * b;
                    if (pendingOp === "÷") res = b === 0 ? "Error" : a / b;
                    if (res === "Error") {
                        display = "Error";
                        storedValue = null;
                        pendingOp = null;
                    } else {
                        display = String(res);
                        storedValue = res;
                    }
                } else {
                    storedValue = currentVal;
                }
                pendingOp = key;
                active_op = key;
                freshEntry = true;
                expression = "";
            } else if (key === "=") {
                if (display === "Error") return;
                let currentVal = parseFloat(display.replace(/,/g, ""));
                if (pendingOp !== null && storedValue !== null) {
                    lastOperand = currentVal;
                    lastOp = pendingOp;
                    let a = storedValue;
                    let b = currentVal;
                    let res = 0;
                    if (pendingOp === "+") res = a + b;
                    if (pendingOp === "-") res = a - b;
                    if (pendingOp === "×") res = a * b;
                    if (pendingOp === "÷") res = b === 0 ? "Error" : a / b;

                    if (res === "Error") {
                        display = "Error";
                    } else {
                        display = String(res);
                        expression = String(a) + pendingOp + String(b);
                    }
                    storedValue = null;
                    pendingOp = null;
                } else if (lastOp !== null && lastOperand !== null) {
                    let a = currentVal;
                    let b = lastOperand;
                    let res = 0;
                    if (lastOp === "+") res = a + b;
                    if (lastOp === "-") res = a - b;
                    if (lastOp === "×") res = a * b;
                    if (lastOp === "÷") res = b === 0 ? "Error" : a / b;
                    if (res === "Error") {
                        display = "Error";
                    } else {
                        display = String(res);
                        expression = String(a) + lastOp + String(b);
                    }
                }
                active_op = null;
                clear_label = "AC";
                freshEntry = true;
            }
        },
        render() {
            return {
                display: formatNumber(display),
                expression: expression === "" ? null : expression,
                clear_label: clear_label,
                active_op: active_op
            };
        }
    };
})();