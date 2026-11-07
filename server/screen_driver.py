"""Drive macOS Calculator while :mod:`server.watch` observes it.

This module intentionally does not read displays, infer keys, or write trace
records.  It provides the physical side of a replay: launch Calculator, grab
its window as a BGR frame, and send the v2 trace keys.  Watch mode owns the
observation side and appends the resulting records to ``Trace``.

Run a saved trace through Calculator with::

    uv run python -m server.screen_driver traces/sample.jsonl
"""
import argparse
import subprocess
import tempfile
import time
from pathlib import Path

import cv2
import Quartz

from server.trace import KEYS, Trace

CALCULATOR_NAME = "Calculator"
WINDOW_OWNER = CALCULATOR_NAME.casefold()

# Virtual key codes on the standard macOS US keyboard.  Calculator accepts
# these ordinary keyboard equivalents; using them avoids clicking a
# resolution- or localization-dependent keypad.
SHIFT = Quartz.kCGEventFlagMaskShift
KEYSTROKES = {
    "0": (29, 0), "1": (18, 0), "2": (19, 0), "3": (20, 0), "4": (21, 0),
    "5": (23, 0), "6": (22, 0), "7": (26, 0), "8": (28, 0), "9": (25, 0),
    ".": (47, 0), "-": (27, 0), "+": (24, SHIFT), "×": (28, SHIFT),
    "÷": (44, 0), "=": (36, 0), "%": (23, SHIFT), "+/-": (45, 0),
    "AC": (53, 0), "C": (53, 0), "⌫": (51, 0),
}


class ScreenDriverError(RuntimeError):
    """The local Calculator target cannot be driven."""


def calculator_window_id():
    """Return the on-screen Calculator window id, or ``None`` when absent."""
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    for window in windows:
        owner = str(window.get("kCGWindowOwnerName", "")).casefold()
        if owner == WINDOW_OWNER and window.get("kCGWindowLayer") == 0:
            return int(window["kCGWindowNumber"])
    return None


def launch(timeout=5):
    """Launch and foreground Calculator, returning its window id.

    The caller must grant macOS Accessibility and Screen Recording permissions
    to the process running this module before pressing keys or capturing it.
    """
    subprocess.run(["open", "-a", CALCULATOR_NAME], check=True, timeout=timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        window = calculator_window_id()
        if window is not None:
            return window
        time.sleep(0.05)
    raise ScreenDriverError("Calculator did not open a visible window")


def screenshot(window=None):
    """Capture Calculator's window as an OpenCV BGR frame for ``watch``/``reader``."""
    window = calculator_window_id() if window is None else window
    if window is None:
        raise ScreenDriverError("Calculator is not visible")
    with tempfile.TemporaryDirectory() as directory:
        image = Path(directory) / "calculator.png"
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-o", f"-l{window}", str(image)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode or not image.exists():
            raise ScreenDriverError(f"Calculator screenshot failed: {result.stderr.strip()}")
        frame = cv2.imread(str(image))
    if frame is None:
        raise ScreenDriverError("Calculator screenshot could not be decoded")
    return frame


def press(key):
    """Send one normalized calculator key without recording a trace line."""
    if key == "none":
        return
    if key not in KEYS or key not in KEYSTROKES:
        raise ValueError(f"unsupported calculator key: {key!r}")
    keycode, flags = KEYSTROKES[key]
    for down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(None, keycode, down)
        Quartz.CGEventSetFlags(event, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def replay(trace_path, pause=0.2):
    """Replay non-deleted v2 trace keys in order for watch mode to observe.

    ``Trace`` supplies the canonical JSONL loading behavior.  This function
    returns the keys it sent so callers can assert a replay without needing a
    display reader; it deliberately never writes a trace file itself.
    """
    if pause < 0:
        raise ValueError("pause must be non-negative")
    lines = Trace(trace_path).lines
    sent = []
    for line in lines:
        if line.get("deleted"):
            continue
        key = line.get("key")
        if key not in KEYS:
            raise ValueError(f"invalid trace key: {key!r}")
        press(key)
        if key != "none":
            sent.append(key)
        if pause:
            time.sleep(pause)
    return sent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="v2 JSONL trace to replay")
    parser.add_argument("--pause", type=float, default=0.2, help="seconds between keys")
    args = parser.parse_args(argv)
    launch()
    print(" ".join(replay(args.trace, args.pause)))


if __name__ == "__main__":
    main()
