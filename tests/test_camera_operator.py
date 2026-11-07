"""Smoke test: camera thread + operator pages produce a trace the checker can score.

No camera and no API keys are needed: the camera is a fake capture device and
the vision reader is swapped for a deterministic calculator model. The app is
exercised through its ASGI interface, exactly like a browser would.

Run: uv run python -m unittest discover -s tests -v
"""
import asyncio
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import camera  # noqa: E402
from server.trace import Trace  # noqa: E402
from server.trace import is_suspect  # noqa: E402

SAMPLE = ROOT / "traces" / "sample.jsonl"
SCRIPT = ["AC", "2", "+", "3", "="]


# --- a tiny calculator: used to say what the camera should see, then again to
# --- replay the trace the way the checker will.
class Calculator:
    OPS = {"+", "-", "×", "÷"}
    DIGITS = set("0123456789")

    def __init__(self):
        self.display = "0"
        self.clear_label = "AC"
        self.active_op = None
        self._entry = False
        self._value = 0.0
        self._pending = None

    def _number(self):
        try:
            return float(self.display.replace(",", ""))
        except ValueError:
            return 0.0

    @staticmethod
    def _format(value):
        return str(int(value)) if float(value).is_integer() else f"{value:.9g}"

    def _apply(self, left, right, op):
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "×":
            return left * right
        return "Error" if right == 0 else left / right

    def press(self, key):
        if key == "AC":
            self.__init__()
        elif key == "C":
            self.display, self._entry, self.clear_label = "0", False, "C"
        elif key == "⌫":
            self.display = self.display[:-1] or "0"
            self._entry = self.display != "0"
            self.clear_label = "C"
        elif key == "+/-":
            self.display = self._format(-self._number())
            self._entry, self.clear_label, self.active_op = True, "C", None
        elif key == "%":
            self.display = self._format(self._number() / 100)
            self._entry, self.clear_label, self.active_op = True, "C", None
        elif key in self.DIGITS or key == ".":
            if not self._entry:
                self.display = "0" if key == "." else key
                self._entry = True
            elif key == ".":
                if "." not in self.display:
                    self.display += "."
            elif len(self.display.lstrip("-").replace(".", "")) < 9:
                self.display = key if self.display == "0" else self.display + key
            self.clear_label, self.active_op = "C", None
        elif key in self.OPS:
            self._value, self._pending = self._number(), key
            self.active_op, self._entry, self.clear_label = key, False, "C"
        elif key == "=":
            if self._pending:
                result = self._apply(self._value, self._number(), self._pending)
                self.display = result if result == "Error" else self._format(result)
                self._pending = None
            self.active_op, self._entry, self.clear_label = None, False, "C"
        else:
            raise ValueError(f"unknown key: {key!r}")
        return self

    def reading(self):
        return {
            "display": self.display,
            "expression": None,
            "clear_label": self.clear_label,
            "active_op": self.active_op,
        }


class FakeCapture:
    """Stand-in for cv2.VideoCapture: hands out numbered 64x48 frames."""

    def __init__(self, opened=True):
        self.opened = opened
        self.released = False
        self.reads = 0

    def isOpened(self):
        return self.opened

    def read(self):
        self.reads += 1
        time.sleep(0.002)  # behave roughly like a camera, do not spin hot
        return True, np.full((48, 64, 3), self.reads % 255, np.uint8)

    def release(self):
        self.released = True


class CameraTest(unittest.TestCase):
    def setUp(self):
        camera.close()
        self.fake = FakeCapture()
        self._original_open = camera._open_capture
        camera._open_capture = lambda index: self.fake

    def tearDown(self):
        camera.close()
        camera._open_capture = self._original_open

    def test_latest_frame_and_preview_chunks(self):
        camera.open(0)
        time.sleep(0.05)
        frame = camera.latest()
        self.assertEqual(frame.shape, (48, 64, 3))

        async def two_chunks():
            stream = camera.mjpeg_frames(fps=60)
            try:
                return [
                    await asyncio.wait_for(stream.__anext__(), timeout=2),
                    await asyncio.wait_for(stream.__anext__(), timeout=2),
                ]
            finally:
                await stream.aclose()

        first, second = asyncio.run(two_chunks())
        for chunk in (first, second):
            self.assertTrue(chunk.startswith(b"--frame\r\nContent-Type: image/jpeg"))
            self.assertIn(b"\xff\xd8\xff", chunk)  # JPEG magic
        self.assertNotEqual(first, second)  # newest frames only, never a repeat

        camera.close()
        self.assertTrue(self.fake.released)
        with self.assertRaises(camera.CameraError):
            camera.latest()

    def test_failed_open_leaves_no_camera(self):
        camera._open_capture = lambda index: FakeCapture(opened=False)
        with self.assertRaises(camera.CameraError):
            camera.open(0)
        with self.assertRaises(camera.CameraError):
            camera.latest()


