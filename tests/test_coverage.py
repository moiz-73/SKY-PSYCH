"""Tests for src/vision/occluder.py and HeadDeviationTracker.

Verifies that coverage classification never reports LOCKED when the face is
absent or pose data is unreliable, and that the head-deviation tracker is a
timestamp-based (not frame-count based) rolling fraction.

Owned by: vision agent.
"""

import math

import pytest

from src.telemetry.headpose import HeadDeviationTracker
from src.vision.occluder import classify_coverage, is_pose_valid


# ---------------------------------------------------------------------------
# classify_coverage
# ---------------------------------------------------------------------------
def test_no_face_when_face_present_false():
    assert classify_coverage(False, 0.9, True) == "NO_FACE"
    # Face absence dominates even if everything else looks fine.
    assert classify_coverage(False, 0.0, False) == "NO_FACE"
    assert classify_coverage(False, None, None) == "NO_FACE"


def test_degraded_when_landmark_quality_low():
    assert classify_coverage(True, 0.1, True) == "DEGRADED"
    assert classify_coverage(True, 0.34, True) == "DEGRADED"
    # A missing quality score is treated as degraded, never as normal.
    assert classify_coverage(True, None, True) == "DEGRADED"


def test_degraded_when_pose_invalid():
    assert classify_coverage(True, 0.9, False) == "DEGRADED"


def test_locked_when_all_good():
    assert classify_coverage(True, 0.9, True) == "LOCKED"
    # Quality exactly at the threshold (0.35) is not "below" it -> LOCKED.
    assert classify_coverage(True, 0.35, True) == "LOCKED"


# ---------------------------------------------------------------------------
# is_pose_valid
# ---------------------------------------------------------------------------
def test_pose_valid_rejects_none():
    assert is_pose_valid(None, 0.0, 0.0) is False
    assert is_pose_valid(0.0, None, 0.0) is False
    assert is_pose_valid(0.0, 0.0, None) is False


def test_pose_valid_rejects_nan_and_inf():
    assert is_pose_valid(float("nan"), 0.0, 0.0) is False
    assert is_pose_valid(0.0, float("nan"), 0.0) is False
    assert is_pose_valid(0.0, 0.0, float("inf")) is False


def test_pose_valid_rejects_absurd_angles():
    assert is_pose_valid(91.0, 0.0, 0.0) is False
    assert is_pose_valid(0.0, -91.0, 0.0) is False
    assert is_pose_valid(0.0, 0.0, 180.0) is False


def test_pose_valid_accepts_plausible_angles():
    assert is_pose_valid(0.0, 0.0, 0.0) is True
    assert is_pose_valid(20.0, 25.0, 0.0) is True
    # Exactly 90 degrees is not "greater than 90".
    assert is_pose_valid(90.0, -90.0, 0.0) is True


def test_pose_valid_rejects_non_numeric():
    assert is_pose_valid("garbage", 0.0, 0.0) is False


# ---------------------------------------------------------------------------
# HeadDeviationTracker - continuous forward pose
# ---------------------------------------------------------------------------
def test_tracker_zero_for_continuous_forward():
    tracker = HeadDeviationTracker()
    for i in range(6):
        tracker.update(0.0, 0.0, float(i * 10))
    assert tracker.value() == 0.0


def test_tracker_zero_before_any_sample():
    assert HeadDeviationTracker().value() == 0.0


# ---------------------------------------------------------------------------
# HeadDeviationTracker - continuous head-off
# ---------------------------------------------------------------------------
def test_tracker_one_for_continuous_head_off():
    tracker = HeadDeviationTracker()
    for i in range(6):
        tracker.update(30.0, 0.0, float(i * 10))  # |pitch| > 20 -> HEAD_OFF
    assert tracker.value() == pytest.approx(1.0, abs=0.05)


def test_tracker_head_off_by_yaw():
    tracker = HeadDeviationTracker()
    for i in range(6):
        tracker.update(0.0, 40.0, float(i * 10))  # |yaw| > 25 -> HEAD_OFF
    assert tracker.value() == pytest.approx(1.0, abs=0.05)


def test_tracker_time_based_integration():
    # 10 s off out of a 30 s window -> ~1/3, independent of sample density.
    tracker = HeadDeviationTracker(window_seconds=30.0)
    tracker.update(0.0, 0.0, 0.0)    # forward
    tracker.update(30.0, 0.0, 10.0)  # head off for 10 s
    tracker.update(0.0, 0.0, 20.0)   # forward again
    tracker.update(0.0, 0.0, 30.0)
    assert tracker.value() == pytest.approx(1.0 / 3.0, abs=0.05)


# ---------------------------------------------------------------------------
# HeadDeviationTracker - expiry of old samples
# ---------------------------------------------------------------------------
def test_tracker_expires_old_samples():
    tracker = HeadDeviationTracker(window_seconds=30.0)
    for i in range(5):
        tracker.update(30.0, 0.0, float(i * 10))  # fill window with head-off
    assert tracker.value() == pytest.approx(1.0, abs=0.05)

    # Jump far past the window with a forward pose: old samples must expire.
    tracker.update(0.0, 0.0, 200.0)
    assert tracker.value() < 0.05


def test_tracker_window_rolls_forward():
    tracker = HeadDeviationTracker(window_seconds=30.0)
    for i in range(5):
        tracker.update(30.0, 0.0, float(i * 10))
    # New head-off samples inside a fresh window rebuild the fraction.
    for i in range(5):
        tracker.update(30.0, 0.0, 200.0 + float(i * 10))
    assert tracker.value() == pytest.approx(1.0, abs=0.05)


def test_tracker_skips_none_inputs():
    tracker = HeadDeviationTracker()
    tracker.update(0.0, 0.0, 10.0)
    before = tracker.value()
    # None/NaN pose must NOT be treated as normal (which would corrupt the
    # window) and must not advance it either.
    tracker.update(None, None, 20.0)
    tracker.update(0.0, float("nan"), 30.0)
    assert tracker.value() == before
    # Fresh head-off run inside a new window still builds a ~1.0 fraction.
    for i in range(5):
        tracker.update(30.0, 0.0, 100.0 + float(i * 10))
    assert tracker.value() == pytest.approx(1.0, abs=0.05)


def test_tracker_reset():
    tracker = HeadDeviationTracker()
    for i in range(5):
        tracker.update(30.0, 0.0, float(i * 10))
    assert tracker.value() == pytest.approx(1.0, abs=0.05)
    tracker.reset()
    assert tracker.value() == 0.0
    tracker.update(0.0, 0.0, 10.0)
    assert tracker.value() == 0.0


def test_tracker_custom_limits():
    tracker = HeadDeviationTracker(pitch_limit_deg=40.0, yaw_limit_deg=45.0)
    for i in range(5):
        tracker.update(35.0, 0.0, float(i * 10))  # within custom limits
    assert tracker.value() == 0.0
    for i in range(5):
        tracker.update(0.0, 50.0, 100.0 + float(i * 10))  # beyond yaw limit
    assert tracker.value() == pytest.approx(1.0, abs=0.05)
