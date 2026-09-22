# SkyPsych - MVP Runbook

Step-by-step guide to set up the environment and run the MVP on Windows.
Everything below was verified against the canonical interpreter
`.\.venv\Scripts\python.exe` (Python 3.11.1, pip 26.2.1).

## Prerequisites

- **Windows** with **PowerShell 5.1 or newer** (the `.ps1` scripts are
  PowerShell 5.1 compatible).
- **Python 3.11 preferred** (3.10+ works). Either the `py` launcher (with a
  `3.11` installation) or a plain `python` on PATH.
- **A webcam** for live mode (optional for file / headless modes).
- A working network connection for the one-time `pip install` during bootstrap
  (the runtime itself makes no network calls).

## 1. Environment setup

### 1a. One-shot bootstrap (recommended)

From the repository root:

```powershell
.\scripts\bootstrap_env.ps1
```

What it does (see `scripts/bootstrap_env.ps1`):

1. Creates `.venv` if it does not exist, preferring `py -3.11 -m venv .venv` and
   falling back to `python -m venv .venv`.
2. Upgrades pip inside the venv.
3. Installs `requirements.txt` into the venv.
4. Prints the canonical interpreter path and an `IMPORTS_OK` confirmation.

### 1b. Manual steps (fallback, same result)

```powershell
# 1) Create the virtual environment
py -3.11 -m venv .venv          # or: python -m venv .venv

# 2) Upgrade pip
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 3) Install pinned dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 4) Verify imports
.\.venv\Scripts\python.exe -c "import cv2, mediapipe, numpy, scipy, yaml, pytest; print('IMPORTS_OK')"
```

Pinned dependency set (installed versions in parentheses):

| Package | Constraint | Installed |
|---|---|---|
| opencv-python | `>=4.8.0,<5.0.0` | 4.11.0.86 |
| mediapipe | `==0.10.21` | 0.10.21 |
| numpy | `>=1.24.0,<2.0.0` | 1.26.4 |
| scipy | `>=1.10.0` | 1.17.1 |
| PyYAML | `>=6.0` | 6.0.3 |
| pytest | `>=7.0` | 9.1.1 |
| protobuf | `>=4.25.0,<5.0.0` | 4.25.9 |

> **Always use `.\.venv\Scripts\python.exe`.** A bare `python` on PATH may
> resolve to an unrelated interpreter.

## 2. Run modes (canonical commands)

All commands run from the repository root. MediaPipe may print INFO/WARN lines
to stderr while running - this is harmless (see Troubleshooting).

### Webcam mode (live HUD)

```powershell
.\.venv\Scripts\python.exe main.py --source 0
```

Opens camera index `0` and shows the dark aviation-style HUD. Press `Q` or
`Esc` to exit.

### File mode (video file, HUD)

```powershell
.\.venv\Scripts\python.exe main.py --source assets\samples\synthetic_no_face.mp4
```

Bundled synthetic sample (320x240 @ 30 fps, ~6 s, procedural shapes, no human
faces). It exercises the NO_FACE / DEGRADED paths. A real `demo.mp4` is
optional and operator-supplied - keep it synthetic / de-identified.

### Headless mode - telemetry to CSV

```powershell
.\.venv\Scripts\python.exe main.py --source assets\samples\synthetic_no_face.mp4 --headless --max-frames 20 --output telemetry_smoke.csv
```

### Headless mode - telemetry to JSON Lines

```powershell
.\.venv\Scripts\python.exe main.py --source assets\samples\synthetic_no_face.mp4 --headless --max-frames 20 --output telemetry_smoke.json
```

`--output` with a `.json` extension writes JSON Lines; anything else writes CSV.
Headless with no `--output` prints JSON Lines to stdout. Both formats share the
same 15-field schema:

```
t,ear_l,ear_r,ear_avg,perclos,bpm,avg_blink_ms,head_off,pitch,yaw,roll,fatigue,severity,microsleeps,coverage
```

### CLI flags

