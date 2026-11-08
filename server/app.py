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
import re
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import Quartz
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import brain, camera, reader, watch
from server.trace import KEYS, Trace

ROOT = Path(__file__).resolve().parent.parent
SETTLE_SECONDS = 0.6  # camera feeds need time to catch up after a tap
STILL = os.environ.get("CLEANROOM_FRAME")
SOURCE = os.environ.get("CLEANROOM_SOURCE", "camera")
if SOURCE not in ("camera", "screen"):
    raise SystemExit(f"CLEANROOM_SOURCE must be camera or screen, not {SOURCE!r}")
MIRROR_APP = "iPhone Mirroring"
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [cleanroom] %(message)s")
log = logging.getLogger("cleanroom")


@asynccontextmanager
async def lifespan(app):
    state["loop"] = asyncio.get_running_loop()  # lets the brain thread send live events
    use_camera = SOURCE == "camera" and not STILL
    if use_camera:
        index = int(os.environ.get("CLEANROOM_CAMERA", "1"))
        try:
            camera.open(index)
        except Exception as e:  # keep serving; captures will log suspect lines
            log.error("camera %s failed to open: %s", index, e)
    elif SOURCE == "screen" and not STILL:
        if not Quartz.CGPreflightScreenCaptureAccess():
            log.error("NO SCREEN RECORDING PERMISSION. System Settings > Privacy & Security > "
                      "Screen & System Audio Recording > turn on your terminal app, then restart it.")
        window = mirror_window_id()
        log.info("screen source: %s", f"{MIRROR_APP} window {window}" if window else
                 f"{MIRROR_APP} not open, will capture the whole screen")
    yield
    if use_camera:
        camera.close()


app = FastAPI(title="Clean Room", lifespan=lifespan)
app.mount("/web", StaticFiles(directory=ROOT / "web"), name="web")
app.mount("/docs", StaticFiles(directory=ROOT / "docs"), name="docs")  # the phone copy, same files as GitHub Pages

state = {"busy": False, "trace": None, "brain_running": False, "loop": None, "watching": False}
subscribers = set()


def new_trace(first=False):
    session = time.strftime("%Y%m%d-%H%M%S")
    saved = os.environ.get("CLEANROOM_TRACE")  # start from a saved session (a clean recording for the demo)
    path = ROOT / saved if first and saved else ROOT / "traces" / f"{session}.jsonl"
    state["trace"] = Trace(path, source=SOURCE)
    return state["trace"]


new_trace(first=True)


def mirror_window_id():
    """CGWindowID of the iPhone Mirroring window, or None if it isn't on screen."""
    windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    for w in windows:
        if w.get("kCGWindowOwnerName") == MIRROR_APP and w.get("kCGWindowLayer") == 0:
            return int(w["kCGWindowNumber"])
    return None


_window = {"id": None, "at": 0.0}


def cached_mirror_window():
    """The mirror window id, looked up at most once a second (listing windows is slow)."""
    now = time.monotonic()
    if _window["id"] is None or now - _window["at"] > 1.0:
        _window["id"], _window["at"] = mirror_window_id(), now
    return _window["id"]


