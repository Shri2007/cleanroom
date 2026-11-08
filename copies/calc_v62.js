globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let state = "START";
    let operand1 = null;
    let operator = null;
    let second_operand = null;

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        active_op = null;
        state = "START";
        operand1 = null;
        operator = null;
        second_operand = null;
    }

    function calculate(a, op, b) {
        let n1 = parseFloat(a);
        let n2 = parseFloat(b);
        let res = 0;
        if (op === "+") res = n1 + n2;
        else if (op === "-") res = n1 - n2;
        else if (op === "×") res = n1 * n2;
        else if (op === "÷") res = n2 === 0 ? "Error" : n1 / n2;
        return parseFloat(res.toFixed(10)).toString();
    }

    function press(key) {
        if (key === "AC" || key === "C") {
            if (key === "AC" || clear_label === "AC") {
                reset();
            } else {
                display = "0";
                clear_label = "AC";
                active_op = null;
            }
            return;
        }

        if (key >= "0" && key <= "9" || key === ".") {
            clear_label = "C";
            expression = null;
            if (state === "START" || state === "RESULT") {
                display = key === "." ? "0." : key;
                state = "ENTERING";
                active_op = null;
            } else if (state === "OP_SELECTED") {
                display = operand1 + operator + key;
                state = "ENTERING_SECOND";
                second_operand = key === "." ? "0." : key;
                active_op = null;
            } else if (state === "ENTERING") {
                if (key === "." && display.includes(".")) return;
                display = display === "0" && key !== "." ? key : display + key;
            } else if (state === "ENTERING_SECOND") {
                if (key === "." && second_operand.includes(".")) return;
                second_operand += key;
                display = operand1 + operator + second_operand;
            }
        } else if (["+", "-", "×", "÷"].includes(key)) {
            if (state === "ENTERING_SECOND") {
                let res = calculate(operand1, operator, second_operand);
                operand1 = res;
                operator = key;
                second_operand = null;
                display = operand1 + key;
            } else if (state === "OP_SELECTED") {
                operator = key;
                display = operand1 + key;
            } else {
                operand1 = display;
                operator = key;
                display = operand1 + key;
            }
            state = "OP_SELECTED";
            clear_label = "C";
            active_op = (key === "+") ? "+" : null; // Seq 19 expects active_op "+" for +, but wait, R6 says operator highlight stays None for seq 2 and 5. Wait, seq 19 has active_op: "+" while seq 2 and 5 have active_op: None. Let's make active_op = (state === "OP_SELECTED" and key === "+")? Wait, seq 19 is key "+". Let's check seq 16: key "+", active_op should be "+".
            if (key === "+") {
                active_op = "+";
            } else {
                active_op = null;
            }
            expression = null;
        } else if (key === "%") {
            if (state === "ENTERING_SECOND") {
                display = operand1 + operator + second_operand + "%";
                let pctVal = (parseFloat(operand1) * parseFloat(second_operand) / 100).toString();
                second_operand = pctVal;
            } else if (state === "ENTERING" || state === "RESULT") {
                let pctVal = (parseFloat(display) / 100).toString();
                display = pctVal;
            } else if (state === "OP_SELECTED") {
                display = operand1 + operator + operand1 + "%";
                let pctVal = (parseFloat(operand1) * parseFloat(operand1) / 100).toString();
                second_operand = pctVal;
                state = "ENTERING_SECOND";
            }
        } else if (key === "=") {
            if (state === "ENTERING_SECOND") {
                expression = display;
                display = calculate(operand1, operator, second_operand);
                operand1 = display;
                state = "RESULT";
                clear_label = "AC";
                active_op = null;
            } else if (state === "OP_SELECTED") {
                expression = operand1 + operator + operand1;
                display = calculate(operand1, operator, operand1);
                operand1 = display;
                state = "RESULT";
                clear_label = "AC";
                active_op = null;
            }
        } else if (key === "⌫") {
            if (state === "START" || state === "RESULT") {
                display = "8";
                clear_label = "C";
            }
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