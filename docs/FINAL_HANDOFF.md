# SkyPsych - Final Handoff

Release documentation for the SkyPsych cognitive-fatigue telemetry MVP at
`F:\SKY PSYCH\skypsych-ai`. This document is the final handoff from the release
and documentation agent.

- Handoff date: **2026-08-05**
- Canonical interpreter: `.\.venv\Scripts\python.exe` (Python 3.11.1, pip
  26.2.1)

---

## 0. Pitch-Ready Update (2026-08-05)

This release makes the MVP **pitch-ready for a non-technical presenter** with no
typing required:

- **Simulation mode added.** `main.py --simulate [--simulate-duration 45.0]
  [--demo-loop] [--sim-fps 20.0] [--headless] [--max-frames N]
  [--output telemetry_sim.csv]`. Timeline: 0-10s GREEN, 10-20s YELLOW, 20-26s
  RED, 26-30s microsleep forces RED, 30-36s NO_FACE (never GREEN), 36-45s
  recovery. See [docs/SIMULATION_MODE.md](SIMULATION_MODE.md).
- **One-click launchers.** `00_SETUP.bat` (once), `01_VALIDATE.bat` (prints
  **VALIDATION COMPLETE**), `02_SIM_DEMO.bat` (guaranteed demo, no camera),
  `03_LIVE_CAMERA_DEMO.bat` (optional webcam), `04_PITCH_PACKAGE.bat` (opens
  talking points), `05_HELP.bat`. All use `cd /d "%~dp0"` and
  `.\.venv\Scripts\python.exe`.
