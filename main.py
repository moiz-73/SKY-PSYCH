"""SkyPsych AI - MVP CLI entrypoint and full pipeline wiring.

Owned by: integration agent (this goal).

Wires the whole edge pipeline together:

    ingestion -> vision -> ocular telemetry -> head pose -> fusion
    -> alerts -> HUD / headless telemetry export

Usage (all local, no cloud):

    python main.py --source 0                          # live webcam (HUD)
    python main.py --source assets/samples/demo.mp4    # video file (HUD)
    python main.py --source demo.mp4 --headless --output telemetry.csv

Flags:
    --source        required; integer webcam index ("0") or file path
    --config        YAML settings (default config/settings.yaml)
    --headless      disable the OpenCV window; telemetry to file/stdout
    --output        CSV or JSON Lines telemetry file (stdout if omitted
                    in headless mode)
    --show-landmarks draw the MediaPipe face-mesh overlay on the HUD
    --max-frames    stop after N frames (testing)

Privacy guarantees:
    * no cloud / network egress
    * no raw frames, screenshots, or video written by default
    * telemetry output contains only the 15 abstract TelemetryPoint fields
    * when no face is present the system reports NO_FACE / DEGRADED and
      never fabricates a normal reading
"""

import argparse
import csv
import json
import os
import sys
import time

import cv2
import yaml

from src.alerts import AlertDispatcher, AudioAlerter, TelemetryEventLogger
from src.ingestion import VideoSource, preprocess
from src.telemetry.blinks import BlinkTracker
from src.telemetry.ear import EARSmoother, compute_ear
from src.telemetry.fusion import FatigueFusion
from src.telemetry.headpose import HeadDeviationTracker, estimate_head_pose
from src.telemetry.perclos import PerclosWindow
from src.vision.occluder import classify_coverage, is_pose_valid

# The exact telemetry schema shared by CSV and JSON Lines output.
CSV_COLUMNS = [
    "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
    "head_off", "pitch", "yaw", "roll", "fatigue", "severity", "microsleeps",
    "coverage",
]

