"""Tests for the camera-free simulation mode (src/simulation.py + main.py).

Owned by: integration agent (this goal).

The simulation timeline is fed through the REAL ``FatigueFusion`` so the
severity transition sequence is verified end-to-end without a webcam and
without MediaPipe:

    GREEN -> YELLOW -> RED -> RED(forced by microsleep) -> NO_FACE (never
    GREEN) -> recovery to GREEN/YELLOW (non-RED).

None of these tests require MediaPipe or a camera. The subprocess tests
exercise ``main.py --simulate --headless`` and verify the exact 15-column CSV
schema plus a NO_FACE row, mirroring tests/test_main_smoke.py.
"""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import (  # noqa: E402
    PHASE_LABELS,
    PHASE_SEVERITY,
    SimulatedFatigueTimeline,
    make_sim_frame,
)
from src.telemetry.fusion import FatigueFusion  # noqa: E402


def _run_main(*args, timeout=180):
    """Run main.py as a subprocess from the project root."""
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _ordered_subsequence(seq, sub):
    """True when the elements of ``sub`` appear in ``seq`` in order."""
    it = iter(seq)
    return all(any(x == y for y in it) for x in sub)


# ---------------------------------------------------------------------------
# Timeline + fusion: severity transition sequence (no camera, no MediaPipe)
# ---------------------------------------------------------------------------


def test_timeline_produces_required_phase_labels():
    tl = SimulatedFatigueTimeline()
    observed = [tl.phase_at(t) for t in (0, 5, 15, 23, 28, 33, 42)]
    assert observed == ["GREEN", "GREEN", "YELLOW", "RED", "MICROSLEEP",
                        "NO_FACE", "RECOVERY"]
    # PHASE_LABELS cover [0, 45) without gaps or overlaps.
    expected = {"GREEN", "YELLOW", "RED", "MICROSLEEP", "NO_FACE", "RECOVERY"}
    assert set(PHASE_LABELS) == expected


def test_timeline_through_fusion_shows_full_severity_sequence():
    tl = SimulatedFatigueTimeline()
    fusion = FatigueFusion()

    history = []
    t = 0.0
    while t <= 45.0:
        point = fusion.update(tl.metrics_at(t), t)
        history.append((t, point.severity, point.coverage, point.microsleeps,
                        point.microsleep_recent_3s))
        t += 0.5

    severities = [s for _, s, _, _, _ in history]

    # 1. GREEN appears first (healthy low-fatigue start).
    assert severities[0] == "GREEN"
    # 2. Then YELLOW, then a non-microsleep RED, in order.
    assert _ordered_subsequence(severities, ["GREEN", "YELLOW", "RED"])
    # 3. A RED forced by microsleep_recent_3s appears, with the counter set.
    ms_rows = [h for h in history if h[4] is True]
    assert ms_rows, "expected a microsleep-forced RED window"
    assert any(r[3] == 1 for r in ms_rows)
    # 4. The microsleep counter increments 0 -> 1.
    assert 0 in [r[3] for r in history] and 1 in [r[3] for r in history]
    # 5. NO_FACE appears and is NEVER GREEN.
    nf_rows = [h for h in history if h[2] == "NO_FACE"]
    assert nf_rows, "expected NO_FACE coverage"
    assert all(s != "GREEN" for _, s, _, _, _ in nf_rows)
    # 6. Final window recovers to GREEN or YELLOW (non-RED).
    final = [h for h in history if h[0] >= 40.0]
    assert final and all(s in ("GREEN", "YELLOW") for _, s, _, _, _ in final)


def test_microsleep_forces_red_and_increments_count():
    tl = SimulatedFatigueTimeline()
    fusion = FatigueFusion()

    before = fusion.update(tl.metrics_at(21.0), 21.0)
    assert before.severity == "RED" and before.microsleeps == 0
    assert before.microsleep_recent_3s is False

    during = fusion.update(tl.metrics_at(28.0), 28.0)
    assert during.severity == "RED"          # forced even though FI could vary
    assert during.microsleep_recent_3s is True
    assert during.microsleeps == 1
    assert during.coverage == "LOCKED"


def test_no_face_never_green_through_fusion():
    tl = SimulatedFatigueTimeline()
    fusion = FatigueFusion()
    for t in (30.0, 32.0, 34.0, 35.0, 35.9):
        point = fusion.update(tl.metrics_at(t), t)
        assert point.coverage == "NO_FACE"
        assert point.severity != "GREEN"
        # ear / pose never fabricated while the face is absent.
        assert point.ear_avg is None and point.pitch is None


