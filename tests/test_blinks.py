"""Tests for src/telemetry/blinks.py.

Exercises the deterministic BlinkTracker state machine: open/closed
transitions, blink vs microsleep classification, noise rejection, blink-rate
(bpm), average blink duration, microsleep recency flags, missing-EAR safety
and threshold configurability.

Owned by: telemetry agent.
"""

import pytest

from src.telemetry.blinks import (
    BlinkTracker,
    EAR_THRESHOLD,
    MICROSLEEP_MIN_MS,
    VALID_BLINK_MAX_MS,
    VALID_BLINK_MIN_MS,
)

OPEN_EAR = 0.30
CLOSED_EAR = 0.05


def _closed(tr, t, ear=CLOSED_EAR):
    """Feed a below-threshold EAR (eye closing / staying closed)."""
    return tr.update(ear, t)


def _open(tr, t, ear=OPEN_EAR):
    """Feed an above-threshold EAR (eye opening / staying open)."""
    return tr.update(ear, t)


# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------
def test_100ms_closure_produces_one_valid_blink():
    tr = BlinkTracker()
    _open(tr, 0.000)
    _closed(tr, 0.033)
    out = _open(tr, 0.133)  # duration = 100 ms

    assert out["blink_completed"] is True
    assert out["microsleep_completed"] is False
    assert out["blink_duration_ms"] == pytest.approx(100.0, abs=0.5)
    assert out["valid_blink_count_total"] == 1
    assert out["microsleep_count_total"] == 0


def test_600ms_closure_produces_one_microsleep():
    tr = BlinkTracker()
    _open(tr, 0.0)
    _closed(tr, 0.1)
    out = _open(tr, 0.7)  # duration = 600 ms

    assert out["microsleep_completed"] is True
    assert out["blink_completed"] is False
    assert out["microsleep_count_total"] == 1
    assert out["valid_blink_count_total"] == 0


def test_20ms_closure_is_ignored_as_noise():
    tr = BlinkTracker()
    _open(tr, 0.0)
    _closed(tr, 0.1)
    out = _open(tr, 0.12)  # duration = 20 ms

    assert out["blink_completed"] is False
    assert out["microsleep_completed"] is False
    assert tr.valid_blink_count_total == 0
    assert tr.microsleep_count_total == 0


def test_closure_active_expected_windows():
    tr = BlinkTracker()
    _open(tr, 0.0)
    assert tr.update(CLOSED_EAR, 0.1)["closure_active"] is True
    assert tr.update(CLOSED_EAR, 0.2)["closure_active"] is True
    assert _open(tr, 0.3)["closure_active"] is False


# ---------------------------------------------------------------------------
# Blink rate (bpm) and average duration
# ---------------------------------------------------------------------------
def test_bpm_increases_after_valid_blinks():
    tr = BlinkTracker()
    _open(tr, 0.0)
    _closed(tr, 0.1)
    out1 = _open(tr, 0.2)   # blink 1
    assert out1["bpm"] == pytest.approx(1.0)

    _closed(tr, 0.3)
    out2 = _open(tr, 0.4)   # blink 2
    assert out2["bpm"] == pytest.approx(2.0)
    assert out2["bpm"] > out1["bpm"]


def test_average_blink_duration_recent_blinks():
    tr = BlinkTracker()
    _open(tr, 0.0)
    _closed(tr, 0.1)
    _open(tr, 0.2)          # 100 ms
    _closed(tr, 0.5)
    out = _open(tr, 0.7)    # 200 ms
    assert out["avg_blink_ms"] == pytest.approx(150.0)


def test_bpm_expires_after_60_seconds():
    tr = BlinkTracker()
    _open(tr, 0.0)
    _closed(tr, 0.1)
    _open(tr, 0.2)          # one blink at ~0.2 s
    out = _open(tr, 60.5)   # >60 s later
    assert out["bpm"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Microsleep recency flags
# ---------------------------------------------------------------------------
def test_microsleep_recent_3s_true_then_false():
    tr = BlinkTracker()
    _open(tr, 0.0)
    _closed(tr, 0.1)
    out = _open(tr, 0.7)         # microsleep ends at t=0.7
    assert out["microsleep_recent_3s"] is True
    assert out["microsleep_recent_30s"] is True

    out2 = _open(tr, 3.8)        # 3.1 s after end
    assert out2["microsleep_recent_3s"] is False
    assert out2["microsleep_recent_30s"] is True

    out3 = _open(tr, 31.0)       # 30.3 s after end
    assert out3["microsleep_recent_30s"] is False


# ---------------------------------------------------------------------------
# Missing-EAR safety
# ---------------------------------------------------------------------------
def test_none_ear_does_not_mutate_state():
    tr = BlinkTracker()
    _open(tr, 1.0)
    _closed(tr, 1.1)

    out_none = tr.update(None, 1.2)
    assert out_none["closure_active"] is False
    assert out_none["blink_completed"] is False
    assert out_none["microsleep_completed"] is False
    assert out_none["valid_blink_count_total"] == 0

    # The open->closed->open event [1.1, 1.3] is still intact (200 ms blink).
    out = _open(tr, 1.3)
    assert out["blink_completed"] is True
    assert out["blink_duration_ms"] == pytest.approx(200.0, abs=0.5)


def test_none_ear_returns_safe_defaults_when_idle():
    tr = BlinkTracker()
    out = tr.update(None, 0.0)
    assert out["closure_active"] is False
    assert out["bpm"] == 0.0
    assert out["avg_blink_ms"] == 0.0
    assert out["microsleep_recent_3s"] is False
    assert out["microsleep_recent_30s"] is False


# ---------------------------------------------------------------------------
# Configurability
# ---------------------------------------------------------------------------
def test_thresholds_configurable():
    tr = BlinkTracker({"EAR_THRESHOLD": 0.28})
    out = tr.update(0.25, 0.0)   # 0.25 < 0.28 -> closed immediately
    assert out["closure_active"] is True


def test_thresholds_default_to_spec():
    assert EAR_THRESHOLD == 0.22
    assert VALID_BLINK_MIN_MS == 60
    assert VALID_BLINK_MAX_MS == 500
    assert MICROSLEEP_MIN_MS == 500