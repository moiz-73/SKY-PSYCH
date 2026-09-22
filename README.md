# SkyPsych AI

Privacy-preserving, edge-native cognitive-fatigue telemetry MVP for operators. Runs entirely on your machine — no cloud, no ML training, no raw-image persistence.

> **IMPORTANT: This is an advisory edge MVP, not a certified aviation safety system.** It must never be used as the sole basis for safety decisions in flight or other safety-critical operations.

## Quick Start (Non-Technical)

**No typing required — everything is a double-click:**

1. `00_SETUP.bat` — run once (installs demo programs, takes a few minutes)
2. `01_VALIDATE.bat` — run once; wait for **VALIDATION COMPLETE**
3. `02_SIM_DEMO.bat` — guaranteed demo, no camera needed; shows GREEN → YELLOW → RED → microsleep → coverage-loss → recovery
4. `03_LIVE_CAMERA_DEMO.bat` — optional, only if webcam available
5. `05_HELP.bat` — if anything is stuck
6. `04_PITCH_PACKAGE.bat` — opens talking points for the pitch

For first-time presenters, start with `README_FIRST.txt`, then read [docs/NON_TECH_HANDOFF.md](docs/NON_TECH_HANDOFF.md).

## Overview

- **Edge-native and local-only.** The pipeline `ingestion → vision → telemetry → fusion → alerts → HUD` runs in one process with no cloud dependency, no dashboard backend, and no network egress.
- **Rule-based fusion, no ML training.** EAR, PERCLOS, blink dynamics, microsleep events, and head-pose deviation are derived from MediaPipe FaceMesh landmarks and combined through explicit rules (weighted fatigue + microsleep penalty). No learned model, no training pipeline.
- **Privacy-first.** Raw frames are transient (memory only), nothing is uploaded, and only abstract telemetry is persisted. See [docs/PRIVACY_AUDIT.md](docs/PRIVACY_AUDIT.md).

## Features

- Webcam or video-file input via OpenCV
- MediaPipe FaceMesh landmark extraction with coverage classification (`LOCKED` / `DEGRADED` / `NO_FACE`)
- Ocular telemetry: EAR (EMA-smoothed), PERCLOS over rolling window, blink rate/duration, microsleep detection (closure ≥ 500 ms)
- Head-pose deviation tracking (pitch / yaw / roll)
- Composite Fatigue Index fusion with microsleep penalty and GREEN/YELLOW/RED severity mapping
- Coverage honesty: `NO_FACE` never yields a false-normal GREEN reading
- Advisory alerts (local audio chime + abstract telemetry log) for YELLOW/RED
- HUD overlay (GUI mode) and headless CSV / JSON Lines export
- Automated validation: `pytest` suite + camera-free `scripts/validate_mvp.py`

## Prerequisites

- Windows with PowerShell 5.1 or newer
- Python 3.11 preferred (3.10+ works). A working `py` launcher or `python` on PATH
- A webcam for live mode (optional for file / headless modes; synthetic sample bundled for camera-free runs)

## Quick Start (Technical)

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run validation
python scripts/validate_mvp.py

# Run simulation demo (no camera)
python main.py --mode sim

# Run with webcam
python main.py --mode live

# Run headless with video file
python main.py --mode file --input sample.mp4 --output telemetry.csv
```

## Architecture

```
Webcam / Video File
        │
        ▼
┌─────────────────┐
│   Ingestion     │  ← OpenCV frame capture
└────────┬────────┘
         │
    ┌────▼────┐
    │  Vision  │  ← MediaPipe FaceMesh (468 landmarks)
    └────┬────┘
         │
    ┌────▼────────┐
    │  Telemetry   │  ← EAR, PERCLOS, blink, microsleep, head pose
    └────┬────────┘
         │
    ┌────▼──────┐
    │  Fusion    │  ← Weighted Fatigue Index (0-100) + severity
    └────┬──────┘
         │
    ┌────▼──────────────┐
    │  Alerts + Export   │  ← HUD overlay / CSV / JSONL / audio chime
    └───────────────────┘
```

## Fatigue Index

The composite Fatigue Index (0–100) is computed from:

| Component | Weight | Source |
|---|---|---|
| EAR (Eye Aspect Ratio) | 30% | MediaPipe landmarks 33–133, 362–263 |
| PERCLOS | 25% | % time eyes closed over rolling window |
| Blink dynamics | 20% | Rate + duration deviation from baseline |
| Head pose | 15% | Pitch/yaw/roll deviation |
| Microsleep penalty | 10% | +20 per event (closure ≥ 500ms) |

**Severity thresholds:**

| Range | Severity | Action |
|---|---|---|
| 0–39 | GREEN | No alert |
| 40–69 | YELLOW | Advisory chime + log |
| 70–100 | RED | Urgent chime + log + HUD warning |

## Project Structure

```
SKY-PSYCH/
├── main.py                  # Entry point (GUI / headless)
├── config/
│   ├── settings.yaml        # Detection thresholds
│   └── logging.yaml         # Log configuration
├── scripts/
│   ├── validate_mvp.py      # Automated validation
│   └── analyze_telemetry.py # Post-session analysis
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PRIVACY_AUDIT.md
│   ├── SIMULATION_MODE.md
│   ├── TROUBLESHOOTING.md
│   └── pitch/               # Pitch deck and certification docs
├── assets/
│   └── samples/             # Synthetic sample videos
└── 00_SETUP.bat ... 05_HELP.bat  # One-click Windows launchers
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Privacy Audit](docs/PRIVACY_AUDIT.md)
- [Simulation Mode](docs/SIMULATION_MODE.md)
- [Non-Tech Handoff](docs/NON_TECH_HANDOFF.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Disclaimer

This system is advisory-only. It is **not** certified aviation or medical equipment, it does **not** prevent fatigue, and it must not be used for safety-critical decisions.

## License

MIT
