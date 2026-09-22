# SkyPsych — Pitch-Readiness Certification

**Date:** 2026-08-05
**Certification agent:** SUBAGENT D — End-to-End QA and Simulation Certification
**Repo:** `F:\SKY PSYCH\skypsych-ai`
**OS:** Windows (PowerShell 5.1)

## Environment Summary

| Component | Version |
|-----------|---------|
| Python | 3.11.1 (`.venv\Scripts\python.exe`) |
| pip | 26.2.1 |
| OpenCV (cv2) | 4.11.0 |
| MediaPipe | 0.10.21 |
| NumPy | 1.26.4 |
| SciPy | 1.17.1 |
| PyYAML | 6.0.3 |

## Certification Checklist — 10 Pitch-Readiness Gates

### Gate 1 — Environment (.venv + imports) — PASS
- `.\.venv\Scripts\python.exe --version` → `Python 3.11.1`
- `-m pip --version` → `pip 26.2.1 from F:\SKY PSYCH\skypsych-ai\.venv\...`
- `import cv2, mediapipe, numpy, scipy, yaml` → `IMPORTS_OK`
- `compileall -q src tests scripts main.py` → exit 0 → `COMPILE_OK`

### Gate 2 — Tests (pytest) — PASS
- `.\.venv\Scripts\python.exe -m pytest -q` → **177 passed in 19.12s**, exit code 0.

### Gate 3 — MVP Validation (validate_mvp) — PASS
- `scripts\validate_mvp.py` → **passed=10/10**, final line `VALIDATE_MVP: PASS`, exit code 0.
- All 10 checks PASS: IMPORTS_OK, CONFIG_LOADING, TELEMETRY_CONTRACT, SYNTHETIC_GREEN, SYNTHETIC_YELLOW, SYNTHETIC_RED, MICROSLEEP_FORCES_RED, NO_FACE_NEVER_GREEN, HEADLESS_CSV_SCHEMA, ALERT_LOGGER_PRIVACY.

### Gate 4 — Simulation (GREEN/YELLOW/RED/microsleep-RED/coverage-loss/recovery) — PASS
All six phenomena observed in a single headless simulation (300 frames, `--simulate --headless --max-frames 300`). See "Validation Evidence" below.

### Gate 5 — Headless Export (schema + transitions) — PASS
- Exit code 0; 300 telemetry rows written.
- Header is EXACTLY: `t,ear_l,ear_r,ear_avg,perclos,bpm,avg_blink_ms,head_off,pitch,yaw,roll,fatigue,severity,microsleeps,coverage` (15 fields).
- All three severities present: GREEN=91, YELLOW=106, RED=103.
- Output file removed after analysis (no artifacts left in repo).

### Gate 6 — Launchers (all .bat exist, correct paths, .venv) — PASS
- All 6 launchers present: 00_SETUP.bat, 01_VALIDATE.bat, 02_SIM_DEMO.bat, 03_LIVE_CAMERA_DEMO.bat, 04_PITCH_PACKAGE.bat, 05_HELP.bat.
- Every .bat has `cd /d "%~dp0"` on line 2 and a `pause` before `exit`.
- Python invocations use quoted `".\.venv\Scripts\python.exe"` (00_SETUP delegates to `scripts\bootstrap_env.ps1`; the venv existence check is unquoted but benign).
- 02_SIM_DEMO.bat references `--simulate` with `--simulate-duration 45.0 --demo-loop` and explicitly says NO camera needed.
- 01_VALIDATE.bat runs pytest + validate_mvp.py + a short headless sim and prints `VALIDATION COMPLETE` / `VALIDATION FAILED`.
- 03_LIVE_CAMERA_DEMO.bat uses `--source 0`, warns about camera permission ("If a permission popup appears, click Allow"), and falls back to 02_SIM_DEMO.bat on failure.
- 04_PITCH_PACKAGE.bat opens `docs\pitch\*.md` and `pitch.html` via `start ""`.
- 05_HELP.bat opens `docs\TROUBLESHOOTING.md` in Notepad (`start "" notepad`) and prints guidance.
- **Live run:** `cmd /c "01_VALIDATE.bat < nul"` exited 0 and ended with `VALIDATION COMPLETE`. Because this primary path succeeded, the fallback (00_SETUP.bat + standalone 02 headless command) was NOT needed; the headless sim command was already proven by Gate 4/5.

### Gate 7 — Presenter Docs (README_FIRST, guide, pitch scripts, troubleshooting) — PASS
- README_FIRST.txt is simple plain English, states "Do NOT type any commands. Everything is a double-click.", enumerates the double-click sequence (00→01→02→03→04→05), and carries the advisory-only note ("NOT certified aviation or medical equipment ... must not be used for safety-critical decisions").
- docs/SIMULATION_MODE.md and docs/TROUBLESHOOTING.md exist.
- All 9 pitch docs exist: ONE_PAGE_PITCH.md, PITCH_30_SECONDS.md, PITCH_2_MINUTES.md, PITCH_5_MINUTES.md, DEMO_TALK_TRACK.md, NON_TECH_PRESENTER_GUIDE.md, QA_QUESTIONS.md, OBJECTIONS_AND_ANSWERS.md, FINAL_SLIDE_NOTES.md, plus pitch.html.
- docs/NON_TECH_HANDOFF.md and docs/PRESENTER_FINAL_CHECKLIST.md exist (created by the handoff agent after this certification ran); see the note at the bottom of this file.

