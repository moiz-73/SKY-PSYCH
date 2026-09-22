# SkyPsych - Architecture

Edge-native, privacy-preserving cognitive-fatigue telemetry for operators.

## Pipeline

```
ingestion -> vision -> telemetry -> fusion -> alerts -> HUD
```

Stage-by-stage responsibility:

1. **ingestion** — `src/ingestion/` — opens the camera (device index) or a
   video file, applies preprocessing (mirror/resize/color) and maintains a
   time-keyed buffer. Frame sources emit timestamps, never frame counts.

2. **vision** — `src/vision/` — runs MediaPipe FaceMesh, extracts landmarks,
   and evaluates coverage/occlusion. No raw frame persistence at any point.

3. **telemetry** — `src/telemetry/` — computes EAR, PERCLOS, blink dynamics,
   microsleeps, and head pose; emits the shared `TelemetryPoint` dataclass
   (see `src/telemetry/__init__.py`).

4. **fusion** — `src/telemetry/fusion.py` — combines metrics into a composite
   Fatigue Index (0-100) with a microsleep penalty, and maps it to
   GREEN/YELLOW/RED severity. Includes coverage guards so the system never
   reports false-normal when coverage is lost.

5. **alerts** — `src/alerts/` — dispatches severity changes to local audio and
   structured telemetry logging. No cloud, no remote endpoints.

6. **HUD** — `src/ui/` — renders the dark aviation-style overlay.

## Privacy & locality guarantees

- **All processing is local.** No cloud dependency, no dashboard backend, no
  authentication, no network egress.
- **Raw frames are transient.** Frames exist only in memory during processing
  and are never written to disk.
- **Only abstract telemetry is logged.** The `TelemetryPoint` record (timestamps
  and derived metrics) is the only thing persisted — never the raw image.

## Safety

This is an advisory MVP and is **not** a certified aviation safety system.