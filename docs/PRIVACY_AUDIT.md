# SkyPsych — Privacy, Safety & Constraint Audit

Audit owner: SUBAGENT D (Privacy, Safety, and Constraint Audit Agent)
Canonical interpreter: `.\.venv\Scripts\python.exe`
Audit date: **2026-08-05**

---

## (a) Audit Scope & Method

Repositories audited: full tree under `F:\SKY PSYCH\skypsych-ai`, excluding
virtual environments and caches (`.venv`, `.pytest_cache`, `__pycache__`, `.git`
if present — none present as a git repo).

Method:
- Recursive content scan for **persistence** patterns: `cv2.imwrite`, `imwrite`,
  `VideoWriter`, `imencode`, save/screenshot/write-raw/frame-writer and image
  extensions (`.jpg/.png/.bmp/.jpeg`), plus file-write primitives (`open()` in
  write mode, `write()`, `tofile`, `np.save`, `savez`, JSON/CSV writers).
- Recursive content scan for **network/cloud** patterns: `requests`, `urllib`,
  `urllib.request`, `urllib2`, `http.client`, `httpx`, `aiohttp`, `socket`,
  `websocket`, `ssl`, `grpc`, `boto`, `azure`, `cloud`, `upload`, `api_key`,
  `token`, `endpoint`, `ftp`.
- Manual source review of the runtime path: `main.py` + `src/` (alerts, ingestion,
  telemetry, vision, ui), `config/settings.yaml`, and `.gitignore`.
- Constraint compliance verified against: no raw frame persistence; no face
  images/videos/landmark arrays in logs; no cloud/network calls; advisory
  alerting only; `NO_FACE` never treated as normal; alert logs contain abstract
  telemetry only.

---

## (b) Raw Frame Persistence — verdict: **PASS**

No production code paths write raw camera/video frames, faces, or images to
disk. Frames exist only in memory and are dropped each loop.

### Evidence table — persistence-pattern hits

| Pattern | File:Line | Verdict | Notes |
|---|---|---|---|
| `cv2.VideoWriter` | `tests/test_ingestion.py:142` | **ALLOWED** | Test fixture writes a synthetic temp clip to `tmp_path` to feed the pipeline; not production. |
| `cv2.VideoWriter` | `tests/test_main_smoke.py:63` | **ALLOWED** | Same — synthetic temp input clip fixture. |
| `.jpg/.png/.bmp` suffix list | `tests/test_main_smoke.py:220` | **ALLOWED** | Positive/negative assertion: verifies **no** raw artifacts are written; it is an anti-persistence guard, not a writer. |
| `"frame_path": "...jpg"`, `"image": "raw-frame..."` | `tests/test_alerts.py:188-189` | **ALLOWED** | Probe payload feeding the logger sanitizer to prove forbidden keys are dropped; assertion checks the sanitized output excludes them. |
| `open(..., "a")` + `write` | `src/alerts/logger.py:91,64` | **ALLOWED** | Appends **abstract telemetry JSON Lines** (whitelist only, see (d)); never raw frames. |
| `open(...,"w")` + csv/JSON writers | `main.py:237,256` (`CsvSink`/`JsonLinesSink`) | **ALLOWED** | Exports the **15-field abstract TelemetryPoint** schema (see (d)); no image data. |
| All `imwrite / VideoWriter / imencode / tofile / np.save` | entire `src/` + `main.py` | **ALLOWED (none found)** | **Zero matches** in production source. |
| `.gitignore` `*.png_original`, `frames/`, `captures/` | `.gitignore:59,61-63` | **ALLOWED (defensive)** | Documents that raw frames/captures must never be persisted. |

**No VIOLATIONS found.** The only writers in the entire runtime path write
abstract telemetry (CSV/JSON), not frames or face data.

---

## (c) Cloud / Network Dependency — verdict: **PASS**

### Evidence table — network-pattern hits

