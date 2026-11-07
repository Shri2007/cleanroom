"""Block Blast spike (Shri): read the 8x8 board from a screenshot of the iPhone Mirroring window.

Plain pixel sampling, no AI: the grid sits at a fixed place in the window, empty cells are dark
navy, filled cells are bright colored blocks. The score is read by the Meta reader separately.
"""
import re

import cv2
import numpy as np

N = 8
# Grid bounds as fractions of the mirror window (measured on a 652x1440 capture).
GRID = (52 / 652, 392 / 1440, 602 / 652, 944 / 1440)  # x0, y0, x1, y1
FILLED_VALUE = 120  # HSV value: empty cells are ~40-70, blocks are 150+


SCORE_BOX = (180 / 652, 230 / 1440, 472 / 652, 360 / 1440)  # the big score number


def read_score(frame):
    """The big score number, read by the Meta reader from a crop. None if unreadable."""
    import json
    from server import reader
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = int(SCORE_BOX[0] * w), int(SCORE_BOX[1] * h), int(SCORE_BOX[2] * w), int(SCORE_BOX[3] * h)
    img = reader._jpeg_b64(frame[y0:y1, x0:x1])
    msgs = [{"role": "user", "content": [
        {"type": "text", "text": 'Read the number in this image. JSON only: {"score": <integer or null>}'},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}]
    try:
        r = reader._client("https://api.meta.ai/v1", "MODEL_API_KEY").chat.completions.create(
            model="muse-spark-1.3", messages=msgs, reasoning_effort="minimal")
        value = json.loads(reader.strip_fences(r.choices[0].message.content) if hasattr(reader, "strip_fences")
                           else r.choices[0].message.content.strip().strip("`").removeprefix("json")).get("score")
        return int(value) if value is not None else None
    except Exception:
        return None


def watch(out_path, seconds=900, period=0.08):
    """Log every distinct board (so a placement and the clear after it are separate steps) and the
    score once the board has settled. Writes one JSON line per board change."""
    import json
    import time
    from server import app
    out = open(out_path, "a")
    last, last_logged, stable, seq = None, None, 0, 0
    end = time.time() + seconds
    print("watching Block Blast… play moves on the phone (Ctrl+C to stop)", flush=True)
    while time.time() < end:
        frame = app.grab_screen()
        if frame is None:
            time.sleep(period); continue
        board = read_board(frame)
        if board != last:
            last, stable = board, 1
            if board != last_logged:
                seq += 1
                line = {"seq": seq, "t": round(time.time(), 2), "board": board, "score": None}
                out.write(json.dumps(line) + "\n"); out.flush()
                last_logged = board
                print(f"#{seq}  " + " ".join(board), flush=True)
        else:
            stable += 1
            if stable == 4:  # settled: read the score for this board
                score = read_score(frame)
                out.write(json.dumps({"seq": seq, "settled": True, "score": score}) + "\n"); out.flush()
                print(f"    score {score}", flush=True)
        time.sleep(period)


def read_board(frame):
    """8 strings of '#' (filled) and '.' (empty), top row first."""
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = GRID[0] * w, GRID[1] * h, GRID[2] * w, GRID[3] * h
    cw, ch = (x1 - x0) / N, (y1 - y0) / N
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    rows = []
    for r in range(N):
        row = ""
        for c in range(N):
            cx, cy = int(x0 + (c + 0.5) * cw), int(y0 + (r + 0.5) * ch)
            patch = hsv[cy - int(ch * 0.2):cy + int(ch * 0.2), cx - int(cw * 0.2):cx + int(cw * 0.2)]
            row += "#" if float(np.median(patch[:, :, 2])) > FILLED_VALUE else "."
        rows.append(row)
    return rows



# ---------- learning: boards -> moves -> rules + a step() copy ----------

def _cells(board):
    return {(r, c) for r, row in enumerate(board) for c, ch in enumerate(row) if ch == "#"}


def moves(path):
    """Group logged boards into real moves: {before, placed, after, points}.
    Only boards that settled (held still) count as game states; boards in between are drag previews
    or the brief "line is full" frame before a clear. For each pair of settled states we take the last
    in-between board that contains the old state and everything in the new one: that is the placement
    with its full lines still showing. Its extra cells over the old state are the placed piece."""
    import json
    boards, settled = {}, []
    for line in open(path):
        rec = json.loads(line)
        if "board" in rec:
            boards[rec["seq"]] = rec["board"]
        elif rec.get("settled") and rec.get("score") is not None and rec["seq"] in boards:
            settled.append((rec["seq"], rec["score"]))
    out = []
    for (sa, score_a), (sb, score_b) in zip(settled, settled[1:]):
        A, B = _cells(boards[sa]), _cells(boards[sb])
        placement = None
        for seq in range(sa + 1, sb + 1):
            mid = _cells(boards.get(seq, []))
            if A < mid and B <= mid:
                placement = mid
        if placement is None:
            continue
        placed = placement - A
        cleared = placement - B
        full_lines = all(all((r, c) in placement for c in range(N)) or all((rr, cc) in placement for rr in range(N))
                         for r, c in cleared for cc in [c] for rr in [r])
        if not (0 < len(placed) <= 9) or not full_lines or score_b < score_a:
            continue  # not a clean single placement (new game, misread, odd frame)
        out.append({"move": len(out) + 1, "before": boards[sa], "placed": sorted(map(list, placed)),
                    "after": boards[sb], "points": score_b - score_a})
    return out


COPY = (
    "Write ONE plain JavaScript file that defines:\n"
    "globalThis.Blocks = { step(board, placed) { return {board: [...8 strings], points: <int>}; } };\n"
    "board is 8 strings of 8 chars, '#' filled and '.' empty, top row first. placed is a list of [row, col] "
    "cells where the player just put a piece. Return the board after the move (including any clears) and "
    "the points scored by this move. It must work for boards it has never seen: general rules only, NO lookup "
    "tables or special cases for the example boards. No import, require, process, fetch, timers, eval or Function. "
    "Return only the code.")

BOARD_LITERAL = re.compile(r"""["'][#.]{8}["']""")  # an 8-cell row pasted into the code


def memorizes(code):
    """A copy that pastes in observed board rows is memorizing examples, not following rules."""
    return len(BOARD_LITERAL.findall(code)) >= 3


def learn(path, on_event=print):
    """Rules (seen/guessed) and a copy from training moves; scored on held-out moves in the sandbox."""
    import json
    import random
    from server import brain
    ms = moves(path)
    if len(ms) < 4:
        raise ValueError(f"only {len(ms)} clean moves logged; play a few more")
    ids = list(range(len(ms)))
    random.Random(1).shuffle(ids)
    held = set(ids[:max(1, len(ms) * 3 // 10)])
    train = [m for i, m in enumerate(ms) if i not in held]
    test = [m for i, m in enumerate(ms) if i in held]
    on_event({"step": "split", "moves": len(ms), "train": len(train), "held": len(test)})
    evidence = "\n".join(json.dumps(m) for m in train)
    rules = json.loads(brain.strip_fences(brain.ask(
        "You reverse-engineer a block puzzle game from observed moves (board before, cells placed, board after, "
        "points). Use ONLY the evidence. 'seen' = shown directly by listed moves; general knowledge = 'guessed'. "
        'Return JSON only: {"rules": [{"id": "R1", "rule": "...", "status": "seen", "evidence": [move numbers]}]}. '
        "Cover placement, which lines clear (rows, columns), and exactly how points are computed. 5-10 rules.",
        evidence)))["rules"]
    on_event({"step": "rules", "rules": rules})
    code = brain.strip_fences(brain.ask("You build a copy of a block puzzle game's move logic. " + COPY,
                                        f"RULES:\n{json.dumps(rules)}\n\nMOVES:\n{evidence}"))
    best = None
    for version in range(1, 4):
        if memorizes(code):  # memorized answers score 0: it has to learn the rules
            tr = he = {"match_pct": 0, "mismatches": [{"error": "copy hard-codes observed boards (memorizing)"}]}
        else:
            tr, he = score(code, train), score(code, test)
        on_event({"step": "score", "version": version, "train_pct": tr["match_pct"], "held_pct": he["match_pct"],
                  "memorized": memorizes(code)})
        if best is None or tr["match_pct"] > best[1]["match_pct"]:
            best = (code, tr, he)
        if tr["match_pct"] == 100:
            break
        code = brain.strip_fences(brain.ask(
            "Fix this block puzzle copy so it matches the observed moves. Return the full new file. " + COPY,
            f"CODE:\n{best[0]}\n\nMISMATCHES:\n{json.dumps(best[1]['mismatches'][:8])}"))
    return {"rules": rules, "code": best[0], "train_pct": best[1]["match_pct"], "held_pct": best[2]["match_pct"]}


_SCORER = r"""
const vm = require('node:vm'); let buf = '';
process.stdin.on('data', d => buf += d).on('end', () => {
  const {code, moves} = JSON.parse(buf); let ok = 0; const mismatches = [];
  let ctx; try { ctx = vm.createContext({}, {codeGeneration: {strings: false, wasm: false}}); vm.runInContext(code, ctx, {timeout: 1000}); }
  catch (e) { process.stdout.write(JSON.stringify({match_pct: 0, mismatches: [{error: String(e.message)}]})); return; }
  for (const m of moves) {
    let got; try { ctx.m = m; got = JSON.parse(vm.runInContext('JSON.stringify(Blocks.step(m.before.slice(), m.placed))', ctx, {timeout: 500})); }
    catch (e) { got = {error: String(e.message)}; }
    const same = got && JSON.stringify(got.board) === JSON.stringify(m.after) && got.points === m.points;
    if (same) ok++; else mismatches.push({move: m.move, expected: {board: m.after, points: m.points}, got});
  }
  process.stdout.write(JSON.stringify({match_pct: moves.length ? Math.round(10000 * ok / moves.length) / 100 : 0, mismatches}));
});
"""


def score(code, ms):
    """A move matches if both the resulting board and the points are exact. Same sandbox as the calculator."""
    import json
    import os
    import subprocess
    try:
        r = subprocess.run(["node", "--permission", "-e", _SCORER], input=json.dumps({"code": code, "moves": ms}),
                           capture_output=True, text=True, timeout=3, env={"PATH": os.environ.get("PATH", "")})
        return json.loads(r.stdout)
    except Exception as e:
        return {"match_pct": 0, "mismatches": [{"error": str(e)}]}


if __name__ == "__main__":
    import sys
    watch(sys.argv[1] if len(sys.argv) > 1 else "traces/blocks.jsonl")
