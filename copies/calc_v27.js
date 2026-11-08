globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let leftVal = null;
    let currentOp = null;
    let waitingForOperand = false;
    let lastInputWasEquals = false;
    let lastRightVal = null;

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        active_op = null;
        leftVal = null;
        currentOp = null;
        waitingForOperand = false;
        lastInputWasEquals = false;
        lastRightVal = null;
    }

    function press(key) {
        if ((key >= '0' && key <= '9') || key === '.') {
            if (lastInputWasEquals) {
                expression = null;
                lastInputWasEquals = false;
                leftVal = null;
                currentOp = null;
            }
            if (waitingForOperand) {
                display = "0";
                waitingForOperand = false;
            }
            if (key === '.') {
                if (!display.includes('.')) {
                    display += '.';
                }
            } else {
                if (display === '0') {
                    display = key;
                } else {
                    display += key;
                }
            }
            clear_label = "C";
        } else if (key === 'AC' || key === 'C') {
            if (key === 'AC' || clear_label === 'AC') {
                reset();
            } else {
                display = "0";
                clear_label = "AC";
            }
        } else if (['+', '-', '×', '÷'].includes(key)) {
            lastInputWasEquals = false;
            leftVal = parseFloat(display);
            currentOp = key;
            active_op = key;
            waitingForOperand = true;
            expression = null;
        } else if (key === '=') {
            if (currentOp !== null) {
                let rightVal = waitingForOperand ? lastRightVal : parseFloat(display);
                if (!waitingForOperand) {
                    lastRightVal = rightVal;
                }
                if (leftVal !== null) {
                    let res = 0;
                    if (currentOp === '+') res = leftVal + rightVal;
                    if (currentOp === '-') res = leftVal - rightVal;
                    if (currentOp === '×') res = leftVal * rightVal;
                    if (currentOp === '÷') res = leftVal / rightVal;

                    expression = leftVal + currentOp + rightVal;
                    display = String(res);
                    leftVal = res;
                }
                active_op = null;
                waitingForOperand = true;
                lastInputWasEquals = true;
                clear_label = "AC";
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