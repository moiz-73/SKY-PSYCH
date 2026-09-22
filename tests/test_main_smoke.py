"""Smoke tests for the integration layer (main.py) and the UI/HUD.

Owned by: integration agent (this goal).

These tests never require a physical camera:
  * ``--help`` and ``import main`` work without MediaPipe.
  * Headless CSV / JSON telemetry runs are exercised on a tiny synthetic
    video written to a pytest temp dir (MediaPipe must be present, so those
    are skipped in mediapipe-less environments, mirroring test_vision.py).
  * HUD rendering is tested on synthetic frames with a synthetic
    TelemetryPoint (no GUI, no window required).

No frames, screenshots, or image/video files are asserted to be written.
"""

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from main import CsvSink, JsonLinesSink, _record  # noqa: E402
from src.telemetry import TelemetryPoint  # noqa: E402


def _mediapipe_available() -> bool:
    """Whether the FaceMesh detector can be imported in this environment."""
    try:
        import src.vision.detector  # noqa: F401
        return True
    except ImportError:
        return False


_NEEDS_MEDIAPIPE = pytest.mark.skipif(
    not _mediapipe_available(),
    reason="MediaPipe is not installed in this environment",
)


def _run_main(*args, timeout=180):
    """Run main.py as a subprocess from the project root."""
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _make_synthetic_video(path, n=10):
    """Write ``n`` dark 'no face' frames to ``path`` (no camera needed)."""
    import cv2

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        30,
        (320, 240),
    )
    try:
        assert writer.isOpened(), "cv2.VideoWriter could not open temp clip"
        for _ in range(n):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(frame, "no face", (40, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            writer.write(frame)
    finally:
        writer.release()


def _point_factory(t=1.0, **overrides):
    """Build a TelemetryPoint with sane defaults."""
    base = dict(
        t=t,
        ear_l=0.30, ear_r=0.28, ear_avg=0.29,
        perclos=5.0, bpm=18.0, avg_blink_ms=120.0,
        head_off=0.02, pitch=3.0, yaw=-2.0, roll=1.0,
        fatigue=20.0, severity="GREEN", microsleeps=0, coverage="LOCKED",
    )
    base.update(overrides)
    return TelemetryPoint(**base)


# ---------------------------------------------------------------------------
# CLI: --help (works even without MediaPipe)
# ---------------------------------------------------------------------------


def test_help_exits_zero_and_documents_flags():
    result = _run_main("--help")
    assert result.returncode == 0
    out = result.stdout
    for flag in ("--source", "--config", "--headless", "--output",
                 "--show-landmarks", "--max-frames"):
        assert flag in out


def test_import_main_module_cleanly():
    # import main must succeed without MediaPipe (detector is lazy).
    import main  # noqa: F401


def test_source_is_required():
    result = _run_main()
    assert result.returncode != 0
    assert "--source" in (result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# CLI: error handling (needs MediaPipe to reach the camera path)
# ---------------------------------------------------------------------------


@_NEEDS_MEDIAPIPE
def test_missing_file_prints_clear_error_and_exits_nonzero(tmp_path):
    out = tmp_path / "out.csv"
    result = _run_main(
        "--source", "definitely_missing_clip.mp4",
        "--headless", "--max-frames", "5", "--output", str(out),
    )
    assert result.returncode != 0
    assert "Error" in (result.stdout + result.stderr)
    assert "Could not open video source" in (result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# CLI: headless telemetry export
# ---------------------------------------------------------------------------


@_NEEDS_MEDIAPIPE
def test_headless_csv_output_writes_exact_schema(tmp_path):
    video = tmp_path / "clip.avi"
    out = tmp_path / "telemetry.csv"
    _make_synthetic_video(video)

    result = _run_main(
        "--source", str(video), "--headless", "--max-frames", "5",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()

    rows = list(csv.reader(out.read_text().splitlines()))
    assert rows, "CSV should have at least a header"
    header = rows[0]
    expected_header = [
        "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
        "head_off", "pitch", "yaw", "roll", "fatigue", "severity",
        "microsleeps", "coverage",
    ]
    assert header == expected_header
    assert len(rows) == 1 + 5  # header + 5 rows

    # No face on a synthetic clip -> NO_FACE coverage, never a false-normal
    # GREEN. Fusion forces YELLOW on NO_FACE with no prior state.
    for row in rows[1:]:
        record = dict(zip(expected_header, row))
        assert record["coverage"] == "NO_FACE"
        assert record["severity"] == "YELLOW"
        # ear / pose never fabricated
        assert record["ear_avg"] == ""
        assert record["pitch"] == ""


@_NEEDS_MEDIAPIPE
def test_headless_json_output_writes_json_lines(tmp_path):
    video = tmp_path / "clip.avi"
    out = tmp_path / "telemetry.json"
    _make_synthetic_video(video)

    result = _run_main(
        "--source", str(video), "--headless", "--max-frames", "5",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()

    lines = out.read_text().splitlines()
    assert len(lines) == 5
    expected_keys = {
        "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
        "head_off", "pitch", "yaw", "roll", "fatigue", "severity",
        "microsleeps", "coverage",
    }
    for line in lines:
        record = json.loads(line)
        assert set(record.keys()) == expected_keys
        assert record["coverage"] == "NO_FACE"
        assert record["severity"] == "YELLOW"
        assert record["ear_l"] is None
        assert record["pitch"] is None


@_NEEDS_MEDIAPIPE
def test_headless_no_raw_frame_files_written(tmp_path):
    video = tmp_path / "clip.avi"
    out = tmp_path / "telemetry.csv"
    _make_synthetic_video(video)

    result = _run_main(
        "--source", str(video), "--headless", "--max-frames", "5",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr

    # Only the source video + the telemetry CSV may exist; no screenshots,
    # extracted frames, or video output may be created by default.
    artifacts = [
        p for p in tmp_path.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".avi",
                                ".mp4", ".mjpg", ".webp")
        and p.name != video.name
    ]
    assert artifacts == [], f"unexpected raw frame/image artifacts: {artifacts}"


# ---------------------------------------------------------------------------
# UI: HUD rendering (no GUI, no MediaPipe required) + telemetry sinks
# ---------------------------------------------------------------------------


def test_hud_renders_lock_green_frame():
    from src.ui import HudOverlay

    hud = HudOverlay()
    points = [
        _point_factory(t=1.0, fatigue=20.0, severity="GREEN", coverage="LOCKED"),
        _point_factory(t=1.0, fatigue=55.0, severity="YELLOW", coverage="DIRTY"),
        _point_factory(t=1.0, fatigue=90.0, severity="RED", coverage="LOCKED"),
        _point_factory(t=1.0, fatigue=20.0, severity="GREEN", coverage="LOCKED"),
    ]
    for point in points:
        hud.reset()
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        out = hud.draw(frame, point, dt=0.033)  # must not raise
        assert out.shape == (720, 1280, 3)
        assert np.any(out != 0), "HUD should draw something on a black frame"


def test_hud_no_face_shows_red_warning():
    from src.ui import HudOverlay

    hud = HudOverlay()
    point = _point_factory(
        t=1.0, ear_l=None, ear_r=None, ear_avg=None, perclos=0.0, bpm=0.0,
        avg_blink_ms=0.0, head_off=0.0, pitch=None, yaw=None, roll=None,
        fatigue=90.0, severity="YELLOW", microsleeps=0, coverage="NO_FACE",
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    out = hud.draw(frame, point, dt=0.033)

    # The large "NO FACE" warning is drawn in RED (B-dominant in BGR).
    # Anti-aliased text over black blends toward the background, so use a
    # permissive red-dominance mask.
    b, g, r = out[:, :, 0], out[:, :, 1], out[:, :, 2]
    red_pixels = np.sum((b > 100) & (g < 140) & (r < 150))
    assert red_pixels > 0, "NO FACE warning should be drawn in red"


def test_hud_degraded_shows_warning():
    from src.ui import HudOverlay

    hud = HudOverlay()
    point = _point_factory(
        fatigue=30.0, severity="GREEN", coverage="DEGRADED",
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    out = hud.draw(frame, point, dt=0.033)
    # DEGRADED shows an amber (G-dominant BGR) warning, never a green banner.
    b, g, r = out[:, :, 0], out[:, :, 1], out[:, :, 2]
    amber_pixels = np.sum((g > 140) & (r > 180) & (b < 90))
    assert amber_pixels > 0, "DEGRADED warning should be drawn in amber"


def test_hud_green_state_draws_green_banner():
    from src.ui import HudOverlay

    hud = HudOverlay()
    point = _point_factory(fatigue=20.0, severity="GREEN", coverage="LOCKED")
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    out = hud.draw(frame, point, dt=0.033)
    b, g, r = out[:, :, 0], out[:, :, 1], out[:, :, 2]
    green_pixels = np.sum((g > 150) & (r < 110) & (b < 110))
    assert green_pixels > 0, "GREEN severity banner should be drawn in green"


def test_hud_handles_all_none_fields_without_crash():
    from src.ui import HudOverlay

    hud = HudOverlay()
    # Repeated renders of a no-face point must be stable (loop stability).
    for _ in range(5):
        point = _point_factory(
            t=1.0, ear_l=None, ear_r=None, ear_avg=None, perclos=None,
            bpm=None, avg_blink_ms=None, head_off=None, pitch=None,
            yaw=None, roll=None, fatigue=None, severity="RED",
            microsleeps=0, coverage="NO_FACE",
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hud.draw(frame, point, dt=0.033)


def test_performance_governor_degrades_waveform_then_minimal():
    from src.ui.osd import PerformanceGovernor

    g = PerformanceGovernor(target_fps=25.0, degrade_after_s=3.0,
                            minimal_after_s=8.0)
    t0 = time.monotonic()
    assert g.update(10.0, t=t0) == "full"
    assert g.update(10.0, t=t0 + 3.0) == "no_waveform"
    assert g.update(10.0, t=t0 + 8.0) == "minimal"
    # Recovery is immediate once FPS is back up.
    assert g.update(30.0, t=t0 + 9.0) == "full"


def test_ear_waveform_skips_none_and_fps_estimator():
    from src.ui.osd import EarWaveform, FpsEstimator

    w = EarWaveform(capacity=10)
    w.push(0.3)
    w.push(None)  # must be skipped, never plotted
    w.push(0.2)
    assert w.values() == [0.3, 0.2]

    f = FpsEstimator()
    f.update(0.1)  # 10 fps
    f.update(0.033)  # ~30 fps
    assert 10 <= f.fps <= 30


# ---------------------------------------------------------------------------
# Telemetry sinks (in-process, no subprocess, no MediaPipe)
# ---------------------------------------------------------------------------


def test_csv_sink_writes_header_and_rounded_values(tmp_path):
    out = tmp_path / "t.csv"
    sink = CsvSink(str(out))
    sink.write(_point_factory(t=1.23456789, ear_l=0.301234, fatigue=25.6789))
    sink.write(_point_factory(
        t=2.0, ear_l=None, ear_r=None, ear_avg=None,
        pitch=None, yaw=None, roll=None,
        severity="YELLOW", coverage="NO_FACE",
    ))
    sink.close()
    rows = list(csv.reader(out.read_text().splitlines()))
    assert rows[0][0] == "t"
    # rounded to 4 decimals
    assert rows[1][rows[0].index("ear_l")] == "0.3012"
    # NO_FACE row has empty ear/pitch cells (non-fabricated)
    assert rows[2][rows[0].index("ear_l")] == ""
    assert rows[2][rows[0].index("pitch")] == ""


def test_json_sink_writes_json_lines(tmp_path):
    out = tmp_path / "t.json"
    sink = JsonLinesSink(str(out))
    sink.write(_point_factory(t=1.0, coverage="NO_FACE", severity="YELLOW"))
    sink.close()
    records = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["coverage"] == "NO_FACE"
    assert "frame" not in records[0] and "landmark" not in records[0]


def test_record_never_contains_frame_or_landmark_fields():
    point = _point_factory()
    rec = _record(point)
    assert set(rec.keys()) == {
        "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
        "head_off", "pitch", "yaw", "roll", "fatigue", "severity",
        "microsleeps", "coverage",
    }
    lowered = " ".join(rec.keys()).lower()
    for banned in ("frame", "image", "landmark", "path", "face"):
        assert banned not in lowered