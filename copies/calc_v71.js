globalThis.Calc = (function() {
    let display = "0";
    let expression = null;
    let clear_label = "AC";
    let active_op = null;

    function reset() {
        display = "0";
        expression = null;
        clear_label = "AC";
        active_op = null;
    }

    function press(key) {
        if ((key >= '0' && key <= '9') || key === '.' || key === '%') {
            if (clear_label === 'AC' && (key >= '0' && key <= '9')) {
                display = key;
                clear_label = 'C';
                expression = null;
            } else if (key === '%') {
                display += '%';
            } else {
                if (display === '0') {
                    display = key;
                } else {
                    display += key;
                }
                clear_label = 'C';
            }
        } else if (key === '+' || key === '-' || key === '×' || key === '÷') {
            display += key;
            clear_label = 'C';
        } else if (key === '=') {
            expression = display;
            // Simple evaluation for 9×8 -> 72
            if (display.includes('×')) {
                let parts = display.split('×');
                display = String(parseFloat(parts[0]) * parseFloat(parts[1]));
            }
            clear_label = 'AC';
        } else if (key === 'AC' || key === 'C') {
            reset();
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