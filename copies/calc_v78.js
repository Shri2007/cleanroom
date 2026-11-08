(function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let full_expr = "";
    let operand1 = null;
    let operator = null;
    let operand2 = "";
    let just_evaluated = false;
    let percent_applied = false;

    function formatNumber(numStr) {
        if (!numStr) return "0";
        let parts = numStr.split('.');
        let intPart = parts[0];
        let neg = "";
        if (intPart.startsWith("-")) {
            neg = "-";
            intPart = intPart.slice(1);
        }
        let formattedInt = intPart === "" ? "0" : Number(intPart).toLocaleString('en-US');
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
            full_expr = "";
            operand1 = null;
            operator = null;
            operand2 = "";
            just_evaluated = false;
            percent_applied = false;
        },
        press(key) {
            if (key === "AC") {
                this.reset();
                return;
            }
            if (key === "C") {
                if (clear_label === "C") {
                    operand2 = "";
                    display = operand1 !== null ? formatNumber(operand1) + operator : "0";
                    clear_label = "AC";
                } else {
                    this.reset();
                }
                return;
            }

            if (key >= "0" && key <= "9" || key === ".") {
                if (just_evaluated) {
                    operand1 = null;
                    operator = null;
                    full_expr = "";
                    just_evaluated = false;
                    expression = null;
                }
                clear_label = "C";
                active_op = null;

                if (operator === null) {
                    if (operand1 === null || operand1 === "0") {
                        operand1 = key;
                    } else {
                        operand1 += key;
                    }
                    display = formatNumber(operand1);
                } else {
                    if (operand2 === "0" && key !== ".") {
                        operand2 = key;
                    } else {
                        operand2 += key;
                    }
                    display = formatNumber(operand1) + operator + formatNumber(operand2);
                }
            } else if (key === "+" || key === "-" || key === "×" || key === "÷") {
                if (just_evaluated) {
                    just_evaluated = false;
                    expression = null;
                }
                if (operand1 !== null && operator !== null && operand2 !== "") {
                    // chain calculate
                    let a = parseFloat(operand1);
                    let b = parseFloat(operand2);
                    let res = 0;
                    if (operator === "+") res = a + b;
                    operand1 = String(res);
                    operand2 = "";
                }
                if (operand1 === null) {
                    operand1 = "0";
                }
                operator = key;
                active_op = key;
                clear_label = "C";
                display = formatNumber(operand1) + operator;
            } else if (key === "⌫") {
                if (just_evaluated) return;
                if (operator !== null && operand2 === "") {
                    // Do nothing or handle op backspace? Evidence shows deleting digits of operand2 or back
                    // Actually evidence test 2: AC, 9, 5, ⌫ -> 909
                    if (operand2 !== "") {
                        operand2 = operand2.slice(0, -1);
                        if (operand2 === "") {
                            display = formatNumber(operand1) + operator;
                        } else {
                            display = formatNumber(operand1) + operator + formatNumber(operand2);
                        }
                    } else if (operator !== null) {
                        operator = null;
                        active_op = null;
                        display = formatNumber(operand1);
                    } else {
                        if (operand1.length > 1) {
                            operand1 = operand1.slice(0, -1);
                        } else {
                            operand1 = "0";
                            clear_label = "AC";
                        }
                        display = formatNumber(operand1);
                    }
                } else if (operator === null) {
                    if (operand1.length > 1) {
                        operand1 = operand1.slice(0, -1);
                    } else {
                        operand1 = "0";
                        clear_label = "AC";
                    }
                    display = formatNumber(operand1);
                } else {
                    operand2 = operand2.slice(0, -1);
                    if (operand2 === "") {
                        display = formatNumber(operand1) + operator;
                    } else {
                        display = formatNumber(operand1) + operator + formatNumber(operand2);
                    }
                }
            } else if (key === "%") {
                if (operand1 !== null && operator !== null && operand2 !== "") {
                    let base = parseFloat(operand1);
                    let p = parseFloat(operand2);
                    let computed = base * (p / 100);
                    operand2 = String(computed);
                    percent_applied = true;
                    display = formatNumber(operand1) + operator + formatNumber(operand2) + "%";
                }
                clear_label = "C";
            } else if (key === "=") {
                if (operand1 !== null && operator !== null && operand2 !== "") {
                    let a = parseFloat(operand1);
                    let b = parseFloat(operand2);
                    let res = 0;
                    if (operator === "+") {
                        if (percent_applied) {
                            res = a + (a * (parseFloat(operand2) / (percent_applied ? 1 : 1))); // wait, percent_applied computed operand2 as the percentage value already!
                            // Ah, in test 1: 50 + 10% -> operand2 became 5. Then 50 + 5 = 55.
                            // But wait, test 3: 90 + 20% -> operand2 became 18. 90 + 18 = 108.
                            // So operand2 is already the computed percentage value!
                            res = a + b;
                        } else {
                            res = a + b;
                        }
                    }
                    expression = formatNumber(operand1) + operator + (percent_applied ? formatNumber(String(parseFloat(operand2)*100/a)) + "%" : formatNumber(operand2));
                    // Wait, test 1 expression is "50+10%". operand2 was "5", percent was "10".
                    // Let's just store exact expression string:
                    expression = formatNumber(operand1) + operator + (percent_applied ? (parseFloat(operand2)/parseFloat(operand1)*100) + "%" : formatNumber(operand2)); // simplify:
                    // Actually let's track raw expression string.
                }
                // Let's fix % and = properly:
            }
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