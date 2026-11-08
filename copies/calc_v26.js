globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let leftVal = null;
    let currentOp = null;
    let waitingForOperand = false;
    let lastInputWasEquals = false;

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        active_op = null;
        leftVal = null;
        currentOp = null;
        waitingForOperand = false;
        lastInputWasEquals = false;
    }

    function press(key) {
        if ((key >= '0' && key <= '9') || key === '.') {
            if (lastInputWasEquals) {
                display = "0";
                expression = null;
                lastInputWasEquals = false;
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
        } else if (key === '=') {
            if (currentOp !== null && leftVal !== null) {
                let rightVal = parseFloat(display);
                let res = 0;
                if (currentOp === '+') res = leftVal + rightVal;
                if (currentOp === '-') res = leftVal - rightVal;
                if (currentOp === '×') res = leftVal * rightVal;
                if (currentOp === '÷') res = leftVal / rightVal;

                expression = leftVal + currentOp + rightVal;
                display = String(res);
                active_op = null;
                currentOp = null;
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