| Pattern | File:Line | Verdict | Notes |
|---|---|---|---|
| `endpoint` | `tests/fixtures/synthetic_landmarks.py:47` | **ALLOWED** | `np.linspace(..., endpoint=False)` — keyword arg, not a network term. |
| `cloud` / `no cloud` | `main.py:10,26`; docstrings in `audio.py`, `logger.py`, `detector.py`; `config/*.yaml`; `docs/*` | **ALLOWED** | Documentation/comment affirmations of the no-cloud constraint. |
| `requests` / `urllib` / `urllib2` / `http.client` / `httpx` / `aiohttp` / `socket` / `websocket` / `ssl` / `grpc` / `boto` / `azure` / `upload` / `ftp` | entire `src/` + `main.py` | **ALLOWED (no imports)** | **Zero runtime imports or calls.** |
| Optional RTSP input string | `src/ingestion/camera.py:1-146` | **ALLOWED** | `VideoSource` accepts a file **or** RTSP string only as an *operator-supplied input* handed to `cv2.VideoCapture`. No egress code, no HTTP client, no telemetry upload. Not activated by the MVP runbook (webcam index / local file). No cloud dependency. |

The main runtime loop (`main.py`) makes **no network calls** and imports no
networking library. Networking libraries do not appear anywhere in `src/` or
`main.py`.

> **Build-time vs runtime note:** `pip install` in bootstrap is a **dev-time
> operation**, not a runtime call. The installed process performs zero network
> egress. MediaPipe model files (if any) are expected to be pre-provisioned
> locally (see `.gitignore` `.mp_model_cache/`); the runtime does not fetch them.

---

## (d) Log Content Whitelist — verdict: **PASS**

Read: `src/alerts/logger.py`.

- Persisted fields: **exactly** the whitelist
  `schema_version`, `t`, `severity`, `fatigue`, `message`, `event_type`
  (`_SAFE_FIELDS`, `logger.py:23-24`).
- A deny-list (`_FORBIDDEN_KEYS`, `logger.py:27-31`) blocks
  `image, frame, frame_path, path, file, face, landmark(s), ear_l, ear_r,
  ear_avg, pitch, yaw, roll, pixels, base64, bbox, coords, coordinates, photo`.
- Any other key in an incoming event is **silently dropped**
  (`_sanitize`, `logger.py:93-112`); only whitelisted scalar values are coerced.
- `output_path=None` (default) keeps the logger **memory-only** — nothing touches
  disk.

Dispatch events (`src/alerts/dispatcher.py:150-155`) are built as plain
abstract dicts: `{"t", "severity", "fatigue", "message"}` — **no** raw frames,
coordinates, landmark arrays, or image paths. Test `test_alerts.py:188-189`
confirms the sanitizer drops injected `frame_path`/`image` fields.

The headless/CSV/JSON export (`main.py:53-57, 200-218`) writes only the
15 abstract `TelemetryPoint` fields `t, ear_l, ear_r, ear_avg, perclos, bpm,
avg_blink_ms, head_off, pitch, yaw, roll, fatigue, severity, microsleeps,
coverage` — numeric/scalar abstract metrics, never the underlying images or
landmark coordinates.

---

## (e) Coverage Honesty (NO_FACE / DEGRADED) — verdict: **PASS**

Read `src/telemetry/fusion.py`, `src/vision/occluder.py`, `main.py`.

- Coverage is classified explicitly (`occluder.py:29-110`): `NO_FACE` (no face),
  `DEGRADED` (present but low landmark quality / invalid pose), `LOCKED`.
  The invariant is documented: *never report LOCKED when no face is present*
  (`occluder.py:10-11`).
- **NO_FACE never yields GREEN.** In `fusion.py`:
  - no prior state → forced `YELLOW` (`fusion.py:203-205`);
  - prior state exists → prior severity preserved for up to 5 s
    (`NO_FACE_GRACE_SECONDS`, `fusion.py:206-211`), then forced `YELLOW`;
  - a recent microsleep (≤3 s) keeps RED, overriding the grace path
    (`fusion.py:198, 109-110`).