def test_recovery_returns_to_non_red():
    tl = SimulatedFatigueTimeline()
    fusion = FatigueFusion()
    # Drive the whole timeline first so fusion state is real, then recover.
    for t in (0.0, 20.0, 28.0, 33.0):
        fusion.update(tl.metrics_at(t), t)
    end = fusion.update(tl.metrics_at(44.0), 44.0)
    assert end.severity in ("GREEN", "YELLOW")
    assert end.severity != "RED"
    assert end.coverage == "LOCKED"


def test_demo_loop_wraps_timeline():
    tl = SimulatedFatigueTimeline(loop=True)
    assert tl.metrics_at(45.0)["coverage"] == "LOCKED"  # wraps to t==0
    assert tl.phase_at(45.0) == "GREEN"
    assert tl.metrics_at(46.0)["coverage"] == "LOCKED"
    assert tl.normalize(45.0) == 0.0


def test_make_sim_frame_renders_bgr_uint8_no_text():
    frame = make_sim_frame(320, 240, 2.0)
    assert frame.shape == (240, 320, 3)
    assert frame.dtype.name == "uint8"
    # Dark synthetic base; the drifting shapes vary with t.
    import numpy as np

    assert int(np.mean(frame)) < 80
    other = make_sim_frame(320, 240, 2.0 + 0.05)
    assert not np.array_equal(frame, other)


# ---------------------------------------------------------------------------
# No MediaPipe required
# ---------------------------------------------------------------------------


def test_simulation_imports_and_runs_without_mediapipe():
    """The timeline + frame generator must work with mediapipe import blocked."""
    code = (
        "import sys, builtins\n"
        "real = builtins.__import__\n"
        "def _blocked(name, *a, **k):\n"
        "    if name == 'mediapipe' or name.startswith('mediapipe.'):\n"
        "        raise ImportError('mediapipe blocked for this test')\n"
        "    return real(name, *a, **k)\n"
        "builtins.__import__ = _blocked\n"
        "from src.simulation import SimulatedFatigueTimeline, make_sim_frame\n"
        "tl = SimulatedFatigueTimeline()\n"
        "assert tl.metrics_at(5.0)['coverage'] == 'LOCKED'\n"
        "assert tl.metrics_at(32.0)['coverage'] == 'NO_FACE'\n"
        "frame = make_sim_frame(320, 240, 1.0)\n"
        "assert frame.shape == (240, 320, 3)\n"
        "print('SIM_OK_NO_MEDIAPIPE')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "SIM_OK_NO_MEDIAPIPE" in result.stdout


# ---------------------------------------------------------------------------
# Headless simulation end-to-end (subprocess)
# ---------------------------------------------------------------------------


def test_simulate_headless_writes_exact_schema_with_no_face(tmp_path):
    out = tmp_path / "telemetry_sim.csv"
    result = _run_main(
        "--simulate", "--headless", "--max-frames", "300",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()

    rows = list(csv.reader(out.read_text().splitlines()))
    assert rows, "CSV should have at least a header"
    expected_header = [
        "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
        "head_off", "pitch", "yaw", "roll", "fatigue", "severity",
        "microsleeps", "coverage",
    ]
    assert rows[0] == expected_header
    assert len(rows) == 1 + 300  # header + 300 frames

    records = [dict(zip(expected_header, row)) for row in rows[1:]]
    severities = {r["severity"] for r in records}
    assert severities == {"GREEN", "YELLOW", "RED"}

    # Microsleep counter increments at least once, NO_FACE rows exist, and
    # NO_FACE rows are never GREEN with never-fabricated ear/pitch.
    assert any(int(r["microsleeps"] or 0) >= 1 for r in records)
    nf_rows = [r for r in records if r["coverage"] == "NO_FACE"]
    assert nf_rows, "expected NO_FACE rows in the simulated run"
    assert all(r["severity"] != "GREEN" for r in nf_rows)
    assert all(r["ear_avg"] == "" and r["pitch"] == "" for r in nf_rows)

    # Recovery returns to a non-RED state at the end of the timeline.
    tail = [r for r in records if float(r["t"]) >= 40.0]
    assert tail and all(r["severity"] in ("GREEN", "YELLOW") for r in tail)


def test_simulate_help_and_integration_flags():
    result = _run_main("--simulate", "--headless", "--max-frames", "5")
    assert result.returncode == 0, result.stderr
    # The summary line is emitted on stderr.
    assert "SIMULATION MODE" in result.stderr


def test_simulate_json_lines_output(tmp_path):
    out = tmp_path / "telemetry_sim.json"
    result = _run_main(
        "--simulate", "--headless", "--max-frames", "10",
        "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    lines = out.read_text().splitlines()
    assert len(lines) == 10
    expected_keys = {
        "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
        "head_off", "pitch", "yaw", "roll", "fatigue", "severity",
        "microsleeps", "coverage",
    }
    import json

    for line in lines:
        assert set(json.loads(line).keys()) == expected_keys
