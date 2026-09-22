# SkyPsych - MVP Validation Report

Recorded validation results for the SkyPsych MVP at
`F:\SKY PSYCH\skypsych-ai`. All commands were executed for real on this
machine and captured below.

- Canonical interpreter: `.\.venv\Scripts\python.exe` (Python 3.11.1, pip
  26.2.1).
- Validation date: **2026-08-05**.
- Repository state: not a git repo; dependencies installed per
  `requirements.txt`.

## 1. Environment

| Item | Expected | Recorded |
|---|---|---|
| Interpreter | `.\.venv\Scripts\python.exe` exists | Present; Python 3.11.1, pip 26.2.1 |
| opencv-python | `>=4.8.0,<5.0.0` | 4.11.0.86 |
| mediapipe | `==0.10.21` | 0.10.21 |
| numpy | `>=1.24.0,<2.0.0` | 1.26.4 |
| scipy | `>=1.10.0` | 1.17.1 |
| PyYAML | `>=6.0` | 6.0.3 |
| pytest | `>=7.0` | 9.1.1 |
| protobuf | `>=4.25.0,<5.0.0` | 4.25.9 |

## 2. Validation matrix

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Dependency imports | `python -c "import cv2, mediapipe, numpy, scipy, yaml, pytest"` | PASS - all imported |
| 2 | Byte-compile | `python -m compileall` (project tree) | PASS - OK |
| 3 | Unit / integration suite | `python -m pytest -q` | PASS - **166 passed** |
| 4 | MVP validation script | `python scripts/validate_mvp.py` | PASS - **10/10 checks** |
| 5 | MVP validation banner | (same run) | `VALIDATE_MVP: PASS` |
| 6 | CLI help | `python main.py --help` | PASS - exit 0 |
| 7 | Headless CSV smoke | `python main.py --source assets/samples/synthetic_no_face.mp4 --headless --max-frames 20 --output telemetry_smoke.csv` | PASS - exit 0, 20 points |
| 8 | Headless JSON smoke | same command with `--output telemetry_smoke.json` | PASS - 20 JSON lines, same 15 fields |
| 9 | Live webcam smoke | `python main.py --source 0 --max-frames 30` | PASS - exit 0, 30 frames processed |

### Headless CSV details

`telemetry_smoke.csv` header exactly:

```
t,ear_l,ear_r,ear_avg,perclos,bpm,avg_blink_ms,head_off,pitch,yaw,roll,fatigue,severity,microsleeps,coverage
```

- 20 data rows written (one per processed frame).
- Every row: `coverage=NO_FACE`, `severity=YELLOW`.
- **Never GREEN**, and never fabricated `ear` / `pitch` values (they are empty /
  null when no face is present).
- The JSON Lines output was verified to carry the same 15 abstract fields.

### Live webcam smoke note

A physical camera was present on this machine and produced 30 processed frames.
This is the **only** check that touches a camera; checks 1-8 above are fully
camera-independent (synthetic inputs / file mode only).

## 3. Synthetic scenario results

From `scripts/validate_mvp.py` (`validate_mvp.py:109-144`) with recorded
fatigue values:

| Scenario | Inputs | Severity | Fatigue |
|---|---|---|---|
| GREEN (low fatigue) | perclos=5.0, bpm=18, blink 120 ms, head_off=0.02 | GREEN | 12.15 |
| YELLOW (elevated) | perclos=50.0, bpm=18, blink 300 ms, head_off=0.10 | YELLOW | 57.00 |
| RED (severe) | perclos=85.0, bpm=5, blink 600 ms, head_off=0.90 | RED | 89.67 |
| Microsleep forces RED | low-fatigue inputs + `microsleep_recent_3s=True` | RED (despite fatigue < 40) | 32.15 |
| NO_FACE, t=0 | coverage=NO_FACE, no ocular inputs | YELLOW (never GREEN) | - |
| NO_FACE, t=6 (> 5 s grace) | coverage=NO_FACE, no ocular inputs | YELLOW (never GREEN) | - |

Properties verified by these scenarios:

- **Microsleep forces RED** even at low computed fatigue (`_severity_for_fi`,
  `fusion.py:109-110`).
- **NO_FACE never yields GREEN**: with no prior state the system forces YELLOW;
  with prior state it preserves severity for up to 5 s
  (`NO_FACE_GRACE_SECONDS`), then forces YELLOW. At t=0 and t=6 severity is
  YELLOW in both cases.
- The real headless smoke corroborates this: all 20 rows are
  `NO_FACE` + `YELLOW`, matching the synthetic `NO_FACE_NEVER_GREEN` check.

## 4. Privacy audit summary

Referenced from [docs/PRIVACY_AUDIT.md](PRIVACY_AUDIT.md) (created by the
privacy audit agent, not modified here).

| Constraint | Verdict |
|---|---|
| No raw frame persistence | COMPLIANT |
| No face images/videos/landmark arrays in logs | COMPLIANT |
| No cloud/network calls (runtime) | COMPLIANT |
| Advisory alerting only | COMPLIANT |
| NO_FACE never silently treated as normal | COMPLIANT |
| Alert logs: abstract telemetry only | COMPLIANT |

**Overall privacy verdict: COMPLIANT.** No violations found.

## 5. Verdict

**PASS.** All automated checks pass (166 pytest tests, 10/10 validate_mvp
checks, compileall clean, imports clean, CLI help exit 0), both headless smoke
runs produced correct telemetry (CSV and JSON), and the live webcam smoke ran
successfully with a physical camera present. The system is camera-independent
for all automated verification; the camera was used only for the final live
smoke. Per the advisory-not-certified disclaimer, this is a validation of the
advisory MVP and is **not** an aviation certification.
