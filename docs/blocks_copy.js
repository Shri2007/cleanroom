globalThis.Blocks = {
  step(board, placed) {
    let grid = board.map(r => r.split(''));
    for (let [r, c] of placed) grid[r][c] = '#';
    let cellPoints = placed.length;
    let fullRows = [];
    let fullCols = [];
    for (let r = 0; r < 8; r++) if (grid[r].every(x => x === '#')) fullRows.push(r);
    for (let c = 0; c < 8; c++) {
      let f = true;
      for (let r = 0; r < 8; r++) if (grid[r][c] !== '#') { f = false; break; }
      if (f) fullCols.push(c);
    }
    for (let r of fullRows) for (let c = 0; c < 8; c++) grid[r][c] = '.';
    for (let c of fullCols) for (let r = 0; r < 8; r++) grid[r][c] = '.';
    let totalLines = fullRows.length + fullCols.length;
    let points = cellPoints;
    if (totalLines === 1) points = cellPoints + 15;
    else if (totalLines > 1) points = cellPoints + totalLines * 50 + totalLines * 80;
    let b = grid.map(r => r.join(''));
    return { board: b, points: points };
  }
};