class ASGIClient:
    """Minimal in-process HTTP client, so the test needs no extra packages."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, payload=None):
        return asyncio.run(self._request(method, path, payload))

    async def _request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        headers = [(b"host", b"testserver")]
        if payload is not None:
            headers.append((b"content-type", b"application/json"))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        messages = []

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        start = next(m for m in messages if m["type"] == "http.response.start")
        raw = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return start["status"], raw


class OperatorFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls.tmp.name)
        still = cls.tmpdir / "still.jpg"
        cv2.imwrite(str(still), np.full((48, 64, 3), 96, np.uint8))

        # server.app reads CLEANROOM_FRAME at import; a still image means no camera.
        os.environ["CLEANROOM_FRAME"] = str(still)
        from server import app as app_module

        cls.app_module = app_module
        cls.app_module.STILL = str(still)
        cls.app_module.SETTLE_SECONDS = 0
        cls.client = ASGIClient(app_module.app)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("CLEANROOM_FRAME", None)
        cls.tmp.cleanup()

    def setUp(self):
        self.calc = Calculator()
        self.trace_path = self.tmpdir / f"{self._testMethodName}.jsonl"
        self.app_module.state["busy"] = False
        self.app_module.state["trace"] = Trace(self.trace_path, source="camera")

        from server import reader

        self._original_read = reader.read
        self.readings = []

        def fake_read(frame):
            self.readings.append(frame is not None)
            return self.calc.reading(), "fake-vision"

        reader.read = fake_read

    def tearDown(self):
        from server import reader

        reader.read = self._original_read

    def tap(self, key):
        self.calc.press(key)
        status, raw = self.client.request("POST", "/tap", {"key": key})
        self.assertEqual(status, 200, raw)
        return json.loads(raw)

    def lines(self):
        text = self.trace_path.read_text()
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def score(self, lines):
        """Replay the trace the way checker/check.mjs will: key -> display."""
        replay = Calculator()
        matched = checked = 0
        for line in lines:
            if line["deleted"]:
                continue
            replay.press(line["key"])
            checked += 1
            matched += replay.display == line["display"]
        return matched, checked

    def test_pages_load(self):
        status, body = self.client.request("GET", "/")
        self.assertEqual(status, 200)
        page = body.decode()
        for marker in ('id="keypad"', 'id="snap"', 'id="undo"', 'id="flash"', 'id="thumbs"'):
            self.assertIn(marker, page)

        status, body = self.client.request("GET", "/screen")
        self.assertEqual(status, 200)
        page = body.decode()
        for marker in ('id="preview"', 'id="thumbs"', 'id="rules"', 'id="score"'):
            self.assertIn(marker, page)

    def test_operator_flow_writes_scoreable_trace(self):
        for key in SCRIPT:
            reply = self.tap(key)
            self.assertEqual(reply["line"]["key"], key)
            self.assertEqual(reply["line"]["source"], "camera")
            self.assertEqual(reply["model"], "fake-vision")

        lines = self.lines()
        self.assertEqual([line["key"] for line in lines], SCRIPT)
        self.assertEqual([line["seq"] for line in lines], [1, 2, 3, 4, 5])
        self.assertEqual({line["test"] for line in lines}, {1})
        self.assertFalse(any(line["deleted"] for line in lines))
        self.assertEqual(
            [line["suspect"] for line in lines], [is_suspect(l["key"], l["display"]) for l in lines]
        )
        self.assertFalse(any(line["suspect"] for line in lines), lines)
        self.assertEqual(lines[-1]["display"], "5")

        # Same shape as traces/sample.jsonl: same keys, same order, same types.
        sample = [json.loads(line) for line in SAMPLE.read_text().splitlines() if line.strip()]
        expected_keys = list(sample[0].keys())
        types = {
            "seq": int, "test": int, "t": (int, float), "source": str, "key": str,
            "display": (str, type(None)), "expression": (str, type(None)),
            "clear_label": (str, type(None)), "active_op": (str, type(None)),
            "suspect": bool, "deleted": bool,
        }
        for line in lines:
            self.assertEqual(list(line.keys()), expected_keys)
            for field, kind in types.items():
                self.assertIsInstance(line[field], kind, (field, line))

        # The checker can replay it: every recorded display matches its key.
        self.assertEqual(self.score(lines), (5, 5))

        # Snap re-reads the last line instead of appending one.
        status, raw = self.client.request("POST", "/snap")
        self.assertEqual(status, 200, raw)
        self.assertEqual(json.loads(raw)["line"]["seq"], 5)
        self.assertEqual(len(self.lines()), 5)

        # Undo marks lines deleted and the checker skips them.
        status, raw = self.client.request("POST", "/undo")
        self.assertEqual(status, 200, raw)
        self.assertTrue(json.loads(raw)["line"]["deleted"])
        self.assertTrue(self.lines()[-1]["deleted"])
        self.assertEqual(self.score(self.lines()), (4, 4))

        for _ in range(4):
            status, _ = self.client.request("POST", "/undo")
            self.assertEqual(status, 200)
        status, raw = self.client.request("POST", "/undo")
        self.assertEqual(status, 400, raw)

    def test_unknown_key_is_rejected(self):
        status, raw = self.client.request("POST", "/tap", {"key": "nope"})
        self.assertEqual(status, 400, raw)
        self.assertFalse(self.trace_path.exists())


if __name__ == "__main__":
    unittest.main()