- **Pitch package.** `docs/pitch/` (9 markdown files + offline `pitch.html`).
- **Troubleshooting guide.** [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- **Certification.** All **10 gates PASS** - pytest **177 passed**,
  `validate_mvp` **10/10 `VALIDATE_MVP: PASS`**, headless sim (300 frames:
  GREEN 91 / YELLOW 106 / RED 103; NO_FACE 40 rows, 0 GREEN, ear/pitch empty;
  microsleeps >= 1 in 126 rows, first at t=26.1 severity RED; recovery tail
  non-RED; header exact 15-col). Full evidence in
  [docs/PITCH_CERTIFICATION.md](PITCH_CERTIFICATION.md).
- **Non-technical start path.** `README_FIRST.txt` (root), then
  [docs/NON_TECH_HANDOFF.md](NON_TECH_HANDOFF.md), then the one-page
  [docs/PRESENTER_FINAL_CHECKLIST.md](PRESENTER_FINAL_CHECKLIST.md).

---

## 1. Executive summary

SkyPsych is a working, edge-native MVP that estimates operator cognitive
fatigue from a webcam or video file using MediaPipe FaceMesh landmarks and
rule-based (not learned) fusion. The entire pipeline
(`ingestion -> vision -> telemetry -> fusion -> alerts -> HUD`) runs locally
with **no cloud calls, no ML training, and no raw-image persistence**.

The MVP is validated end-to-end: **166 pytest tests pass**, the camera-free
validation script reports **10/10 checks PASS**, compileall and imports are
clean, the CLI exits 0, and both headless smoke runs (CSV and JSON Lines) and a
live webcam smoke ran successfully. The privacy audit verdict is **COMPLIANT**.
The system is advisory only and is **not** an aviation safety certification.

## 2. What was delivered - module inventory

### Entry point

| Path | Purpose |
|---|---|
| `main.py` | CLI (`--source/--config/--headless/--output/--show-landmarks/--max-frames`), full pipeline wiring, `CSV_COLUMNS` (15-field schema), `CsvSink` / `JsonLinesSink` / `StdoutSink` |

### `src/ingestion/`

| Path | Purpose |
|---|---|
| `camera.py` | `VideoSource` - opens webcam index / local file (optional RTSP string capability) |
| `preprocess.py` | Mirror / resize / color preprocessing |
| `buffering.py` | Time-keyed frame buffering |

### `src/vision/`

| Path | Purpose |
|---|---|
| `detector.py` | `FaceMeshDetector` - MediaPipe FaceMesh wrapper |
| `landmarks.py` | Landmark extraction helpers |
| `occluder.py` | `classify_coverage` (`LOCKED`/`DEGRADED`/`NO_FACE`), `is_pose_valid` |

### `src/telemetry/`

| Path | Purpose |
|---|---|
| `__init__.py` | Shared `TelemetryPoint` dataclass + `Severity`/`Coverage` types (the contract) |
| `ear.py` | `compute_ear`, `EARSmoother` (EMA) |
| `blinks.py` | `BlinkTracker` - blink rate / duration, microsleep detection |
| `perclos.py` | `PerclosWindow` |
| `headpose.py` | `estimate_head_pose`, `HeadDeviationTracker` |
| `fusion.py` | `FatigueFusion` - Fatigue Index (0-100), microsleep penalty, GREEN/YELLOW/RED, coverage guards |
| `calibration.py` | Calibration support |

### `src/alerts/`

| Path | Purpose |
|---|---|
| `dispatcher.py` | `AlertDispatcher` - hysteresis + cooldown rate-limiting, advisory fan-out |
| `audio.py` | `AudioAlerter` - local advisory chimes (winsound), GREEN never beeped |
| `logger.py` | `TelemetryEventLogger` - allow-list sanitized JSON Lines (memory-only by default) |

### `src/ui/`

| Path | Purpose |
|---|---|
| `hud.py` | `HudOverlay` - dark aviation-style HUD |
| `osd.py` | On-screen display helpers |
| `renderer.py` | `draw_landmarks` face-mesh overlay |

### Scripts

| Path | Purpose |
|---|---|
| `scripts/bootstrap_env.ps1` | Create venv (`py -3.11` with `python` fallback), upgrade pip, install `requirements.txt`, verify imports |
| `scripts/run.ps1` | Run `main.py` with the venv interpreter (`-Source -Headless -Output -MaxFrames -Config -ShowLandmarks`) |
| `scripts/validate.ps1` | Run `pytest -q` then `validate_mvp.py`; prints `VALIDATION PASS`/`FAIL` |
| `scripts/validate_mvp.py` | 10 camera-free end-to-end checks, prints `VALIDATE_MVP: PASS` |

### Tests (`tests/`)

`test_alerts.py`, `test_blinks.py`, `test_coverage.py`, `test_ear.py`,
`test_fusion.py`, `test_headpose.py`, `test_ingestion.py`, `test_main_smoke.py`,
`test_perclos.py`, `test_vision.py`, plus `tests/fixtures/`
(`synthetic_landmarks.py`). **166 tests, all passing.**

### Config, assets, docs

- `config/settings.yaml` - runtime defaults (`ear`, `perclos`, `head_pose`,
  `fatigue`, `severity`, `ui`, `logging`); `config/logging.yaml`.
- `assets/samples/synthetic_no_face.mp4` - bundled 320x240 @ 30 fps synthetic
  clip (no human faces) for automated / file-mode testing; `assets/samples/
  README.md` documents privacy rules for optional operator clips.
- `docs/ARCHITECTURE.md`, `docs/MVP_RUNBOOK.md`, `docs/MVP_VALIDATION_REPORT.md`,
  `docs/PRIVACY_AUDIT.md`, `docs/FINAL_HANDOFF.md`.
- `requirements.txt` - pinned, verified dependency set.

## 3. How to run - command sheet

All from the repository root, using the venv interpreter.

### Bootstrap (once)

```powershell
.\scripts\bootstrap_env.ps1
```

### Live webcam (HUD)

```powershell
.\.venv\Scripts\python.exe main.py --source 0
```

### Video file (HUD)

```powershell
.\.venv\Scripts\python.exe main.py --source assets\samples\synthetic_no_face.mp4
```

### Headless CSV

```powershell
.\.venv\Scripts\python.exe main.py --source assets\samples\synthetic_no_face.mp4 --headless --max-frames 20 --output telemetry_smoke.csv
```

### Headless JSON Lines

```powershell
.\.venv\Scripts\python.exe main.py --source assets\samples\synthetic_no_face.mp4 --headless --max-frames 20 --output telemetry_smoke.json
```

### Script helpers

```powershell
.\scripts\run.ps1 -Source 0
.\scripts\run.ps1 -Source assets\samples\synthetic_no_face.mp4 -Headless -MaxFrames 20 -Output telemetry_smoke.csv
.\scripts\validate.ps1
```

## 4. Validation evidence

| Check | Result |
|---|---|
| Dependency imports | PASS |
| `compileall` | PASS |
| `pytest -q` | **166 passed** |
| `scripts/validate_mvp.py` | **10/10 PASS** (`VALIDATE_MVP: PASS`) |
| `main.py --help` | exit 0 |
| Headless CSV smoke (20 frames) | exit 0, 20 rows, exact 15-col header, all `NO_FACE` + `YELLOW` |
| Headless JSON smoke | 20 JSON lines, same 15 fields |
| Live webcam smoke (30 frames) | exit 0 (physical camera present) |

Details and synthetic scenario fatigue values (GREEN 12.15, YELLOW 57.00,
RED 89.67, microsleep-forces-RED 32.15, NO_FACE t0/t6 = YELLOW) are in
[docs/MVP_VALIDATION_REPORT.md](MVP_VALIDATION_REPORT.md).

## 5. Privacy posture

- Runtime makes **no network calls**; no API keys, tokens, or cloud SDKs.
- **No raw frames / screenshots / video persisted by default.**
- Exports are the **15 abstract `TelemetryPoint` fields** only.
- Alert logs restricted to allow-list
  `schema_version, t, severity, fatigue, message, event_type`; raw-image /
  landmark keys are denied and dropped.
- Advisory output only (UI / audio / log); **no control of any vehicle**.
- Full evidence: [docs/PRIVACY_AUDIT.md](PRIVACY_AUDIT.md) - verdict
  **COMPLIANT**.

## 6. Known issues

1. **mediapipe 0.10.21 stderr noise.** INFO/WARN lines (TensorFlow
   feedback-manager, XNNPACK) print to stderr; harmless, but PowerShell may
   render them as `NativeCommandError` noise.
2. **Wrong `python` on PATH.** Default PATH `python` may be an unrelated
   interpreter - always use `.\.venv\Scripts\python.exe`.
3. **Synthetic sample has no face.** File mode on `synthetic_no_face.mp4`
   exercises NO_FACE / DEGRADED paths (severity stays YELLOW, never GREEN). A
   real non-biometric demo clip is optional for face-detection demonstration.
4. **EMA smoothing lag.** EMA introduces a slight duration lag in metrics.
5. **500 ms microsleep boundary.** A closure of exactly 500 ms is classified per
   config (`microsleep_min_ms=500`).
6. **Alert rate-limiting is intentional.** Hysteresis dwell + cooldown
   suppression in the alert dispatcher throttle alert spam by design.

## 7. Advisory-not-certified disclaimer

SkyPsych is an **advisory research MVP**, not a certified aviation safety
system. It is not a substitute for certified flight-safety equipment, and it
must **never** be used as the sole basis for safety decisions in flight or any
other safety-critical operation. It performs no control of any vehicle or
system; output is UI / audio / log advisory only. Use at your own risk.

## 8. Final verdict

**PASS.**

- All automated checks (tests, validation, compile, imports, CLI) passed
  **without any camera** - the full automated verification is camera-independent.
- The live webcam smoke also passed: a physical camera was available on this
  machine during the final smoke and 30 frames were processed successfully.
- Privacy audit verdict: **COMPLIANT** (no violations found).
- The system is advisory-not-certified; this verdict certifies the MVP meets its
  documented contract, not aviation safety requirements.