def grab_window_fast(window):
    """The window's pixels straight from the window server, no subprocess and no temp file: ~15-30 ms
    instead of ~150 ms for screencapture. Returns a BGR array, or None if the window can't be captured."""
    import numpy as np
    image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow, window,
        Quartz.kCGWindowImageBoundsIgnoreFraming)
    if image is None:
        return None
    w, h = Quartz.CGImageGetWidth(image), Quartz.CGImageGetHeight(image)
    if w < 50 or h < 50:
        return None
    row = Quartz.CGImageGetBytesPerRow(image)
    data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(image))
    pixels = np.frombuffer(data, dtype=np.uint8).reshape(h, row // 4, 4)[:, :w, :]
    return np.ascontiguousarray(pixels[:, :, :3])  # BGRA -> BGR


def grab_screen():
    """The mirroring window (whole screen if it isn't open). Fast in-process grab first, screencapture
    as the fallback."""
    window = cached_mirror_window()
    if window is not None:
        frame = grab_window_fast(window)
        if frame is not None:
            return frame
        _window["id"] = None  # window id may be stale; look it up again next time
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


def _fan_out(message):
    for queue in list(subscribers):
        queue.put_nowait(message)


def emit(event, data):
    """Send an SSE event to every page. Safe to call from the brain's worker thread."""
    message = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    loop = state["loop"]
    if loop is not None:
        loop.call_soon_threadsafe(_fan_out, message)
    else:
        _fan_out(message)


def set_busy(busy):
    state["busy"] = busy
    emit("state", {"busy": busy, "lines": len(state["trace"].lines)})


async def capture(apply_reading):
    """Wait for the display to settle, read one frame, record it, tell the screens."""
    if state["busy"]:
        raise HTTPException(409, "busy: wait for green")
    set_busy(True)
    try:
        await asyncio.sleep(0.25 if SOURCE == "screen" else SETTLE_SECONDS)
        frame = await asyncio.to_thread(grab_frame)
        thumb = reader.thumb(frame)
        if thumb:
            emit("snapshot", {"thumb": thumb})
        reading, model = await asyncio.to_thread(reader.read, frame)
        line = apply_reading(reading)
        emit("capture", {"thumb": thumb, "reading": reading, "model": model, "line": line,
                         "snapshot_shown": bool(thumb)})
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


WATCH_PERIOD = 0.04  # short pause between screenshots; capture itself also takes time


async def watch_loop():
    """Screenshot often; when the display changes and settles, read it and infer the key."""
    frame = await asyncio.to_thread(grab_frame)
    if frame is None:
        emit("watch", {"on": False, "error": "no frame to watch"})
        state["watching"] = False
        return
    # The screenshot loop never waits for the reader: every settled screen goes into a queue,
    # and the reader works through it in order, so fast typing is caught up afterwards, not lost.
    queue = asyncio.Queue()
    queue.put_nowait(frame)  # the starting screen, used only as the baseline for the first key
    reader_task = asyncio.create_task(watch_reader(queue))
    seen, pending, still = watch.signature(frame), None, 0
    emit("watch", {"on": True})
    while state["watching"]:
        await asyncio.sleep(WATCH_PERIOD)
        frame = await asyncio.to_thread(grab_frame)
        if frame is None:
            continue
        sig = watch.signature(frame)
        if not watch.changed(sig, seen):
            pending, still = None, 0
            continue
        if pending is None or watch.changed(sig, pending):
            pending, still = sig, 1  # still changing (or glowing): wait for it to hold still
            continue
        still += 1
        if still < watch.SETTLE_FRAMES:
            continue
        seen, pending, still = sig, None, 0
        emit("snapshot", {"thumb": reader.thumb(frame)})
        queue.put_nowait(frame)
    queue.put_nowait(None)
    await reader_task
    emit("watch", {"on": False})


async def watch_reader(queue):
    """Read queued screens in order; log a line only when the reading really changed."""
    prev, done = None, False
    while not done:
        frames = [await queue.get()]
        while not queue.empty():
            frames.append(queue.get_nowait())  # everything that piled up while we were reading
        if frames[-1] is None:
            frames.pop()
            done = True
        if not frames:
            continue
        set_busy(True)
        try:
            # read them all at once, then log in screen order so key inference sees the right sequence
            readings = await asyncio.gather(*(asyncio.to_thread(reader.read, f) for f in frames))
            for frame, (reading, model) in zip(frames, readings):
                if reading.get("display") is None:
                    continue
                if prev is None or watch.same_reading(prev, reading):
                    prev = prev or reading  # baseline, or a re-detection of the same screen: not a key
                    continue
                key = watch.infer_key(prev, reading) or await asyncio.to_thread(watch.ask_key, prev, reading)
                if key:
                    line = state["trace"].append(key, reading)
                    emit("capture", {"thumb": reader.thumb(frame), "reading": reading, "model": model,
                                     "line": line, "inferred": True, "snapshot_shown": True})
                else:
                    emit("watch", {"on": True, "skipped": reading.get("display")})
                prev = reading
        except Exception as e:  # keep watching; show the problem
            log.exception("watch step failed")
            emit("watch", {"on": True, "error": f"{type(e).__name__}: {e}"[:200]})
        finally:
            set_busy(not queue.empty())


@app.post("/watch/start")
async def watch_start():
    if state["watching"]:
        return {"watching": True}
    state["watching"] = True
    asyncio.create_task(watch_loop())
    return {"watching": True}


@app.post("/watch/stop")
async def watch_stop():
    state["watching"] = False
    return {"watching": False}


@app.post("/watch/toggle")
async def watch_toggle():
    """The server knows whether it is watching; pages may have a stale idea after a restart."""
    return await (watch_stop() if state["watching"] else watch_start())


class BrainRun(BaseModel):
    trace: str | None = None  # a file name in traces/; default: the live session


@app.post("/brain/run")
async def brain_run(body: BrainRun | None = None):
    """Run spec → copy → score → fix in the background. Progress arrives as SSE `brain` events."""
    if state["brain_running"]:
        raise HTTPException(409, "brain is already running")
    name = body.trace if body and body.trace else state["trace"].path.name
    if not re.fullmatch(r"[\w.-]+\.jsonl", name) or not (ROOT / "traces" / name).is_file():
        raise HTTPException(400, f"no such trace: {name!r}")
    state["brain_running"] = True

    async def work():
        try:
            await asyncio.to_thread(brain.run_loop, ROOT / "traces" / name, lambda e: emit("brain", e))
        except Exception as e:  # report it on screen instead of failing silently
            log.exception("brain run failed")
            emit("brain", {"step": "failed", "error": f"{type(e).__name__}: {e}"[:300]})
        finally:
            state["brain_running"] = False

    asyncio.create_task(work())
    return {"started": True, "trace": name}


def latest_trace_with_lines():
    """The live session if it has lines, else the newest saved trace that does."""
    if state["trace"].lines:
        return state["trace"].path
    for path in sorted((ROOT / "traces").glob("2*.jsonl"), reverse=True):
        if path.stat().st_size:
            return path
    raise HTTPException(400, "no trace with lines yet")


@app.post("/brain/modernize")
async def brain_modernize():
    """Rewrite the best copy as clean code and prove it still behaves the same. SSE `modernize` events."""
    if state["brain_running"]:
        raise HTTPException(409, "brain is busy")
    trace_path = latest_trace_with_lines()
    state["brain_running"] = True

    async def work():
        try:
            await asyncio.to_thread(brain.modernize, trace_path, lambda e: emit("modernize", e))
        except Exception as e:
            log.exception("modernize failed")
            emit("modernize", {"step": "failed", "error": f"{type(e).__name__}: {e}"[:300]})
        finally:
            state["brain_running"] = False

    asyncio.create_task(work())
    return {"started": True, "trace": trace_path.name}


@app.post("/brain/pick_test")
async def brain_pick_test():
    """Ask the brain for one key sequence that would confirm a guessed rule. Shown on screen as `pick_test`."""
    versions = brain.load_history().get("calc", [])
    if not versions:
        raise HTTPException(400, "run the brain first: there are no rules yet")
    rules = versions[-1]["rules"]
    try:
        picked = await asyncio.to_thread(brain.pick_test, rules)
    except Exception as e:
        raise HTTPException(502, f"brain could not pick a test: {type(e).__name__}: {e}"[:300])
    rule = next((r for r in rules if r["id"] == str(picked.get("rule_id"))), None)
    result = {"rule_id": picked.get("rule_id"), "instruction": str(picked.get("instruction", ""))[:120],
              "rule": rule["rule"] if rule else None}
    emit("pick_test", result)
    return result


@app.get("/scores")
async def scores():
    return brain.load_history()


@app.get("/copies/{name}")
async def get_copy(name: str):
    if not re.fullmatch(r"calc_v\d+\.js", name) or not (ROOT / "copies" / name).is_file():
        raise HTTPException(404, "no such copy")
    return FileResponse(ROOT / "copies" / name, media_type="text/plain")


@app.get("/trace")
async def get_trace():
    trace = state["trace"]
    return {"path": trace.path.name, "busy": state["busy"], "watching": state["watching"], "lines": trace.lines}


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
    pause = 0.1  # the in-process grab costs ~30 ms, so the preview can run at ~10 fps

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


@app.get("/twin")
async def twin():
    """"Which one is real?": the phone copy, running the best copy so far. Sits beside the mirror window."""
    return RedirectResponse("/docs/play.html")
