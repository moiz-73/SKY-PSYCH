"""Tests for src/telemetry/perclos.py.

Verifies the timestamp-based PERCLOS window: interval integration, open/closed
ratios, sample expiry, missing-EAR safety, insufficient-data handling and
threshold configurability.

Owned by: telemetry agent.
"""

import pytest

from src.telemetry.perclos import (
    EAR_THRESHOLD,
    PERCLOS_WINDOW_SECONDS,
    PerclosWindow,
)

OPEN_EAR = 0.30
CLOSED_EAR = 0.05


# ---------------------------------------------------------------------------
# Core ratio behaviour
# ---------------------------------------------------------------------------
def test_closed_3s_in_30s_window_is_approximately_10_percent():
    pw = PerclosWindow(window_seconds=30.0, ear_threshold=0.22)
    for t in range(0, 27):          # open for 27 s (t=0..26)
        pw.update(OPEN_EAR, float(t))
    pw.update(CLOSED_EAR, 27.0)     # eye closes at t=27
    pw.update(CLOSED_EAR, 30.0)     # still closed at t=30
    # closed interval [27, 30] = 3 s of 30 s total
    assert pw.value() == pytest.approx(10.0, abs=0.5)


def test_open_entire_window_is_0_percent():
    pw = PerclosWindow()
    for t in range(0, 31, 5):
        pw.update(OPEN_EAR, float(t))
    assert pw.value() == pytest.approx(0.0)


def test_t_now_extends_last_interval():
    pw = PerclosWindow(window_seconds=30.0)
    pw.update(OPEN_EAR, 0.0)
    pw.update(CLOSED_EAR, 5.0)
    # open [0,5], closed [5,10] -> 50%
    assert pw.value(t_now=10.0) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Window expiry
# ---------------------------------------------------------------------------
def test_old_samples_expire_after_window():
    pw = PerclosWindow(window_seconds=30.0)
    for t in range(0, 6):           # closed t=0..5
        pw.update(CLOSED_EAR, float(t))
    for t in range(10, 41, 10):     # open t=10..40
        pw.update(OPEN_EAR, float(t))
    # At t=40 the cutoff is 10: every closed sample (t<10) is expired.
    assert pw.value() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Missing-EAR safety
# ---------------------------------------------------------------------------
def test_none_ear_samples_are_skipped():
    pw = PerclosWindow()
    pw.update(OPEN_EAR, 0.0)
    pw.update(CLOSED_EAR, 5.0)
    before = pw.value()

    pw.update(None, 6.0)
    pw.update(None, 7.0)
    assert pw.value() == before
    assert len(pw._samples) == 2    # None updates added nothing


def test_none_ear_does_not_corrupt_subsequent_ratio():
    pw = PerclosWindow()
    pw.update(OPEN_EAR, 0.0)
    pw.update(CLOSED_EAR, 5.0)
    pw.update(CLOSED_EAR, 10.0)
    pw.update(None, 11.0)           # missing landmark between samples
    # closed [5,10] = 5 s of 10 s -> 50%
    assert pw.value() == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Insufficient data / boundaries
# ---------------------------------------------------------------------------
def test_insufficient_data_returns_zero():
    pw = PerclosWindow()
    pw.update(CLOSED_EAR, 0.0)
    assert pw.value() == 0.0
    assert pw.value() is not None


def test_threshold_is_strictly_less_than():
    pw = PerclosWindow(ear_threshold=0.22)
    pw.update(0.22, 0.0)            # exactly at threshold -> not closed
    pw.update(OPEN_EAR, 5.0)
    assert pw.value() == pytest.approx(0.0)


def test_reset_clears_window():
    pw = PerclosWindow()
    pw.update(CLOSED_EAR, 0.0)
    pw.update(CLOSED_EAR, 5.0)
    pw.reset()
    assert pw.value() == 0.0


def test_thresholds_default_to_spec():
    assert PERCLOS_WINDOW_SECONDS == 30.0
    assert EAR_THRESHOLD == 0.22