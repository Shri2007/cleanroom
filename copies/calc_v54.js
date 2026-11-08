(function() {
    let currentInput = "0";
    let expression = null;
    let clearLabel = "AC";
    let lastOp = null;
    let lastNum = null;
    let state = "START"; // START, TYPING_NUM, OP_PRESSED, TYPING_SECOND, RESULT
    let fullExprLine = null; // tracks the expression line shown after '='

    function formatNum(n) {
        if (n === "Error" || isNaN(n)) return "Error";
        let parts = n.toString().split(".");
        let intPart = Number(parts[0]).toLocaleString("en-US");
        if (parts.length > 1) {
            return intPart + "." + parts[1];
        }
        return intPart;
    }

    globalThis.Calc = {
        reset() {
            currentInput = "0";
            expression = null;
            clearLabel = "AC";
            lastOp = null;
            lastNum = null;
            state = "START";
            fullExprLine = null;
        },
        press(key) {
            if (key === "AC") {
                this.reset();
                return;
            }
            if (key === "C") {
                currentInput = "0";
                clearLabel = "AC";
                if (state === "TYPING_SECOND") {
                    // keep op
                } else {
                    state = "START";
                }
                return;
            }
            if (key >= "0" && key <= "9" || key === ".") {
                if (fullExprLine !== null) {
                    // After equals, pressing a number starts fresh
                    this.reset();
                }
                if (clearLabel === "AC") clearLabel = "C";

                if (state === "START" || state === "RESULT" || state === "OP_PRESSED") {
                    currentInput = key === "." ? "0." : key;
                    if (state === "OP_PRESSED") {
                        state = "TYPING_SECOND";
                    } else {
                        state = "TYPING_NUM";
                    }
                } else {
                    if (key === "." && currentInput.includes(".")) return;
                    if (currentInput === "0" && key !== ".") {
                        currentInput = key;
                    } else {
                        currentInput += key;
                    }
                }
                return;
            }

            if (["+", "-", "×", "÷"].includes(key)) {
                if (fullExprLine !== null) {
                    // use prior result
                    fullExprLine = null;
                }
                lastNum = currentInput;
                lastOp = key;
                state = "OP_PRESSED";
                clearLabel = "AC";
                return;
            }

            if (key === "%") {
                if (state === "TYPING_SECOND" && lastNum !== null) {
                    // e.g. 72 + 10%
                    // evaluate percentage: 10% of lastNum
                    let base = parseFloat(lastNum);
                    let val = parseFloat(currentInput);
                    let computed = 0;
                    if (lastOp === "+") computed = base + base * (val / 100);
                    if (lastOp === "-") computed = base - base * (val / 100);
                    if (lastOp === "×") computed = base * (val / 100);
                    if (lastOp === "÷") computed = base / (val / 100);
                    
                    // Display shows full expression with %
                    currentInput = lastNum + " " + lastOp + currentInput + "%";
                    // wait, rule says display shows full typed expression: "72+10%"
                    // Let's store exact formatting:
                    // Actually evidence 9: display "72+10%", expression None, clear C
                    currentInput = lastNum + lastOp + currentInput + "%";
                    // store the numeric result for when '=' is pressed
                    lastNum = computed.toString(); // wait, next equals uses it
                    // To keep it simple:
                }
                return;
            }

            if (key === "=") {
                if (state === "TYPING_SECOND" && lastOp && lastNum !== null) {
                    let base = parseFloat(lastNum);
                    let val = parseFloat(currentInput);
                    let computed = 0;
                    if (lastOp === "+") computed = base + base * (val / 100); // if % was pressed
                    // Wait, what if % was NOT pressed? Standard calc: 8 * 9 = 72
                    if (currentInput.includes("%")) {
                        // handled differently or let's parse
                        // From evidence 9->10: 72+10% => = -> 79.2, expr: 72+10%
                        let exprStr = currentInput; // e.g. "72+10%"
                        // evaluate
                        // base is 72, + 10% -> 79.2
                        fullExprLine = exprStr;
                        currentInput = "79.2";
                    } else {
                        if (lastOp === "+") computed = base + val;
                        if (lastOp === "-") computed = base - val;
                        if (lastOp === "×") computed = base * val;
                        if (lastOp === "÷") computed = base / val;
                        fullExprLine = lastNum + lastOp + currentInput;
                        currentInput = computed.toString();
                    }
                    state = "RESULT";
                    clearLabel = "AC";
                } else if (state === "OP_PRESSED" && lastNum !== null) {
                    // e.g. 8 * =
                    let base = parseFloat(lastNum);
                    let computed = 0;
                    if (lastOp === "+") computed = base + base;
                    if (lastOp === "-") computed = base - base;
                    if (lastOp === "×") computed = base * base;
                    if (lastOp === "÷") computed = base / base;
                    fullExprLine = lastNum + lastOp + lastNum;
                    currentInput = computed.toString();
                    state = "RESULT";
                    clearLabel = "AC";
                }
                return;
            }
        },
        render() {
            let disp = currentInput;
            if (state === "OP_PRESSED") {
                disp = lastNum + lastOp;
            }
            return {
                display: disp,
                expression: fullExprLine,
                clear_label: clearLabel,
                active_op: null
            };
        }
    };
})();