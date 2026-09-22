"""Tests for src/telemetry/ear.py.

Covers EAR computation from synthetic landmarks, safe handling of missing /
degenerate landmarks, and EMA smoothing semantics.

Owned by: telemetry agent.
"""

import numpy as np
import pytest

from src.telemetry.ear import (
    EARSmoother,
    LEFT_EYE,
    RIGHT_EYE,
    compute_ear,
    eye_aspect_ratio,
)
from tests.fixtures.synthetic_landmarks import (
    make_landmarks_eye_closed,
    make_landmarks_eye_open,
    make_landmarks_left_closed,
)


# ---------------------------------------------------------------------------
# EAR from synthetic landmarks
# ---------------------------------------------------------------------------
def test_open_landmarks_ear_above_020():
    lm = make_landmarks_eye_open()
    ear_l, ear_r, ear_avg = compute_ear(lm)
    assert ear_l > 0.20
    assert ear_r > 0.20
    assert ear_avg > 0.20
    # open fixture is designed for EAR ~0.25-0.33
    assert 0.25 <= ear_avg <= 0.33


def test_closed_landmarks_ear_below_020():
    lm = make_landmarks_eye_closed()
    ear_l, ear_r, ear_avg = compute_ear(lm)
    assert ear_l < 0.20
    assert ear_r < 0.20
    assert ear_avg < 0.20
    # closed fixture is designed for EAR well below 0.15
    assert ear_avg < 0.15


def test_per_eye_indices_match_spec():
    lm = make_landmarks_left_closed()  # left closed, right open
    ear_l, ear_r, ear_avg = compute_ear(lm)
    assert ear_l < 0.20
    assert ear_r > 0.20


def test_eye_aspect_ratio_accepts_list_input():
    lm = make_landmarks_eye_open()
    ear = eye_aspect_ratio(lm.tolist(), LEFT_EYE)
    assert ear is not None and ear > 0.20


# ---------------------------------------------------------------------------
# None / degenerate safety
# ---------------------------------------------------------------------------
def test_compute_ear_none_landmarks():
    assert compute_ear(None) == (None, None, None)


def test_eye_aspect_ratio_none_inputs():
    assert eye_aspect_ratio(None, LEFT_EYE) is None
    assert eye_aspect_ratio(np.zeros((478, 2)), None) is None


def test_degenerate_eye_returns_none_no_divzero():
    # Squash both corners of the left eye onto the same point -> dist(p1,p4)=0
    lm = make_landmarks_eye_open()
    lm[LEFT_EYE[0]] = (100.0, 100.0)
    lm[LEFT_EYE[3]] = (100.0, 100.0)
    assert eye_aspect_ratio(lm, LEFT_EYE) is None
    ear_l, ear_r, ear_avg = compute_ear(lm)
    assert ear_l is None
    assert ear_r > 0.20      # right eye still valid
    assert ear_avg is None   # do not average partial data


def test_missing_landmark_index_returns_none():
    lm = make_landmarks_eye_open()
    lm[LEFT_EYE[1]] = np.nan
    assert eye_aspect_ratio(lm, LEFT_EYE) is None
    assert compute_ear(lm)[0] is None


def test_short_array_returns_none():
    assert eye_aspect_ratio(np.zeros((10, 2)), LEFT_EYE) is None


# ---------------------------------------------------------------------------
# EARSmoother
# ---------------------------------------------------------------------------
def test_smoother_first_value_equals_raw():
    s = EARSmoother(alpha=0.5)
    assert s.update(0.3) == pytest.approx(0.3)


def test_smoother_applies_ema_formula():
    s = EARSmoother(alpha=0.5)
    s.update(0.1)          # seed -> 0.1
    out = s.update(0.3)    # 0.5*0.3 + 0.5*0.1 = 0.2
    assert out == pytest.approx(0.2)
    out2 = s.update(0.0)   # 0.5*0.0 + 0.5*0.2 = 0.1
    assert out2 == pytest.approx(0.1)


def test_smoother_none_passthrough():
    s = EARSmoother(alpha=0.15)
    s.update(0.3)
    assert s.update(None) == pytest.approx(0.3)
    # and still smooths afterwards
    assert s.update(0.2) == pytest.approx(0.15 * 0.2 + 0.85 * 0.3)


def test_smoother_reset():
    s = EARSmoother(alpha=0.5)
    s.update(0.3)
    s.reset()
    assert s.value is None
    # after reset the next raw value seeds directly again
    assert s.update(0.7) == pytest.approx(0.7)
