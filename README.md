# Clean Room

An AI that rebuilds software just by watching it.

Built at AIE Code Summit, Nov 7 2026. Work in progress.

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

## Requirements

- **macOS** for the live server: camera capture uses AVFoundation and screen capture uses Quartz.
- **Python 3.12+** and [uv](https://docs.astral.sh/uv/).
- **Node.js 24+** for the checker and camera/operator tests. The checker runs untrusted copies with `node --permission`, which Node 24 provides. Check with `node --version`; put Node 24 first on `PATH` if needed.
- A camera for live capture. Vision API keys are optional for the deterministic tests and required for live readings.

## Setup

```bash
uv sync
```

For live vision, copy the example environment file and fill in at least one model key. Never commit `.env`.

```bash
cp .env.example .env
# edit .env: GEMINI_API_KEY or MODEL_API_KEY
```

macOS asks once for camera access. Allow **Camera** for the terminal app (or the IDE that launches the server), then restart that app. If you use the `screen` source, grant **Screen & System Audio Recording** instead.

## Run the server

```bash
CLEANROOM_CAMERA=0 uv run uvicorn server.app:app --host 127.0.0.1 --port 8000
```

- `CLEANROOM_CAMERA` selects the OpenCV camera index. The app defaults to `1`; `0` is usually the built-in MacBook camera.
- `CLEANROOM_SOURCE=screen` watches the iPhone Mirroring window instead of a camera (macOS screen-recording permission required).
- `CLEANROOM_FRAME=/path/to/frame.jpg` serves a still image instead of a live source, which is useful without a camera.
- Vision keys are read from `.env`. Without a key, captures are still recorded but their readings are `null` and marked suspect.

Open the operator console at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and the projector view at [http://127.0.0.1:8000/screen](http://127.0.0.1:8000/screen). Sessions are written to `traces/<timestamp>.jsonl`; the live trace is also available at `/trace`.

## Run the checker

The checker loads a copy (the generated calculator implementation) into a Node VM and compares its display state against a recorded trace. Use the Python wrapper so the copy also runs under Node's permission sandbox:

```bash
node --version   # must be v24+

uv run python -m server.checker tests/fixtures/calc_good.js traces/sample.jsonl
```

Expected result:

```text
match 100%  (5/5 lines)
```

To prove the checker is not a rubber stamp, score the deliberately wrong copy:

```bash
uv run python -m server.checker tests/fixtures/calc_bad.js traces/sample.jsonl
# match 80%  (4/5 lines)
```

The raw Node entry point is available for debugging:

```bash
node checker/check.mjs tests/fixtures/calc_good.js traces/sample.jsonl
```

### Checker tests

```bash
uv run python -m unittest tests.test_checker tests.test_checker_cal tests.test_checker_secrets -v
```

This runs 15 tests, including the sandbox escape/secret-leak checks.

## Camera and operator smoke test

The deterministic smoke test needs **no camera and no API keys**. It drives the real FastAPI app through its ASGI interface with a fake capture device and a deterministic reader, exercises taps, Snap, and Undo, then scores the resulting trace with the real checker:

```bash
uv run python -m unittest tests.test_camera_operator -v
```

This runs 5 tests. It is the reproducible camera/operator proof until the real iPhone camera and vision keys are available.

For a live hardware run:

1. Start the server with the camera index you want (see above).
2. Open the operator page, confirm the live preview, enter a known calculation, press **Snap**, and press **Undo**.
3. Score the session trace:

```bash
uv run python -m server.checker tests/fixtures/calc_good.js traces/<timestamp>.jsonl
```

The live reader is the vision model. Its readings will only match the reference copy when the camera sees the expected calculator state; use the deterministic test above when you need a repeatable 100% result.

## CI

The [`Checker and camera`](.github/workflows/checker.yml) workflow runs on pushes to `main` and `freebuff/**` and on pull requests to `main`:

- **Node 24 checker tests** on `ubuntu-latest`: `tests.test_checker`, `tests.test_checker_cal`, and `tests.test_checker_secrets` (15 tests).
- **Node 24 camera + operator test** on `macos-latest`: `uv sync --frozen` followed by `tests.test_camera_operator` (5 tests). macOS is required because the app imports Quartz and uses OpenCV.

Both jobs pin Node 24 before running the tests. The Ubuntu job invokes the checker tests without `uv sync` because the checker is stdlib-only and the full app dependencies include macOS-only PyObjC. The camera job does not use a physical camera or API keys.
