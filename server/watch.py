"""Watch mode (Shri): no key entry at all. The server screenshots the phone a few times a second,
notices when the display changes, reads it, and works out which key was pressed from the change.

Keys are inferred from what the screen shows, so a press that changes nothing on screen
(a second operator, a second ".") is not recorded. That is the honest limit of watching.
"""
import json
import re

import cv2
import numpy as np

from server import brain

CHANGE_THRESHOLD = 2.5   # mean pixel difference (0-255) in the display area that counts as a change
DISPLAY_TOP, DISPLAY_BOTTOM = 0.10, 0.45  # display band of the phone window, below the status bar clock

DIGITS = set("0123456789")
OPS = {"+", "-", "×", "÷"}


def signature(frame):
    """Small grayscale picture of the display band, for cheap change detection."""
    h = frame.shape[0]
    band = frame[int(h * DISPLAY_TOP):int(h * DISPLAY_BOTTOM)]
    return cv2.resize(cv2.cvtColor(band, cv2.COLOR_BGR2GRAY), (96, 48), interpolation=cv2.INTER_AREA).astype(np.int16)


def changed(a, b):
    return a is None or b is None or float(np.abs(a - b).mean()) > CHANGE_THRESHOLD


def _plain(text):
    return (text or "").replace(",", "").replace(" ", "")


def infer_key(prev, cur):
    """Which single key turns reading `prev` into reading `cur`? Rules first, None if unsure."""
    p, c = _plain(prev.get("display")), _plain(cur.get("display"))
    if cur.get("display") is None:
        return None
    if c == "0" and cur.get("clear_label") == "AC" and (p != "0" or prev.get("expression") or prev.get("active_op")):
        return "AC"
    if cur.get("active_op") and cur.get("active_op") != prev.get("active_op") and c == p:
        return cur["active_op"]
    if cur.get("expression") and cur.get("expression") != prev.get("expression"):
        return "="
    if prev.get("expression") and cur.get("expression") == prev.get("expression") and c != p:
        return "="  # repeated = keeps the expression line style but changes the result
    if c.startswith(p) and len(c) == len(p) + 1:
        last = c[-1]
        return last if last in DIGITS | {".", "%"} else None
    if c.startswith(p) and len(c) == len(p) + 2 and c[-2] in OPS | {"*", "/", "x"} and c[-1] in DIGITS:
        return c[-1]  # "50" -> "50+1": the operator shows up together with the first digit after it
    if p == "0" and len(c) == 1 and c in DIGITS:
        return c
    if prev.get("active_op") and not cur.get("active_op") and len(c) == 1 and c in DIGITS:
        return c  # first digit of the second number replaces the display
    if p.startswith(c) and len(p) == len(c) + 1:
        return "⌫"
    if c == "-" + p or p == "-" + c:
        return "+/-"
    return None


def ask_key(prev, cur):
    """Fallback: a quick text-only question to the brain. Returns a key or None."""
    system = ('A phone calculator display changed from A to B after exactly one key press. Keys: 0-9 . + - × ÷ = % '
              '+/- AC C ⌫. Return JSON only: {"key": "<one key>"}, or {"key": null} if impossible to tell.')
    user = json.dumps({"A": prev, "B": cur}, ensure_ascii=False)
    try:
        key = json.loads(brain.strip_fences(brain.ask(system, user))).get("key")
    except Exception:
        return None
    return key if isinstance(key, str) and re.fullmatch(r"[0-9.%=×÷+\-]|\+/-|AC|C|⌫", key) else None
