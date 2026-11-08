globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    let currentInput = "0";
    let priorExpression = null;
    let lastOperator = null;
    let lastOperand = null;
    let waitingForOperand = false;
    let justCalculated = false;

    function reset() {
        currentInput = "0";
        expression = null;
        priorExpression = null;
        lastOperator = null;
        lastOperand = null;
        waitingForOperand = false;
        justCalculated = false;
        clear_label = "AC";
        display = "0";
        active_op = null;
    }

    function press(key) {
        if ((key >= '0' && key <= '9') || key === '.') {
            if (justCalculated) {
                currentInput = "0";
                expression = null;
                priorExpression = null;
                justCalculated = false;
            }
            if (waitingForOperand) {
                currentInput = key === '.' ? '0.' : key;
                waitingForOperand = false;
            } else {
                if (key === '.' && currentInput.includes('.')) return;
                if (currentInput === '0' && key !== '.') {
                    currentInput = key;
                } else {
                    currentInput += key;
                }
            }
            clear_label = "C";
            if (lastOperator) {
                display = priorExpression + currentInput;
            } else {
                display = currentInput;
            }
        } else if (key === '+' || key === '-' || key === '×' || key === '÷') {
            if (justCalculated) {
                priorExpression = display;
                expression = priorExpression;
                justCalculated = false;
            } else if (lastOperator && !waitingForOperand) {
                // intermediate calculation
                let res = calculate(parseFloat(priorExpression.split(/[\+\-×÷]/)[0]), parseFloat(currentInput), lastOperator);
                currentInput = String(res);
                priorExpression = currentInput + key;
                expression = null;
            } else {
                priorExpression = currentInput + key;
                expression = null;
            }
            lastOperator = key;
            waitingForOperand = true;
            display = priorExpression;
            clear_label = "C";
        } else if (key === '=') {
            if (lastOperator && !waitingForOperand) {
                let parts = display.split(lastOperator);
                let left = parseFloat(parts[0]);
                let right = parseFloat(currentInput);
                let res = calculate(left, right, lastOperator);
                expression = display;
                display = String(res);
                currentInput = String(res);
                lastOperator = null;
                waitingForOperand = true;
                justCalculated = true;
                clear_label = "AC";
            }
        } else if (key === 'AC' || key === 'C') {
            if (key === 'C' && clear_label === 'C') {
                currentInput = "0";
                if (lastOperator) {
                    display = priorExpression;
                } else {
                    display = "0";
                }
                clear_label = "AC";
            } else {
                reset();
            }
        }
    }

    function calculate(a, b, op) {
        if (op === '+') return a + b;
        if (op === '-') return a - b;
        if (op === '×') return a * b;
        if (op === '÷') return a / b;
        return b;
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