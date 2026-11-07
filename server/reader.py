"""Frame -> display JSON via vision model (Shri).

Gemini Flash-Lite first: ~2 s per read. Meta muse-spark-1.3 reads images too but
took ~24 s in our 11:05 test, so it is the backup here (Meta stays the brain).
A failed reading returns every field as None, so the trace line is suspect.
"""
import base64
import json
import os

import cv2
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODELS = [  # (name, base_url, key env var, model, extra request args)
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY",
     "gemini-flash-lite-latest", {"reasoning_effort": "low"}),
    ("meta", "https://api.meta.ai/v1", "MODEL_API_KEY", "muse-spark-1.3", {}),
]
OPS = {"+", "-", "×", "÷"}
EMPTY = {"display": None, "expression": None, "clear_label": None, "active_op": None}

PROMPT = """Find the calculator display in this photo and read exactly what it shows.
Return JSON only, with these keys:
- "display": the big result line, exactly as shown (keep commas, minus sign, "Error", "e").
- "expression": the smaller line above it if one is shown, else null.
- "clear_label": the text on the clear key ("AC" or "C") if visible, else null.
- "active_op": the operator key that is highlighted ("+", "-", "×", "÷"), else null.
Do not guess digits you cannot see. If there is no calculator, set "display" to null."""

_clients = {}


def _client(base_url, key_name):
    if key_name not in _clients:
        _clients[key_name] = OpenAI(base_url=base_url, api_key=os.environ[key_name], timeout=15)
    return _clients[key_name]


def _jpeg_b64(frame, quality=90):
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("could not encode frame")
    return base64.b64encode(buf).decode()


def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(text)
    out = {}
    for field in EMPTY:
        value = data.get(field)
        out[field] = None if value in (None, "", "null") else str(value).strip()
    if out["active_op"] not in OPS:
        out["active_op"] = {"*": "×", "x": "×", "/": "÷", "−": "-"}.get(out["active_op"])
    return out


def read(frame):
    """Read one BGR frame. Returns (reading, model name or error text)."""
    if frame is None:
        return dict(EMPTY), "no frame"
    image = _jpeg_b64(frame)
    messages = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}},
    ]}]
    errors = []
    for name, base_url, key_name, model, extra in MODELS:
        if not os.environ.get(key_name):
            continue
        try:
            reply = _client(base_url, key_name).chat.completions.create(model=model, messages=messages, **extra)
            return _parse(reply.choices[0].message.content), name
        except Exception as e:  # try the next model, but keep the reason
            errors.append(f"{name}: {type(e).__name__}: {e}"[:200])
    return dict(EMPTY), "; ".join(errors) or "no API keys set"


def thumb(frame, width=320):
    """Small JPEG (base64) for the flash + thumbnail on screen."""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    if w > width:
        frame = cv2.resize(frame, (width, int(h * width / w)))
    return _jpeg_b64(frame, quality=70)
