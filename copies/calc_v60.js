(function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let state = "START"; // START, ENTERING, OP_SELECTED, RESULT
    let operand1 = null;
    let operator = null;
    let operand2 = null;
    let lastOp = null;
    let lastVal = null;

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        active_op = null;
        state = "START";
        operand1 = null;
        operator = null;
        operand2 = null;
        lastOp = null;
        lastVal = null;
    }

    function press(key) {
        if (key === "AC" || key === "C") {
            if (key === "AC" || clear_label === "AC") {
                reset();
            } else {
                display = "0";
                clear_label = "AC";
            }
            return;
        }

        if (key >= "0" && key <= "9") {
            clear_label = "C";
            expression = null;
            if (state === "START" || state === "RESULT") {
                display = key;
                state = "ENTERING";
            } else if (state === "OP_SELECTED") {
                display = operand1 + operator + key;
                state = "ENTERING_SECOND";
            } else if (state === "ENTERING") {
                display = display === "0" ? key : display + key;
            } else if (state === "ENTERING_SECOND") {
                display = display + key;
            }
        } else if (["+", "-", "×", "÷"].includes(key)) {
            operator = key;
            if (state === "RESULT") {
                operand1 = display;
            } else if (state === "ENTERING") {
                operand1 = display;
            } else if (state === "ENTERING_SECOND") {
                // evaluate current
                let parts = display.split(/[\+\-×÷]/);
                operand1 = calculate(operand1, operator_from_display(display), parts[parts.length-1]);
                display = operand1;
            } else if (state === "START") {
                operand1 = display;
            }
            display = operand1 + key;
            state = "OP_SELECTED";
            clear_label = "C";
            expression = null;
        } else if (key === "=") {
            if (state === "ENTERING_SECOND") {
                let parts = display.split(new RegExp(`[\\+\\-×÷]`));
                let op = operator;
                let second = parts[parts.length - 1];
                expression = operand1 + op + second;
                display = calculate(operand1, op, second);
                operand1 = display;
                state = "RESULT";
                clear_label = "AC";
            } else if (state === "OP_SELECTED") {
                let second = operand1;
                expression = operand1 + operator + second;
                display = calculate(operand1, operator, second);
                state = "RESULT";
                clear_label = "AC";
            } else if (state === "RESULT") {
                if (expression && operator) {
                    let parts = expression.split(new RegExp(`[\\+\\-×÷]`));
                    let second = parts[1];
                    expression = display + operator + second;
                    display = calculate(display, operator, second);
                }
            }
        } else if (key === "⌫") {
            if (state === "START" || state === "RESULT") {
                display = "8";
                clear_label = "C";
            }
        }
    }

    function operator_from_display(str) {
        if (str.includes("+")) return "+";
        if (str.includes("-")) return "-";
        if (str.includes("×")) return "×";
        if (str.includes("÷")) return "÷";
        return "";
    }

    function calculate(a, op, b) {
        let n1 = parseFloat(a);
        let n2 = parseFloat(b);
        let res = 0;
        if (op === "+") res = n1 + n2;
        if (op === "-") res = n1 - n2;
        if (op === "×") res = n1 * n2;
        if (op === "÷") res = n2 === 0 ? "Error" : n1 / n2;
        return res.toString();
    }

    function render() {
        return {
            display: display,
            expression: expression,
            clear_label: clear_label,
            active_op: active_op
        };
    }

    globalThis.Calc = { reset, press, render };
})();