_NO_FACE = "NO_FACE"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    """Parse the CLI surface required by the MVP runbook."""
    parser = argparse.ArgumentParser(
        prog="skypsych-ai",
        description="SkyPsych AI - edge-native cognitive fatigue telemetry MVP.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Video source: a camera index (e.g. 0) or a video file path. "
             "Not required when --simulate is used.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in camera-free simulation mode using a synthetic fatigue "
             "timeline (no webcam, no MediaPipe face detection).",
    )
    parser.add_argument(
        "--simulate-duration",
        type=float,
        default=45.0,
        help="Total simulated timeline seconds (default: 45.0).",
    )
    parser.add_argument(
        "--demo-loop",
        action="store_true",
        help="Loop the simulated timeline indefinitely (until Q/ESC or "
             "--max-frames).",
    )
    parser.add_argument(
        "--sim-fps",
        type=float,
        default=20.0,
        help="Simulated frames/sec: how fast the timeline advances per "
             "rendered frame in unbounded (GUI) simulation (default: 20.0).",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to the YAML settings file (default: config/settings.yaml).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without the HUD window (headless telemetry mode).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Telemetry output path. .json -> JSON Lines, .csv -> CSV. "
             "In headless mode with no --output, telemetry is printed to stdout.",
    )
    parser.add_argument(
        "--show-landmarks",
        action="store_true",
        help="Draw the face-mesh landmark overlay on the HUD.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Stop after this many frames (useful for testing).",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def load_config(path):
    """Load the YAML settings file safely; never raises.

    Missing or unparseable files produce a warning and an empty dict so the
    pipeline falls back to the modules' safe internal defaults.
    """
    if not path or not os.path.isfile(path):
        print(f"warning: config file {path!r} not found; using safe defaults",
              file=sys.stderr)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001 - config must never crash startup
        print(f"warning: could not parse config {path!r}: {exc}; "
              "using safe defaults", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def _group(config, name):
    """Return the named config group dict, or {} for anything invalid."""
    if not isinstance(config, dict):
        return {}
    group = config.get(name)
    return group if isinstance(group, dict) else {}


def _ear_config(config):
    """Translate settings.yaml 'ear' group to the EARSmoother/BlinkTracker keys."""
    ear = _group(config, "ear")
    return {
        "EAR_THRESHOLD": ear.get("threshold", 0.22),
        "VALID_BLINK_MIN_MS": ear.get("valid_blink_min_ms", 60),
        "VALID_BLINK_MAX_MS": ear.get("valid_blink_max_ms", 500),
        "MICROSLEEP_MIN_MS": ear.get("microsleep_min_ms", 500),
        "BPM_WINDOW_SECONDS": ear.get("bpm_window_seconds", 60.0),
        "AVG_BLINK_SAMPLES": ear.get("avg_blink_samples", 10),
        "ema_alpha": ear.get("ema_alpha", 0.15),
    }


def _fusion_config(config):
    """Translate settings.yaml 'fatigue'/'severity' groups to fusion keys."""
    fatigue = _group(config, "fatigue")
    severity = _group(config, "severity")
    weights = fatigue.get("weights")
    if not isinstance(weights, dict):
        weights = {}
    return {
        "PERCLOS_WEIGHT": weights.get("perclos", 0.35),
        "BLINK_RATE_WEIGHT": weights.get("blink_rate", 0.25),
        "BLINK_DURATION_WEIGHT": weights.get("blink_duration", 0.20),
        "HEAD_DEVIATION_WEIGHT": weights.get("head_deviation", 0.20),
        "MICROSLEEP_PENALTY": fatigue.get("microsleep_penalty", 20.0),
        "CAUTION_THRESHOLD": severity.get("caution_threshold", 40.0),
        "ALERT_THRESHOLD": severity.get("alert_threshold", 70.0),
        "MICROSLEEP_RED_SECONDS": severity.get("microsleep_red_seconds", 3.0),
    }


def resolve_source(raw):
    """Turn the --source string into an int webcam index or a file path."""
    text = str(raw).strip()
    if text.isdigit():
        return int(text)
    return text


# ---------------------------------------------------------------------------
# Telemetry sinks (headless export)
# ---------------------------------------------------------------------------


def _num(value):
    """Round a float for export; None/NaN -> None (never fabricated)."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return round(f, 4)


def _record(point):
    """TelemetryPoint -> the 15-field export dict (rounds floats)."""
    return {
        "t": round(float(point.t), 6),
        "ear_l": _num(point.ear_l),
        "ear_r": _num(point.ear_r),
        "ear_avg": _num(point.ear_avg),
        "perclos": _num(point.perclos),
        "bpm": _num(point.bpm),
        "avg_blink_ms": _num(point.avg_blink_ms),
        "head_off": _num(point.head_off),
        "pitch": _num(point.pitch),
        "yaw": _num(point.yaw),
        "roll": _num(point.roll),
        "fatigue": _num(point.fatigue),
        "severity": str(point.severity),
        "microsleeps": int(point.microsleeps or 0),
        "coverage": str(point.coverage),
    }


class _BaseSink:
    """Common sink surface: write(point) / close() / count."""

    count = 0

    def write(self, point):  # pragma: no cover - abstract
        raise NotImplementedError

    def close(self):  # pragma: no cover - abstract
        raise NotImplementedError


class CsvSink(_BaseSink):
    """CSV telemetry file with the exact 15-column header."""

    def __init__(self, path):
        self._fh = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(CSV_COLUMNS)

    def write(self, point):
        rec = _record(point)
        self._writer.writerow(
            ["" if rec[col] is None else rec[col] for col in CSV_COLUMNS]
        )
        self.count += 1

    def close(self):
        self._fh.close()


class JsonLinesSink(_BaseSink):
    """JSON Lines telemetry file (one 15-field object per line)."""

    def __init__(self, path):
        self._fh = open(path, "w", encoding="utf-8")

    def write(self, point):
        self._fh.write(
            json.dumps(_record(point), ensure_ascii=False,
                       separators=(",", ":"))
            + "\n"
        )
        self.count += 1

    def close(self):
        self._fh.close()


class StdoutSink(_BaseSink):
    """Prints one JSON object per telemetry point to stdout (headless)."""

    def write(self, point):
        print(json.dumps(_record(point), ensure_ascii=False,
                         separators=(",", ":")))
        self.count += 1

    def close(self):
        pass


def make_sink(output_path):
    """Build the export sink for ``--output`` (None -> stdout JSONL)."""
    if output_path is None:
        return StdoutSink()
    ext = os.path.splitext(str(output_path))[1].lower()
    if ext == ".json":
        return JsonLinesSink(output_path)
    return CsvSink(output_path)  # anything else (or no ext) -> CSV


def _draw_sim_caption(frame):
    """Overlay a clearly visible SIMULATION MODE caption on a HUD frame."""
    caption = "SIMULATION MODE - SYNTHETIC TIMELINE (no camera, no MediaPipe)"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.5, 1
    (tw, _th), _ = cv2.getTextSize(caption, font, scale, thickness)
    height = frame.shape[0]
    x = max(0, (frame.shape[1] - tw) // 2)
    # Black strip along the bottom so the caption stays readable over HUD art.
    cv2.rectangle(frame, (0, height - 24), (frame.shape[1], height),
                  (0, 0, 0), -1)
    cv2.putText(frame, caption, (x, height - 8), font, scale,
                (255, 0, 255), thickness, cv2.LINE_AA)


def _run_simulation(args, config):
    """Camera- and MediaPipe-free simulation of the full fatigue timeline.

    Builds the same fusion / alert / HUD / export objects as the real
    pipeline, but feeds ``FatigueFusion`` from a synthetic timeline instead of
    a video source. No webcam, no MediaPipe face detection, and no frames (raw
    or images) are ever written to disk.
    """
    from src.simulation import SimulatedFatigueTimeline, make_sim_frame

    duration = float(args.simulate_duration or 45.0)
    if duration < 1.0:
        duration = 45.0
    sim_fps = float(args.sim_fps or 20.0)
    if sim_fps <= 0:
        sim_fps = 20.0

    # Time advance per rendered frame. In a bounded --max-frames demo the
    # timeline is spread across the whole frame budget so every phase can be
    # observed; otherwise it advances ~in real time (1.0/sim_fps).
    if args.max_frames and args.max_frames >= 1:
        dt = duration / float(args.max_frames)
    else:
        dt = 1.0 / sim_fps

    timeline = SimulatedFatigueTimeline(duration=duration,
                                        loop=bool(args.demo_loop))

    # --- Fusion + alerts ----------------------------------------------------
    fusion = FatigueFusion(_fusion_config(config))
    audio_cfg = _group(config, "audio")
    audio = AudioAlerter(enabled=bool(audio_cfg.get("enabled", False)))
    logging_cfg = _group(config, "logging")
    event_logger = TelemetryEventLogger(
        logging_cfg.get("event_output") if logging_cfg else None
    )
    dispatcher = AlertDispatcher({"logger": event_logger, "audio": audio})

    # --- HUD / export ---------------------------------------------------------
    hud = None
    if not args.headless:
        from src.ui import HudOverlay  # noqa: PLC0415

        hud = HudOverlay(config)

    sink = None
    if args.headless or args.output is not None:
        try:
            sink = make_sink(args.output)
        except OSError as exc:
            print(f"Error: cannot open output file {args.output!r}: {exc}",
                  file=sys.stderr)
            if event_logger is not None:
                event_logger.close()
            return 1

    camera = _group(config, "camera")
    width = int(camera.get("width", 1280))
    height = int(camera.get("height", 720))

    t = 0.0
    frames_done = 0
    gui_fallback = False
    try:
        while True:
            metrics = timeline.metrics_at(t)
            point = fusion.update(metrics, t)
            dispatcher.dispatch(point, t)

            # --- GUI mode ------------------------------------------------------
            if hud is not None:
                frame = make_sim_frame(width, height, t)
                hud.push_ear(point.ear_avg)
                hud.draw(frame, point, dt=dt)
                _draw_sim_caption(frame)
                try:
                    cv2.imshow("SkyPsych AI - SIMULATION MODE", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):  # Q or ESC
                        break
                except cv2.error:
                    # No GUI backend available: degrade to headless once.
                    if not gui_fallback:
                        print(
                            "warning: OpenCV GUI unavailable; continuing "
                            "headless (simulation)",
                            file=sys.stderr,
                        )
                        gui_fallback = True
                    hud = None

            # --- Headless mode --------------------------------------------------
            if sink is not None:
                sink.write(point)

            frames_done += 1
            if args.max_frames is not None and frames_done >= args.max_frames:
                break
            t += dt

        print(
            f"SIMULATION MODE: processed {frames_done} frames"
            + (f", wrote {sink.count} telemetry points -> {args.output}"
               if sink is not None and args.output else ""),
            file=sys.stderr,
        )
        return 0

    except KeyboardInterrupt:
        print("interrupted: stopping cleanly", file=sys.stderr)
        return 0

    finally:
        if sink is not None:
            sink.close()
        if event_logger is not None:
            event_logger.close()
        if not args.headless:
            try:
                cv2.destroyAllWindows()
            except Exception:  # noqa: BLE001 - GUI cleanup is best-effort
                pass


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run(args, config=None):
    """Execute the MVP pipeline; returns a process exit code."""
    if config is None:
        config = load_config(args.config)

    if args.max_frames is not None and args.max_frames < 1:
        print("Error: --max-frames must be a positive integer.",
              file=sys.stderr)
        return 1

    # Camera-free simulation: bypasses MediaPipe detection and ingestion
    # entirely while still exercising the same fusion, alerts, HUD, schema
    # and headless export.
    if args.simulate:
        return _run_simulation(args, config)

    if args.source is None:
        print(
            "Error: the following arguments are required: --source "
            "(unless --simulate is used).",
            file=sys.stderr,
        )
        return 2

    source = resolve_source(args.source)

    sink = None
    source_obj = None
    detector = None
    event_logger = None
    hud = None
    gui_fallback = False
    frames_done = 0

    try:
        # --- MediaPipe detector (lazy import: --help works without it) ----
        try:
            from src.vision.detector import FaceMeshDetector  # noqa: PLC0415
        except ImportError as exc:
            print(
                "Error: MediaPipe is required by the FaceMesh detector but "
                f"could not be imported: {exc}",
                file=sys.stderr,
            )
            return 1
        try:
            detector = FaceMeshDetector(config)
        except Exception as exc:  # noqa: BLE001 - surface init failure clearly
            print(f"Error: failed to initialize MediaPipe FaceMesh: {exc}",
                  file=sys.stderr)
            return 1

        # --- Ingestion ------------------------------------------------------
        source_obj = VideoSource(source, config)
        try:
            source_obj.start()
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        # --- Ocular telemetry + head pose -----------------------------------
        ear_cfg = _ear_config(config)
        ear_smoother = EARSmoother(alpha=ear_cfg.get("ema_alpha", 0.15))
        blink_tracker = BlinkTracker(ear_cfg)
        ear_threshold = float(ear_cfg.get("EAR_THRESHOLD", 0.22))
        perclos_window = PerclosWindow(
            window_seconds=float(
                _group(config, "perclos").get("window_seconds", 30.0)
            ),
            ear_threshold=ear_threshold,
        )
        head_pose_cfg = _group(config, "head_pose")
        head_dev = HeadDeviationTracker(
            window_seconds=float(
                _group(config, "perclos").get("window_seconds", 30.0)
            ),
            pitch_limit_deg=float(head_pose_cfg.get("pitch_limit_deg", 20.0)),
            yaw_limit_deg=float(head_pose_cfg.get("yaw_limit_deg", 25.0)),
        )

        # --- Fusion + alerts -------------------------------------------------
        fusion = FatigueFusion(_fusion_config(config))
        audio_cfg = _group(config, "audio")
        audio = AudioAlerter(enabled=bool(audio_cfg.get("enabled", False)))
        logging_cfg = _group(config, "logging")
        event_logger = TelemetryEventLogger(
            logging_cfg.get("event_output") if logging_cfg else None
        )
        dispatcher = AlertDispatcher(
            {"logger": event_logger, "audio": audio}
        )

        # --- HUD / export -----------------------------------------------------
        if not args.headless:
            from src.ui import HudOverlay  # noqa: PLC0415

            hud = HudOverlay(config)
        # Headless mode without --output prints JSON Lines to stdout; GUI mode
        # with no --output writes nothing.
        if args.headless or args.output is not None:
            try:
                sink = make_sink(args.output)
            except OSError as exc:
                print(f"Error: cannot open output file {args.output!r}: {exc}",
                      file=sys.stderr)
                return 1

        # --- Main loop ---------------------------------------------------------
        while True:
            loop_t0 = time.monotonic()
            frame, ts = source_obj.read()

            if frame is None:
                if isinstance(source, str):
                    # File/URL stream ended (or could not produce frames):
                    # end cleanly, never fabricate a final telemetry point.
                    break
                time.sleep(0.005)  # transient camera miss: stay stable
                continue

            frames_done += 1
            processed = preprocess(frame, config)
            if processed is None:
                continue

            result = detector.detect(processed)

            # --- Face present: full telemetry path -------------------------
            if result.face_present and result.landmarks_px is not None:
                ear_l, ear_r, ear_avg = compute_ear(result.landmarks_px)
                smoothed = ear_smoother.update(ear_avg)
                blink = blink_tracker.update(smoothed, ts)
                perclos_window.update(smoothed, ts)
                width, height = result.frame_size
                pitch, yaw, roll = estimate_head_pose(
                    result.landmarks_px, width, height
                )
                head_dev.update(pitch, yaw, ts)
                pose_valid = is_pose_valid(pitch, yaw, roll)
                coverage = classify_coverage(
                    result.face_present,
                    result.landmark_quality,
                    pose_valid,
                )
            # --- Face absent: explicit NO_FACE, never fabricated data --------
            else:
                ear_l = ear_r = ear_avg = None
                smoothed = None
                blink = blink_tracker.update(None, ts)
                perclos_window.update(None, ts)
                pitch = yaw = roll = None
                head_dev.update(None, None, ts)
                coverage = _NO_FACE

            metrics = {
                "ear_l": ear_l,
                "ear_r": ear_r,
                "ear_avg": smoothed,
                "perclos": perclos_window.value(ts),
                "bpm": blink["bpm"],
                "avg_blink_ms": blink["avg_blink_ms"],
                "head_off": head_dev.value(),
                "pitch": pitch,
                "yaw": yaw,
                "roll": roll,
                "microsleep_count_total": blink["microsleep_count_total"],
                "microsleep_recent_30s": blink["microsleep_recent_30s"],
                "microsleep_recent_3s": blink["microsleep_recent_3s"],
                "coverage": coverage,
            }

            point = fusion.update(metrics, ts)
            dispatcher.dispatch(point, ts)

            # --- GUI mode ----------------------------------------------------
            if hud is not None:
                if args.show_landmarks and result.landmarks_px is not None:
                    from src.ui import draw_landmarks  # noqa: PLC0415

                    draw_landmarks(processed, result.landmarks_px)
                hud.push_ear(smoothed)
                loop_dt = time.monotonic() - loop_t0
                hud.draw(processed, point, dt=loop_dt)
                try:
                    cv2.imshow("SkyPsych AI", processed)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), ord("Q"), 27):  # Q or ESC
                        break
                except cv2.error:
                    # No GUI backend available: degrade to headless once.
                    if not gui_fallback:
                        print(
                            "warning: OpenCV GUI unavailable; continuing "
                            "headless",
                            file=sys.stderr,
                        )
                        gui_fallback = True
                    hud = None

            # --- Headless mode ------------------------------------------------
            if sink is not None:
                sink.write(point)

            if args.max_frames is not None and frames_done >= args.max_frames:
                break

        print(
            f"done: processed {frames_done} frames"
            + (f", wrote {sink.count} telemetry points -> {args.output}"
               if sink is not None and args.output else ""),
            file=sys.stderr,
        )
        return 0

    except KeyboardInterrupt:
        print("interrupted: stopping cleanly", file=sys.stderr)
        return 0

    finally:
        if detector is not None:
            detector.close()
        if source_obj is not None:
            source_obj.release()
        if sink is not None:
            sink.close()
        if event_logger is not None:
            event_logger.close()
        if not args.headless:
            try:
                cv2.destroyAllWindows()
            except Exception:  # noqa: BLE001 - GUI cleanup is best-effort
                pass


def main(argv=None):
    """Entrypoint: parse args and run; propagates the exit code."""
    args = parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
