"""Routes, capture loop, SSE (Shri).

Run: uv run uvicorn server.app:app --host 127.0.0.1 --port 8000

Frame sources (CLEANROOM_SOURCE):
- camera (default): Ali's server.camera, opened at startup on CLEANROOM_CAMERA (default 1).
- screen: a screenshot of the iPhone Mirroring window (whole screen if it isn't open).
  macOS asks once for Screen Recording permission for the terminal.
Set CLEANROOM_FRAME=<path to a jpg> to test with a still image instead.
"""
import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import Quartz
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import camera, reader
from server.trace import KEYS, Trace

ROOT = Path(__file__).resolve().parent.parent
SETTLE_SECONDS = 0.6  # the display finishes changing after a tap
STILL = os.environ.get("CLEANROOM_FRAME")
SOURCE = os.environ.get("CLEANROOM_SOURCE", "camera")
if SOURCE not in ("camera", "screen"):
    raise SystemExit(f"CLEANROOM_SOURCE must be camera or screen, not {SOURCE!r}")
MIRROR_APP = "iPhone Mirroring"
log = logging.getLogger("cleanroom")


@asynccontextmanager
async def lifespan(app):
    if SOURCE == "camera" and not STILL:
        index = int(os.environ.get("CLEANROOM_CAMERA", "1"))
        try:
            camera.open(index)
        except Exception as e:  # keep serving; captures will log suspect lines
            log.error("camera %s failed to open: %s", index, e)
    yield
    camera.close()


app = FastAPI(title="Clean Room", lifespan=lifespan)
app.mount("/web", StaticFiles(directory=ROOT / "web"), name="web")

state = {"busy": False, "trace": None}
subscribers = set()


def new_trace():
    session = time.strftime("%Y%m%d-%H%M%S")
    state["trace"] = Trace(ROOT / "traces" / f"{session}.jsonl", source=SOURCE)
    return state["trace"]


new_trace()


def mirror_window_id():
    """CGWindowID of the iPhone Mirroring window, or None if it isn't on screen."""
    windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    for w in windows:
        if w.get("kCGWindowOwnerName") == MIRROR_APP and w.get("kCGWindowLayer") == 0:
            return int(w["kCGWindowNumber"])
    return None


def grab_screen():
    """Screenshot the mirroring window (no shadow, no sound). Whole screen as a fallback."""
    window = mirror_window_id()
    if window is None:
        log.warning("%s window not found; capturing the whole screen", MIRROR_APP)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "frame.png")
        args = ["/usr/sbin/screencapture", "-x", "-o"] + ([f"-l{window}"] if window else []) + [path]
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        if result.returncode or not os.path.exists(path):
            log.error("screencapture failed: %s", result.stderr.strip())
            return None
        return cv2.imread(path)


def grab_frame():
    if STILL:
        return cv2.imread(STILL)
    if SOURCE == "screen":
        return grab_screen()
    try:
        return camera.latest()
    except camera.CameraError as e:
        log.error("no frame: %s", e)
        return None


def emit(event, data):
    message = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    for queue in list(subscribers):
        queue.put_nowait(message)


def set_busy(busy):
    state["busy"] = busy
    emit("state", {"busy": busy, "lines": len(state["trace"].lines)})


async def capture(apply_reading):
    """Wait for the display to settle, read one frame, record it, tell the screens."""
    if state["busy"]:
        raise HTTPException(409, "busy: wait for green")
    set_busy(True)
    try:
        await asyncio.sleep(SETTLE_SECONDS)
        frame = await asyncio.to_thread(grab_frame)
        reading, model = await asyncio.to_thread(reader.read, frame)
        line = apply_reading(reading)
        emit("capture", {"thumb": reader.thumb(frame), "reading": reading, "model": model, "line": line})
        return {"line": line, "model": model}
    finally:
        set_busy(False)


class Tap(BaseModel):
    key: str


@app.post("/tap")
async def tap(body: Tap):
    if body.key not in KEYS or body.key == "none":
        raise HTTPException(400, f"unknown key: {body.key!r}")
    return await capture(lambda reading: state["trace"].append(body.key, reading))


@app.post("/snap")
async def snap():
    trace = state["trace"]
    if trace.lines:
        return await capture(trace.reread_last)
    return await capture(lambda reading: trace.append("none", reading))


@app.post("/undo")
async def undo():
    line = state["trace"].undo_last()
    if line is None:
        raise HTTPException(400, "nothing to undo")
    emit("undo", {"line": line})
    return {"line": line}


@app.post("/session/new")
async def session_new():
    trace = new_trace()
    emit("session", {"path": trace.path.name})
    return {"path": trace.path.name}


@app.get("/trace")
async def get_trace():
    trace = state["trace"]
    return {"path": trace.path.name, "busy": state["busy"], "lines": trace.lines}


@app.get("/events")
async def events():
    queue = asyncio.Queue()
    subscribers.add(queue)

    async def stream():
        try:
            yield f"event: state\ndata: {json.dumps({'busy': state['busy'], 'lines': len(state['trace'].lines)})}\n\n"
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            subscribers.discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/preview.mjpg")
async def preview():
    media_type = "multipart/x-mixed-replace; boundary=frame"
    if SOURCE == "camera" and not STILL:
        return StreamingResponse(camera.mjpeg_frames(), media_type=media_type)
    pause = 0.5 if SOURCE == "screen" else 0.1  # a screenshot costs ~0.2 s, so go slower

    async def stream():
        while True:
            frame = await asyncio.to_thread(grab_frame)
            if frame is not None:
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            await asyncio.sleep(pause)

    return StreamingResponse(stream(), media_type=media_type)


@app.get("/")
async def index():
    return FileResponse(ROOT / "web" / "operator.html")


@app.get("/screen")
async def screen():
    return FileResponse(ROOT / "web" / "screen.html")