| Flag | Meaning |
|---|---|
| `--source` | Required. Camera index (e.g. `0`) or a video file path. |
| `--config` | YAML settings (default `config/settings.yaml`). |
| `--headless` | Disable the HUD window; telemetry to file / stdout. |
| `--output` | CSV or JSON Lines telemetry file. |
| `--show-landmarks` | Draw the face-mesh landmark overlay on the HUD. |
| `--max-frames` | Stop after N frames (useful for testing). |

## 3. Scripts

### `scripts\run.ps1` - run with the venv interpreter

```powershell
# Webcam
.\scripts\run.ps1 -Source 0

# Headless file run writing CSV (verified exit 0)
.\scripts\run.ps1 -Source assets\samples\synthetic_no_face.mp4 -Headless -MaxFrames 20 -Output telemetry_smoke.csv

# Headless JSON
.\scripts\run.ps1 -Source assets\samples\synthetic_no_face.mp4 -Headless -MaxFrames 20 -Output telemetry_smoke.json

# Options
.\scripts\run.ps1 -Source 0 -Config config\settings.yaml -ShowLandmarks
```

`run.ps1` parameters: `-Source` (mandatory), `-Headless` (switch), `-Output`,
`-MaxFrames` (int, 0 = unset), `-Config` (default `config/settings.yaml`),
`-ShowLandmarks` (switch). It prints the exact command line before running and
propagates the exit code.

### `scripts\validate.ps1` - tests + validation in one step

```powershell
.\scripts\validate.ps1
```

Runs `pytest -q`, then `scripts/validate_mvp.py`. Prints `VALIDATION PASS`
(green) on success or `VALIDATION FAIL` (red) on the first failure, with a
non-zero exit code.

## 4. Testing and validation

### Unit / integration tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: **166 passed**.

### End-to-end MVP validation (camera-free)

```powershell
.\.venv\Scripts\python.exe scripts\validate_mvp.py
```

Expected: **10/10 checks PASS** and final line `VALIDATE_MVP: PASS`. The 10
checks are: `IMPORTS_OK`, `CONFIG_LOADING`, `TELEMETRY_CONTRACT`,
`SYNTHETIC_GREEN`, `SYNTHETIC_YELLOW`, `SYNTHETIC_RED`,
`MICROSLEEP_FORCES_RED`, `NO_FACE_NEVER_GREEN`, `HEADLESS_CSV_SCHEMA`,
`ALERT_LOGGER_PRIVACY`. No camera or human face is required.

### CLI sanity

```powershell
.\.venv\Scripts\python.exe main.py --help
```

Expected: exit code 0 and usage text.

## 5. Troubleshooting

### `python` resolves to the wrong interpreter

A bare `python` on PATH may point at an unrelated Python. **Always invoke
`.\.venv\Scripts\python.exe`.** Check which interpreter you are using:

```powershell
.\.venv\Scripts\python.exe --version   # -> Python 3.11.1
```

If `.venv` is missing, re-run `.\scripts\bootstrap_env.ps1`.

### MediaPipe INFO/WARN lines on stderr (NativeCommandError)

mediapipe 0.10.21 writes INFO/WARN lines to stderr (TensorFlow
feedback-manager, XNNPACK). They are **harmless** and do not affect results.
In PowerShell they may render as red `NativeCommandError` text. The `.ps1`
scripts deliberately use `$ErrorActionPreference = 'Continue'` and check
`$LASTEXITCODE` explicitly so this noise does not abort a run.

### Camera errors in webcam mode

- Make sure the index is correct (`--source 0` for the default camera).
- Close other applications holding the camera (video calls, OBS, other
  instances of SkyPsych).
- If OpenCV GUI is unavailable the process degrades to headless with a warning
  to stderr instead of crashing.

### Missing-file errors in file mode

- Use a path relative to the repository root, e.g.
  `assets\samples\synthetic_no_face.mp4`.
- The bundled sample is `synthetic_no_face.mp4` (exists under `assets/samples/`).
  A `demo.mp4` is **not** shipped; it is optional and operator-supplied.
- `--output` files are written to the current working directory; run from the
  repository root so paths resolve predictably.

### Missing venv

If `.\.venv\Scripts\python.exe` does not exist, the `.ps1` scripts exit with a
clear FAIL message. Re-run `.\scripts\bootstrap_env.ps1` first.