### Gate 8 — Privacy (no raw frames, no cloud, no biometrics) — PASS
- Zero occurrences of `cv2.imwrite`, `VideoWriter`, `np.save`, `tofile`, `.jpg`-write patterns in `src/` + `main.py`. The only textual matches are a synthetic test fixture in `scripts\validate_mvp.py` (line 175: `"frame_path": "C:/x.jpg"` fed to the alert-logger privacy check to prove the path is NOT stored) and the word "screenshots" in a `main.py` docstring stating nothing is written by default. No production code writes raw frames.
- Zero network imports in `src/` + `main.py` + `scripts/` (`requests`, `urllib`, `http.client`, `socket`, `websocket`, `grpc`, `boto`, `httpx`, `aiohttp`): none found. Zero matches in any `.bat`.
- `docs/pitch/pitch.html` contains **0** `http(s)://` references — no external resources.
- `assets/` contains only the non-biometric synthetic clip `assets\samples\synthetic_no_face.mp4` and `assets\samples\README.md`. No real faces, no biometric assets.

### Gate 9 — UX (double-click only, no typing) — PASS
- README_FIRST.txt and 05_HELP.bat both instruct double-click operation only, with "press any key" for prompt handling. No CLI typing required for the demo sequence.

### Gate 10 — Certificate exists (this file) — PASS
- `docs/PITCH_CERTIFICATION.md` exists at the path below.

## Validation Evidence (recorded command outputs)

Headless simulation — `main.py --simulate --headless --max-frames 300 --output telemetry_sim.csv` (exit 0):

```
ROWS=300
HEADER=t,ear_l,ear_r,ear_avg,perclos,bpm,avg_blink_ms,head_off,pitch,yaw,roll,fatigue,severity,microsleeps,coverage
SEVERITY: GREEN=91 YELLOW=106 RED=103
MICROSLEEP_ROWS=126            (rows with microsleeps >= 1)
MICROSLEEP_RED_ROWS=66         (rows with microsleeps >= 1 AND severity RED)
NO_FACE_ROWS=40
NO_FACE_GREEN_ROWS=0           (NO_FACE rows are NEVER GREEN)
NO_FACE_NONEMPTY_EAR_AVG=0     (ear_avg is EMPTY on NO_FACE rows)
NO_FACE_NONEMPTY_PITCH=0       (pitch is EMPTY on NO_FACE rows)
DEGRADED_ROWS=0
SEVERITY_VALUES=GREEN,RED,YELLOW
```

**Microsleep forces RED (first increment):**
```
FIRST_MICROSLEEP_ROW t=26.1 microsleeps=1 severity=RED fatigue=100.0
PRIOR_ROW              t=25.95 microsleeps=0 severity=RED fatigue=83.8861
SEG idx=172 t=25.8  microsleeps=0 severity=RED
SEG idx=173 t=25.95 microsleeps=0 severity=RED
SEG idx=174 t=26.1  microsleeps=1 severity=RED   <-- microsleeps first increments here; severity is RED
SEG idx=175 t=26.25 microsleeps=1 severity=RED
SEG idx=176 t=26.4  microsleeps=1 severity=RED
```
(This behaviour is also independently asserted by the passing `MICROSLEEP_FORCES_RED` gate in validate_mvp.)

**Recovery tail (last 6 rows of file):**
```
t=44.1  severity=YELLOW coverage=LOCKED
t=44.25 severity=YELLOW coverage=LOCKED
t=44.4  severity=YELLOW coverage=LOCKED
t=44.55 severity=GREEN  coverage=LOCKED
t=44.7  severity=GREEN  coverage=LOCKED
t=44.85 severity=GREEN  coverage=LOCKED
```
After the NO_FACE segment the file returns to non-RED (YELLOW then GREEN). Recovery confirmed.

## Final Verdict

**PITCH-READY: PASS**

| Gate | Check | Result |
|------|-------|--------|
| 1 | Environment (.venv + imports + compile) | PASS |
| 2 | Tests (pytest 177 passed) | PASS |
| 3 | MVP validation (10/10) | PASS |
| 4 | Simulation (all 6 phenomena observed) | PASS |
| 5 | Headless export (schema + transitions) | PASS |
| 6 | Launchers (6 .bat, live 01_VALIDATE → VALIDATION COMPLETE) | PASS |
| 7 | Presenter docs (README_FIRST + pitch set) | PASS |
| 8 | Privacy (no frames, no cloud, no biometrics) | PASS |
| 9 | UX (double-click only) | PASS |
| 10 | Certificate exists (this file) | PASS |

**Blockers: none.**

Note: `docs/NON_TECH_HANDOFF.md` and `docs/PRESENTER_FINAL_CHECKLIST.md` were created by the handoff agent after this certification ran; their presence strengthens Gate 7 and does not change any verdict.
