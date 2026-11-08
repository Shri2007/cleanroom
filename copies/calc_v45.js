globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let leftVal = null;
    let op = null;
    let waitingForOperand = false;
    let lastOp = null;
    let lastOperand = null;

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        active_op = null;
        leftVal = null;
        op = null;
        waitingForOperand = false;
        lastOp = null;
        lastOperand = null;
    }

    function formatNum(n) {
        if (!isFinite(n)) return "Error";
        let str = n.toString();
        if (str.length > 12) {
            str = Number(n.toPrecision(10)).toString();
        }
        return str;
    }

    function press(key) {
        if (key >= "0" && key <= "9") {
            if (display === "Error") {
                display = "0";
            }
            if (waitingForOperand) {
                display = key;
                waitingForOperand = false;
            } else {
                display = display === "0" ? key : display + key;
            }
            clear_label = "C";
            lastOp = null;
            lastOperand = null;
        } else if (key === ".") {
            if (display === "Error") display = "0";
            if (waitingForOperand) {
                display = "0.";
                waitingForOperand = false;
            } else if (!display.includes(".")) {
                display += ".";
            }
            clear_label = "C";
        } else if (key === "AC") {
            reset();
        } else if (key === "C") {
            if (clear_label === "C") {
                display = "0";
                clear_label = "AC";
            } else {
                reset();
            }
        } else if (key === "+" || key === "-" || key === "×" || key === "÷") {
            let currentNum = parseFloat(display);
            if (leftVal !== null && op !== null && !waitingForOperand) {
                leftVal = compute(leftVal, currentNum, op);
                display = formatNum(leftVal);
            } else {
                leftVal = currentNum;
            }
            op = key;
            active_op = key;
            waitingForOperand = true;
            expression = null;
        } else if (key === "=") {
            let currentNum = parseFloat(display);
            if (op !== null) {
                if (!waitingForOperand) {
                    lastOperand = currentNum;
                    lastOp = op;
                }
                let b = lastOperand !== null ? lastOperand : currentNum;
                let a = leftVal !== null ? leftVal : currentNum;
                let res = compute(a, b, op);
                expression = formatNum(a) + op + formatNum(b);
                display = formatNum(res);
                leftVal = res;
                active_op = null;
                waitingForOperand = true;
                op = null;
            } else if (lastOp !== null && lastOperand !== null) {
                let res = compute(parseFloat(display), lastOperand, lastOp);
                expression = formatNum(display) + lastOp + formatNum(lastOperand);
                display = formatNum(res);
                leftVal = res;
            }
            clear_label = "AC";
        } else if (key === "%") {
            let val = parseFloat(display) / 100;
            display = formatNum(val);
        } else if (key === "+/-") {
            if (display !== "0" && display !== "Error") {
                if (display.startsWith("-")) {
                    display = display.substring(1);
                } else {
                    display = "-" + display;
                }
            }
        }
    }

    function compute(a, b, op) {
        switch (op) {
            case "+": return a + b;
            case "-": return a - b;
            case "×": return a * b;
            case "÷": return b === 0 ? NaN : a / b;
            default: return b;
        }
    }

    function render() {
        return {
            display: display,
            expression: expression,
            clear_label: clear_label,
            active_op: active_op
        };
    }

    return { reset, press, render };
})();