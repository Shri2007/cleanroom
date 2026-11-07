"""Append/read contract v2 trace lines (Shri)."""
import json
import time
from pathlib import Path

DIGITS = set("0123456789")
KEYS = DIGITS | {".", "+", "-", "×", "÷", "=", "%", "+/-", "AC", "C", "⌫", "none"}
MAX_DIGITS = 9  # the phone display stops accepting digits here
READING_FIELDS = ("display", "expression", "clear_label", "active_op")


def is_suspect(key, display):
    """Sanity flag, no AI: digits must show up at the end, AC must show 0."""
    if display is None:
        return True
    shown = display.replace(",", "").replace(" ", "")
    if key in DIGITS:
        digit_count = sum(ch in DIGITS for ch in shown)
        return not shown.endswith(key) and digit_count < MAX_DIGITS
    if key == "AC":
        return shown != "0"
    return False


class Trace:
    """One session's lines, kept in memory and rewritten to traces/<session>.jsonl."""

    def __init__(self, path, source="camera"):
        self.path = Path(path)
        self.source = source
        self.lines = []
        self.started = time.monotonic()
        if self.path.exists():
            self.lines = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]

    def _next_test(self, key):
        if not self.lines:
            return 1
        last = self.lines[-1]["test"]
        return last + 1 if key == "AC" else last

    def append(self, key, reading):
        if key not in KEYS:
            raise ValueError(f"unknown key: {key!r}")
        line = {
            "seq": self.lines[-1]["seq"] + 1 if self.lines else 1,
            "test": self._next_test(key),
            "t": round(time.monotonic() - self.started, 1),
            "source": self.source,
            "key": key,
            **{f: reading.get(f) for f in READING_FIELDS},
            "suspect": is_suspect(key, reading.get("display")),
            "deleted": False,
        }
        self.lines.append(line)
        self._save()
        return line

    def reread_last(self, reading):
        """Replace the last line's reading (fixes a misread). Keeps seq/test/key."""
        line = self.lines[-1]
        line.update({f: reading.get(f) for f in READING_FIELDS})
        line["suspect"] = is_suspect(line["key"], line["display"])
        self._save()
        return line

    def undo_last(self):
        """Mark the newest non-deleted line as deleted. Returns it, or None."""
        for line in reversed(self.lines):
            if not line["deleted"]:
                line["deleted"] = True
                self._save()
                return line
        return None

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in self.lines))