- `DEGRADED` is an explicit, surfaced state (metrics carry `coverage`), and
  `main.py:428-435` emits `NO_FACE` explicitly when the face is absent, never
  fabricating filled metrics.
- **Microsleep forces RED** (`_severity_for_fi`, `fusion.py:109-110`), and the
  dispatcher treats microsleep RED as urgent/immediate
  (`dispatcher.py:114-119`).

---

## (f) Advisory Alerting — verdict: **PASS**

Read `src/alerts/dispatcher.py` and `src/alerts/audio.py`.

- Dispatcher is transition-only + hysteresis (1.0 s dwell) + per-severity
  cooldowns (YELLOW 5 s, RED 10 s) to throttle spam (`dispatcher.py:32-34`).
- Emitted events are **abstract telemetry only**, fanned out to an optional
  in-process logger and/or `AudioAlerter`; sink failures are swallowed
  (`dispatcher.py:160-169`).
- `AudioAlerter` only emits local advisory chimes (`winsound.Beep`) for
  YELLOW/RED and otherwise records state; failures are silent (`audio.py:26-72`);
  GREEN is never beeped. **No control of any vehicle, no mechanical/automatic
  action** — alerting is purely display/audio/log advisory.

---

## (g) Build-Time vs Runtime Network

`pip install -r requirements.txt` (bootstrap) performs network access for **dev
setup only**. The runtime application (`main.py` + `src/`) performs **no**
network calls and holds **no** API keys, tokens, endpoints, or cloud SDKs. This
satisfies the "no cloud/network calls" constraint for the running system.

---

## (h) Residual Risks / Notes

1. **Operator-supplied inputs must remain non-biometric.** `--source` may point
   at a local `.mp4` (`assets/samples/`). Any demo clip containing recognizable
   faces/biometrics is an *operator choice*, not a persistence issue; the README
   (`assets/samples/README.md:12`) already warns against committing biometric
   clips. Keep sample media synthetic/anonymous.
2. **Optional RTSP input** (`camera.py`) is a capability, not a dependency. If a
   future operator streams from a remote camera, the connection is outbound to a
   camera the operator controls — still no cloud/telemetry egress. Document usage
   if enabled.
3. **Future features must preserve the invariant.** Any change that adds
   `cv2.imwrite`, `VideoWriter`, `imencode`, face/landmark serialization, or a
   networking client into `src/` or `main.py` would violate constraints. The
   `save_raw_frames` key in `config/settings.yaml:44` is `false`; if later wired
   to production it must remain off to stay compliant.
4. **Log sanitization is allow-list, not just deny-list.** Even if a new field is
   added to an event, it will **not** be persisted unless added to `_SAFE_FIELDS`.
   This is defense-in-depth; keep it.
5. `.gitignore` correctly ignores `telemetry*.csv/json`, `frames/`, `captures/`,
   `logs/`, and `.venv/` — but it is a *commit-time* guard, not a runtime guard.
   It does not prevent a future feature from writing frames; constraints are
   enforced by code discipline (see item 3).

---

## (i) Constraint Compliance Verdict — **COMPLIANT**

| Constraint | Verdict |
|---|---|
| 1. No raw frame persistence | **COMPLIANT** |
| 2. No face images/videos/landmark arrays in logs | **COMPLIANT** |
| 3. No cloud/network calls (runtime) | **COMPLIANT** |
| 4. Advisory alerting only | **COMPLIANT** |
| 5. NO_FACE never silently treated as normal | **COMPLIANT** |
| 6. Alert logs: abstract telemetry only | **COMPLIANT** |

**Overall verdict: COMPLIANT.** No violations found.

---

## (j) Timestamp

Audit completed: **2026-08-05**