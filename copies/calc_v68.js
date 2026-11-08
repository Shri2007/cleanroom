(function() {
  let displayValue = '0';
  let expressionValue = null;
  let clearLabel = 'AC';
  let activeOp = null;

  let state = 'START'; // START, ENTERING, OP_PENDING
  let firstOperand = null;
  let pendingOp = null;
  let justEvaluated = false;

  function formatDisplay(val) {
    if (val === 'Error') return 'Error';
    let parts = val.split('.');
    let intPart = parts[0];
    let neg = intPart.startsWith('-');
    if (neg) intPart = intPart.slice(1);
    
    let formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    if (neg) formattedInt = '-' + formattedInt;
    
    if (parts.length > 1) {
      return formattedInt + '.' + parts[1];
    }
    return formattedInt;
  }

  globalThis.Calc = {
    reset() {
      displayValue = '0';
      expressionValue = null;
      clearLabel = 'AC';
      activeOp = null;
      state = 'START';
      firstOperand = null;
      pendingOp = null;
      justEvaluated = false;
    },

    press(key) {
      if (key === 'AC' || key === 'C') {
        if (key === 'C' && clearLabel === 'C') {
          displayValue = '0';
          clearLabel = 'AC';
        } else {
          this.reset();
        }
        return;
      }

      if ((key >= '0' && key <= '9') || key === '.') {
        clearLabel = 'C';
        if (state === 'OP_PENDING') {
          displayValue = (key === '.') ? '0.' : key;
          state = 'ENTERING';
          activeOp = null;
        } else if (state === 'START' || justEvaluated) {
          if (key === '.') {
            displayValue = '0.';
          } else {
            displayValue = key;
          }
          justEvaluated = false;
          state = 'ENTERING';
        } else {
          if (key === '.' && displayValue.includes('.')) return;
          if (displayValue === '0' && key !== '.') {
            displayValue = key;
          } else {
            displayValue += key;
          }
        }
        return;
      }

      if (['+', '-', '×', '÷'].includes(key)) {
        firstOperand = displayValue;
        pendingOp = key;
        state = 'OP_PENDING';
        activeOp = null;
        displayValue = firstOperand + key;
        expressionValue = null;
        return;
      }
    },

    render() {
      return {
        display: displayValue,
        expression: expressionValue,
        clear_label: clearLabel,
        active_op: activeOp
      };
    }
  };
})();