# SkyPsych AI - Simulation Mode

Simulation mode runs the **full SkyPsych AI pipeline with no webcam and no
MediaPipe face detection**. It is designed for demos and test runs: a presenter
opens the same security HUD and the same headless telemetry export they would
get from a live camera, driven entirely by a deterministic in-memory fatigue
timeline.

Everything is synthetic. No camera, no human face, and no frame (raw video,
screenshot, or image) is ever captured or written to disk.

---

## What simulation is

The real pipeline is:

```
ingestion -> vision(FaceMeshDetector) -> ear/blink/perclos/headpose
   -> FatigueFusion -> AlertDispatcher -> HUD / CSV / JSON Lines export
```

Simulation replaces only the left-hand side. Instead of opening a video source
and detecting a face, `src/simulation.py` synthesizes the exact metrics dict
that `FatigueFusion.update()` expects (`ear_avg`, `perclos`, `bpm`,
`avg_blink_ms`, `head_off`, `pitch/yaw/roll`, `microsleep_*`, `coverage`).

The **same** `FatigueFusion`, severity thresholds, alert dispatcher, event
logger, `HudOverlay`, `TelemetryPoint` schema, and CSV/JSON sinks are used, so
the demo behaves exactly like the real system -- including the privacy rules
(telemetry only, no raw frames).

In GUI mode a non-biometric canvas (dark base with drifting geometric shapes,
**no faces, no text**) is rendered purely so the HUD has a surface to draw on,
and a "SIMULATION MODE" caption is shown along the bottom.

---

## The timeline

The default timeline is 45 simulated seconds. It walks through every severity
state in order so a demo shows the full behavior of the fusion + alert + HUD
stack:

| Time (s) | Phase        | What happens                                                                 |
|----------|--------------|------------------------------------------------------------------------------|
| 0 - 10   | `GREEN`      | Healthy: EAR ~0.28, PERCLOS ~5, BPM ~18, avg blink ~120 ms, tiny head offset. |
| 10 - 20  | `YELLOW`     | Rising fatigue: PERCLOS ramps 5 -> 45, avg blink 120 -> 260 ms, BPM drops toward 10, head offset 0.02 -> 0.35. |
| 20 - 26  | `RED`        | High fatigue: PERCLOS ~70, avg blink ~500 ms, BPM ~6, head offset ~0.7.       |
| 26 - 30  | `MICROSLEEP` | A microsleep event: `microsleep_recent_3s=True` **forces RED** through fusion; `microsleeps` increments to 1; the alert dispatcher logs a RED "Microsleep detected" alert. |
| 30 - 36  | `NO_FACE`    | Coverage lost: EAR/pose are `None` (never fabricated); conservative signal values; fusion shows the NO FACE warning and is **never GREEN**. |
| 36 - 45  | `RECOVERY`   | Face restored: coverage `LOCKED`, fatigue ramps back down to GREEN/low YELLOW by the end. |

The severity sequence a presenter can expect (via the HUD banner and the
telemetry export):

```
GREEN -> YELLOW -> RED -> RED (microsleep-forced) -> NO_FACE (never GREEN)
   -> GREEN/YELLOW recovery
```

---

## CLI flags

| Flag                    | Default | Meaning                                                        |
|-------------------------|---------|----------------------------------------------------------------|
| `--simulate`            | off     | Enable camera-free simulation mode. `--source` is not required.|
| `--simulate-duration`   | `45.0`  | Total simulated timeline seconds.                              |
| `--demo-loop`           | off     | Loop the timeline indefinitely (until Q/ESC or `--max-frames`).|
| `--sim-fps`             | `20.0`  | Timeline seconds advanced per rendered frame in unbounded (GUI) mode. |
| `--max-frames`          | none    | Stop after N frames. When given, the timeline is spread across the whole frame budget so every phase is observable. |
| `--output`              | none    | CSV (`*.csv`) or JSON Lines (`*.json`) telemetry file. Headless without `--output` prints JSON Lines to stdout. |

All existing flags (`--headless`, `--show-landmarks`, `--config`, ...) still
work. In simulation mode `--show-landmarks` has no effect (no landmarks exist).

---

## Running a demo

### GUI (the live HUD)

```powershell
.\.venv\Scripts\python.exe main.py --simulate
```

A window opens showing the dark aviation HUD driven by the synthetic timeline.
Watch the severity banner move GREEN -> YELLOW -> RED -> microsleep RED ->
NO FACE warning -> recovery. Press **Q** or **ESC** to exit.

To loop the 45-second timeline forever:

```powershell
.\.venv\Scripts\python.exe main.py --simulate --demo-loop
```

### Headless (telemetry export)

```powershell
.\.venv\Scripts\python.exe main.py --simulate --headless --max-frames 300 --output telemetry_sim.csv
```

This writes the standard 15-column CSV header and 300 rows covering the whole
timeline:

```
t,ear_l,ear_r,ear_avg,perclos,bpm,avg_blink_ms,head_off,pitch,yaw,roll,fatigue,severity,microsleeps,coverage
```

The severity column will contain `GREEN`, `YELLOW` and `RED`, rows where
`microsleeps >= 1`, `NO_FACE` rows that are never `GREEN`, and a final
recovery back to `GREEN`/`YELLOW`.

JSON Lines is chosen automatically for `*.json`:

```powershell
.\.venv\Scripts\python.exe main.py --simulate --headless --max-frames 300 --output telemetry_sim.json
```

---

## Privacy notes

* **No webcam.** Simulation never opens a camera device.
* **No MediaPipe face detection.** The FaceMesh detector is never imported or
  instantiated in simulation mode.
* **No frames written.** `make_sim_frame` only produces in-memory canvas pixels
  for the HUD; nothing is saved to disk.
* **Same telemetry schema.** Export contains only the 15 abstract
  `TelemetryPoint` fields; during `NO_FACE`, EAR/pose fields are empty
  (`None`), never fabricated.

---

## Integration with the security HUD

Simulation drives the exact same `HudOverlay`. The HUD shows the `SIMULATION
MODE` caption, the standard severity banner, the NO FACE warning during the
`NO_FACE` phase, and the microsleep counter incrementing at the microsleep
event. The alert dispatcher still emits the RED microsleep alert to the
telemetry event logger, exactly as it would in production.

This lets you demonstrate the full operator-coverage workflow (healthy ->
fatigue -> microsleep -> signal loss -> recovery) safely, deterministically and
privacy-preservingly.
