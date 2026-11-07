"""Camera thread: latest frame + preview stream (Ali).

One daemon thread owns the capture device and keeps only the newest frame, so a
tap never waits on the phone camera and the preview can never lag behind the
display. The capture loop reads `latest()`; the browser reads `mjpeg_frames()`.
"""
from __future__ import annotations

import asyncio
import threading
import time

import cv2

PREVIEW_WIDTH = 720  # a monitor feed, not the evidence we send the reader
PREVIEW_FPS = 15
PREVIEW_QUALITY = 70
FRAME_GRACE = 2.0  # seconds of failed reads before latest() calls it dead
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
    """A capture device drained by one thread; readers always get the newest frame."""

    def __init__(self, capture, index=None):
        self.index = index
        self._capture = capture
        self._lock = threading.Lock()
        self._closed = False
        self._frame = None
        self._seq = 0
        self._error = None
        self._reconnect_used = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"camera-{index}", daemon=True)

    def start(self):
        self._thread.start()
        return self

    @property
    def is_open(self):
        return not self._closed

    def _run(self):
        failing_since = None
        while not self._stop.is_set():
            try:
                ok, frame = self._capture.read()
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

            if reason is not None:
                failing_since = failing_since if failing_since is not None else time.monotonic()
                if time.monotonic() - failing_since >= FRAME_GRACE:
                    if self._stop.is_set():
                        break
                    if not self._reconnect_used:
                        # One retry per failure episode: unplug/replug, or a phone that
                        # went to sleep, should not leave a stale frame on the preview.
                        self._reconnect_used = True
                        if self._reconnect():
                            failing_since = None
                            continue
                    else:
                        self._fail(reason)
                self._stop.wait(0.05)
                continue

            failing_since = None
            with self._lock:
                self._frame = frame
                self._seq += 1
                self._error = None
                self._reconnect_used = False

    def _fail(self, reason):
        """Make latest() raise instead of serving the frame that is no longer live."""
        with self._lock:
            self._error = reason
            self._frame = None

    def _reconnect(self):
        """Open the capture device once more; return False if the retry failed."""
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
            self._capture = new
        if new is not old:
            old.release()
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
        self._capture.release()


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
