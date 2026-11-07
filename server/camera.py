"""Camera thread: latest frame + preview stream (Ali).

One daemon thread owns the capture device and keeps only the newest frame, so a
tap never waits on the phone camera and the preview can never lag behind the
display. The capture loop reads `latest()`; the browser reads `mjpeg_frames()`.

A capture `read()` can block forever (phone asleep, USB unplugged mid-read). The
reader thread is therefore disposable and a watchdog owns failure/reconnect: if
no fresh frame arrives within FRAME_GRACE, the old reader is abandoned, one
reconnect is attempted, and a failed retry clears the frame so `latest()` raises
instead of serving the last good one.
"""
from __future__ import annotations

import asyncio
import threading
import time

import cv2

PREVIEW_WIDTH = 720  # a monitor feed, not the evidence we send the reader
PREVIEW_FPS = 15
PREVIEW_QUALITY = 70
FRAME_GRACE = 2.0  # seconds without a fresh frame before latest() calls it dead
BLACK_LEVEL = 8  # a frame this dark is a covered/closed camera, not evidence


def _is_black(frame):
    """True for a missing or all-but-black frame (the lens is covered, or the feed died)."""
    if frame is None or getattr(frame, "size", 0) == 0:
        return True
    try:
        return int(frame.max()) <= BLACK_LEVEL
    except (AttributeError, ValueError):
        return False


class CameraError(RuntimeError):
    """The camera is closed, or has not produced a frame."""


class Camera:
    """A capture device drained by one disposable reader; readers always get the newest frame."""

    def __init__(self, capture, index=None):
        self.index = index
        self._capture = capture
        self._lock = threading.Lock()
        self._closed = False
        self._frame = None
        self._seq = 0
        self._error = None
        self._reason = None
        self._reconnect_used = False
        self._stop = threading.Event()
        self._generation = 0
        self._last_frame_at = time.monotonic()
        self._thread = threading.Thread(target=self._watch, name=f"camera-{index}", daemon=True)

    def start(self):
        with self._lock:
            self._last_frame_at = time.monotonic()
            capture = self._capture
            generation = self._generation
        self._start_reader(capture, generation)
        self._thread.start()
        return self

    @property
    def is_open(self):
        return not self._closed

    def _start_reader(self, capture, generation):
        thread = threading.Thread(
            target=self._read_loop,
            args=(capture, generation),
            name=f"camera-{self.index}-read-{generation}",
            daemon=True,
        )
        thread.start()

    def _read_loop(self, capture, generation):
        """Drain one capture generation. A newer generation makes this thread stop."""
        while not self._stop.is_set():
            with self._lock:
                if generation != self._generation or self._error is not None:
                    return
            try:
                ok, frame = capture.read()
            except Exception as e:  # unplugged phone, device reset, ...
                ok, frame = False, None
                reason = f"{type(e).__name__}: {e}"
            else:
                if not ok or frame is None:
                    reason = "camera stopped returning frames"
                elif _is_black(frame):
                    reason = "camera returned black frames"
                else:
                    reason = None

            with self._lock:
                if generation != self._generation or self._error is not None:
                    return
                if reason is not None:
                    self._reason = reason
                else:
                    self._frame = frame
                    self._seq += 1
                    self._last_frame_at = time.monotonic()
                    self._reason = None
                    self._reconnect_used = False

            if reason is not None:
                self._stop.wait(0.05)

    def _watch(self):
        """Fail closed when frames stop, even if the reader is stuck inside read()."""
        while not self._stop.wait(0.02):
            with self._lock:
                if self._error is not None:
                    return
                if time.monotonic() - self._last_frame_at < FRAME_GRACE:
                    continue
                reason = self._reason or (
                    "camera stopped returning frames" if self._frame is not None
                    else "camera produced no frames"
                )
                retry = not self._reconnect_used
                if retry:
                    self._reconnect_used = True
            if retry:
                if self._reconnect():
                    continue
                return
            self._fail(reason)
            return

    def _fail(self, reason):
        """Make latest() raise instead of serving the frame that is no longer live."""
        with self._lock:
            self._error = reason
            self._frame = None
            self._reason = reason
            self._generation += 1  # any read still in flight is now stale

    def _reconnect(self):
        """Open the capture device once more, then read it from a fresh thread."""
        old = self._capture
        try:
            new = _open_capture(self.index)
        except Exception as e:
            self._fail(f"camera reconnect failed: {type(e).__name__}: {e}")
            return False
        if new is None or not new.isOpened():
            if new is not None:
                new.release()
            self._fail("camera reconnect failed: camera did not open")
            return False
        with self._lock:
            if self._stop.is_set() or self._error is not None:
                new.release()
                return False
            self._capture = new
            self._generation += 1
            generation = self._generation
            self._frame = None  # fail closed while the retry warms up
            self._reason = None
            self._last_frame_at = time.monotonic()
        if new is not old:
            old.release()
        self._start_reader(new, generation)
        return True

    def snapshot(self):
        """Newest (frame, seq) without raising: previews tolerate an empty camera."""
        with self._lock:
            return self._frame, self._seq

    def latest(self):
        """Newest frame, or CameraError when the feed is gone (never a stale frame)."""
        frame, _ = self.snapshot()
        with self._lock:
            error = self._error
        if frame is None or error:
            raise CameraError(error or "no frame yet")
        return frame

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._stop.set()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)
        with self._lock:
            capture = self._capture
        capture.release()


def _open_capture(index):
    capture = cv2.VideoCapture(index)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # do not queue stale frames
    return capture


_camera: Camera | None = None
_camera_lock = threading.Lock()


def open(index=0):
    """Open `index` and start draining it. Closes any previous camera."""
    global _camera
    capture = _open_capture(index)
    if not capture.isOpened():
        capture.release()
        raise CameraError(f"camera {index} did not open")

    camera = Camera(capture, index).start()
    with _camera_lock:
        previous, _camera = _camera, camera
    if previous is not None:
        previous.close()
    return camera


def close():
    """Stop the thread and release the device; safe to call more than once."""
    global _camera
    with _camera_lock:
        camera, _camera = _camera, None
    if camera is not None:
        camera.close()


def latest():
    """Newest frame from the open camera."""
    camera = _camera
    if camera is None:
        raise CameraError("camera is not open")
    return camera.latest()


def _encode_jpeg(frame, quality, max_width):
    height, width = frame.shape[:2]
    if max_width and width > max_width:
        scale = max_width / width
        frame = cv2.resize(
            frame,
            (max_width, max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buffer.tobytes() if ok else None


async def mjpeg_frames(fps=PREVIEW_FPS, quality=PREVIEW_QUALITY, width=PREVIEW_WIDTH):
    """Yield multipart JPEG chunks for `/preview.mjpg`, one per new frame."""
    header = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
    period = 1.0 / max(fps, 1)
    camera = _camera
    last_seq = -1

    while camera is not None and camera.is_open:
        frame, seq = camera.snapshot()
        if frame is not None and seq != last_seq:
            last_seq = seq
            jpeg = await asyncio.to_thread(_encode_jpeg, frame, quality, width)
            if jpeg:
                yield header + jpeg + b"\r\n"
        await asyncio.sleep(period)


__all__ = ["Camera", "CameraError", "open", "close", "latest", "mjpeg_frames"]
