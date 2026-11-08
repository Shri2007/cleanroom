(function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let currentVal = "0";
    let prevVal = null;
    let op = null;
    let waitingForOperand = false;
    let lastOpResult = null;
    let lastEnteredPercent = false;

    function formatDisplay(valStr) {
        if (valStr === "Error") return "Error";
        if (valStr.endsWith(".")) {
            let numPart = valStr.slice(0, -1);
            return Number(numPart).toLocaleString('en-US') + ".";
        }
        let parts = valStr.split('.');
        let intPart = parts[0];
        let neg = "";
        if (intPart.startsWith("-")) {
            neg = "-";
            intPart = intPart.slice(1);
        }
        if (intPart === "") intPart = "0";
        let formattedInt = Number(intPart).toLocaleString('en-US');
        let res = neg + formattedInt;
        if (parts.length > 1) {
            res += "." + parts[1];
        }
        return res;
    }

    globalThis.Calc = {
        reset() {
            display = "0";
            expression = null;
            clear_label = "AC";
            active_op = null;
            currentVal = "0";
            prevVal = null;
            op = null;
            waitingForOperand = false;
            lastOpResult = null;
            lastEnteredPercent = false;
        },
        press(key) {
            if (key >= "0" && key <= "9") {
                if (clear_label === "AC") {
                    expression = null;
                }
                if (waitingForOperand) {
                    currentVal = key;
                    waitingForOperand = false;
                } else {
                    if (currentVal === "0") {
                        currentVal = key;
                    } else {
                        currentVal += key;
                    }
                }
                clear_label = "C";
                lastEnteredPercent = false;
            } else if (key === ".") {
                if (waitingForOperand) {
                    currentVal = "0.";
                    waitingForOperand = false;
                } else if (!currentVal.includes(".")) {
                    currentVal += ".";
                }
                clear_label = "C";
            } else if (key === "AC") {
                this.reset();
                return;
            } else if (key === "C") {
                currentVal = "0";
                clear_label = "AC";
            } else if (key === "⌫") {
                if (clear_label === "C") {
                    if (currentVal.length > 1) {
                        currentVal = currentVal.slice(0, -1);
                    } else {
                        currentVal = "0";
                        clear_label = "AC";
                    }
                }
            } else if (key === "+") {
                prevVal = currentVal;
                op = "+";
                waitingForOperand = true;
                clear_label = "C";
            } else if (key === "%") {
                if (prevVal !== null && op !== null) {
                    let base = parseFloat(prevVal);
                    let pct = parseFloat(currentVal);
                    let computed = base * (pct / 100);
                    currentVal = String(computed);
                    expression = prevVal + op + currentVal + "%";
                    lastEnteredPercent = true;
                }
                clear_label = "C";
            } else if (key === "=") {
                if (prevVal !== null && op !== null) {
                    let b = parseFloat(prevVal);
                    let c = parseFloat(currentVal);
                    let res = 0;
                    if (op === "+") {
                        if (lastEnteredPercent) {
                            res = b + (b * (c / 100));
                        } else {
                            res = b + c;
                        }
                    }
                    if (!expression) {
                        expression = prevVal + op + currentVal + (lastEnteredPercent ? "%" : "");
                    }
                    currentVal = String(res);
                    prevVal = null;
                    op = null;
                    waitingForOperand = true;
                    clear_label = "AC";
                }
            }
            display = formatDisplay(currentVal);
        },
        render() {
            return {
                display: display,
                expression: expression,
                clear_label: clear_label,
                active_op: active_op
            };
        }
    };
})();