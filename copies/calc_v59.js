globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let lastNum = null;
    let lastOp = null;
    let secondNum = null;
    let hasEvaluated = false;
    let percentApplied = false;

    function parseVal(s) {
        if (!s) return 0;
        if (s.startsWith("(-") && s.endsWith(")")) {
            return -parseFloat(s.slice(2, -1));
        }
        return parseFloat(s);
    }

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        lastNum = null;
        lastOp = null;
        secondNum = null;
        hasEvaluated = false;
        percentApplied = false;
    }

    return {
        reset,
        press(key) {
            if (key === "AC") {
                reset();
                return;
            }
            if (key === "C") {
                if (clear_label === "C") {
                    if (hasEvaluated) {
                        reset();
                    } else if (lastOp && secondNum !== null) {
                        secondNum = null;
                        display = lastNum + lastOp;
                        clear_label = "C";
                    } else {
                        display = "0";
                        clear_label = "AC";
                    }
                }
                return;
            }
            if ((key >= "0" && key <= "9") || key === ".") {
                if (hasEvaluated) {
                    expression = null;
                    lastNum = null;
                    lastOp = null;
                    secondNum = null;
                    display = "0";
                    hasEvaluated = false;
                    percentApplied = false;
                }
                clear_label = "C";
                if (lastOp !== null) {
                    if (secondNum === null) {
                        secondNum = key === "." ? "0." : key;
                    } else {
                        if (key === "." && secondNum.includes(".")) return;
                        if (secondNum === "0" && key !== ".") {
                            secondNum = key;
                        } else {
                            secondNum += key;
                        }
                    }
                    display = lastNum + lastOp + secondNum;
                } else {
                    if (key === "." && display.includes(".")) return;
                    if (display === "0" && key !== ".") {
                        display = key;
                    } else {
                        display += key;
                    }
                }
                return;
            }
            if (["+", "-", "×", "÷"].includes(key)) {
                if (hasEvaluated) {
                    expression = null;
                    hasEvaluated = false;
                }
                if (lastOp !== null && secondNum !== null && !percentApplied) {
                    let res = evaluate(lastNum, lastOp, secondNum);
                    lastNum = res.toString();
                    secondNum = null;
                } else if (lastNum === null || percentApplied || hasEvaluated) {
                    lastNum = display;
                }
                lastOp = key;
                percentApplied = false;
                secondNum = null;
                display = lastNum + lastOp;
                clear_label = "AC";
                return;
            }
            if (key === "+/-") {
                if (display.startsWith("(-")) {
                    display = display.slice(2, -1);
                } else {
                    if (display !== "0") {
                        display = "(-" + display + ")";
                    }
                }
                return;
            }
            if (key === "%") {
                if (lastOp !== null && secondNum !== null && !percentApplied) {
                    percentApplied = true;
                    secondNum = secondNum + "%";
                    display = lastNum + lastOp + secondNum;
                    clear_label = "C";
                }
                return;
            }
            if (key === "=") {
                if (lastOp !== null) {
                    let s2 = secondNum !== null ? secondNum : (lastNum !== null ? lastNum : display);
                    let exprStr = lastNum + lastOp + s2;
                    let res = 0;
                    let base = parseVal(lastNum);
                    let val = parseVal(secondNum !== null ? secondNum : lastNum);
                    if (percentApplied) {
                        if (lastOp === "+") res = base + base * (val / 100);
                        else if (lastOp === "-") res = base - base * (val / 100);
                        else if (lastOp === "×") res = base * (val / 100);
                        else if (lastOp === "÷") res = base / (val / 100);
                    } else {
                        if (lastOp === "+") res = base + val;
                        else if (lastOp === "-") res = base - val;
                        else if (lastOp === "×") res = base * val;
                        else if (lastOp === "÷") res = base / val;
                    }
                    expression = exprStr;
                    display = res.toString();
                    hasEvaluated = true;
                    lastNum = display;
                    secondNum = null;
                    lastOp = null;
                    percentApplied = false;
                    clear_label = "AC";
                } else if (hasEvaluated && expression) {
                    let match = expression.match(/^(.*)([+\-×÷])(.*)$/);
                    if (match) {
                        let op = match[2];
                        let valStr = match[3];
                        let base = parseVal(display);
                        let v = parseVal(valStr);
                        let res = 0;
                        if (op === "+") res = base + v;
                        else if (op === "-") res = base - v;
                        else if (op === "×") res = base * v;
                        else if (op === "÷") res = base / v;
                        expression = display + op + valStr;
                        display = res.toString();
                    }
                }
                return;
            }
        },
        render() {
            return {
                display: display,
                expression: expression,
                clear_label: clear_label,
                active_op: null
            };
        }
    };

    function evaluate(a, op, b) {
        let n1 = parseVal(a);
        let n2 = parseVal(b);
        if (op === "+") return n1 + n2;
        if (op === "-") return n1 - n2;
        if (op === "×") return n1 * n2;
        if (op === "÷") return n1 / n2;
        return n2;
    }
})();