"""Tests for src/telemetry/fusion.py.

Verifies the weighted Fatigue Index formula, normalization rules, severity
classification, microsleep-forced RED, FI clamping, and the NO_FACE guard that
prevents a false-normal GREEN. Also checks the shared TelemetryPoint contract
is produced correctly.

Owned by: telemetry agent.
"""

import pytest

from src.telemetry.fusion import (
    FatigueFusion,
    PERCLOS_WEIGHT,
    BLINK_RATE_WEIGHT,
    BLINK_DURATION_WEIGHT,
    HEAD_DEVIATION_WEIGHT,
    MICROSLEEP_PENALTY,
    CAUTION_THRESHOLD,
    ALERT_THRESHOLD,
    MICROSLEEP_RED_SECONDS,
    NO_FACE_GRACE_SECONDS,
    _bpr_norm,
    _perclos_norm,
)


def _healthy(t=0.0, coverage="LOCKED"):
    """A low-fatigue, LOCKED metrics dict."""
    return {
        "ear_l": 0.31, "ear_r": 0.30, "ear_avg": 0.305,
        "perclos": 5.0,
        "bpm": 20.0,
        "avg_blink_ms": 100.0,
        "head_off": 0.05,
        "pitch": 0.0, "yaw": 0.0, "roll": 0.0,
        "microsleep_count_total": 0,
        "microsleep_recent_30s": False,
        "microsleep_recent_3s": False,
        "coverage": coverage,
    }


# ---------------------------------------------------------------------------
# Defaults / normalization helpers
# ---------------------------------------------------------------------------
def test_default_thresholds_match_spec():
    assert PERCLOS_WEIGHT == 0.35
    assert BLINK_RATE_WEIGHT == 0.25
    assert BLINK_DURATION_WEIGHT == 0.20
    assert HEAD_DEVIATION_WEIGHT == 0.20
    assert MICROSLEEP_PENALTY == 20.0
    assert CAUTION_THRESHOLD == 40.0
    assert ALERT_THRESHOLD == 70.0
    assert MICROSLEEP_RED_SECONDS == 3.0
    assert NO_FACE_GRACE_SECONDS == 5.0


def test_bpr_norm_rules():
    assert _bpr_norm(0.0) == pytest.approx(100.0)
    assert _bpr_norm(5.0) == pytest.approx(100.0 * (15.0 - 5.0) / 15.0)
    assert _bpr_norm(15.0) == pytest.approx(0.0)
    assert _bpr_norm(20.0) == pytest.approx(0.0)   # healthy band
    assert _bpr_norm(30.0) == pytest.approx(0.0)
    assert _bpr_norm(40.0) == pytest.approx(50.0)  # above 30 -> 50


def test_perclos_norm_rule():
    assert _perclos_norm(5.0) == pytest.approx(25.0)
    assert _perclos_norm(20.0) == pytest.approx(100.0)
    assert _perclos_norm(50.0) == pytest.approx(100.0)  # capped at 1.0


# ---------------------------------------------------------------------------
# Healthy -> GREEN
# ---------------------------------------------------------------------------
def test_healthy_signals_produce_green():
    f = FatigueFusion()
    tp = f.update(_healthy(t=0.0), 0.0)
    assert tp.severity == "GREEN"
    assert 0.0 <= tp.fatigue < CAUTION_THRESHOLD
    # FI = 0.35*25 + 0.25*0 + 0.20*5 + 0.20*5 = 10.75
    assert tp.fatigue == pytest.approx(10.75, abs=1e-6)
    assert tp.coverage == "LOCKED"
    assert tp.microsleeps == 0
    assert tp.microsleep_recent_3s is False
    assert tp.microsleep_recent_30s is False


def test_update_returns_valid_telemetry_point():
    f = FatigueFusion()
    tp = f.update(_healthy(t=1.0), 1.0)
    assert tp.t == 1.0
    assert tp.ear_avg == pytest.approx(0.305)
    assert tp.perclos == pytest.approx(5.0)
    assert tp.head_off == pytest.approx(0.05)
    # severity is one of the contract types
    assert tp.severity in ("GREEN", "YELLOW", "RED")
    assert tp.coverage in ("LOCKED", "DEGRADED", "NO_FACE")


# ---------------------------------------------------------------------------
# PERCLOS 20 with moderate abnormalities -> YELLOW
# ---------------------------------------------------------------------------
def test_perclos_20_moderate_abnormalities_is_yellow():
    f = FatigueFusion()
    tp = f.update(
        {
            "perclos": 20.0,       # PERCLOS_norm = 100
            "bpm": 5.0,            # BPR_norm   = 100 * 10/15 = 66.67
            "avg_blink_ms": 150.0,  # ABD_norm   = 30
            "head_off": 0.3,       # HDD_norm   = 30
            "microsleep_count_total": 0,
            "microsleep_recent_30s": False,
            "microsleep_recent_3s": False,
            "coverage": "LOCKED",
        },
        0.0,
    )
    # FI = 35 + 16.67 + 6 + 6 = 63.67 -> YELLOW (40 <= FI < 70)
    assert CAUTION_THRESHOLD <= tp.fatigue < ALERT_THRESHOLD
    assert tp.severity == "YELLOW"


def test_high_abnormalities_produce_red():
    f = FatigueFusion()
    tp = f.update(
        {
            "perclos": 20.0,
            "bpm": 0.0,            # BPR_norm = 100
            "avg_blink_ms": 200.0,  # ABD_norm = 55
            "head_off": 0.5,       # HDD_norm = 50
            "microsleep_count_total": 0,
            "microsleep_recent_30s": False,
            "microsleep_recent_3s": False,
            "coverage": "LOCKED",
        },
        0.0,
    )
    # FI = 35 + 25 + 11 + 10 = 81 -> RED
    assert tp.fatigue >= ALERT_THRESHOLD
    assert tp.severity == "RED"


# ---------------------------------------------------------------------------
# FI >= 70 -> RED, no microsleep
# ---------------------------------------------------------------------------
def test_fi_above_alert_threshold_is_red():
    f = FatigueFusion()
    tp = f.update(
        {
            "perclos": 20.0,       # 100
            "bpm": 0.0,            # 100
            "avg_blink_ms": 290.0,  # clamp((200)/200)=100
            "head_off": 0.5,       # 50
            "microsleep_count_total": 0,
            "microsleep_recent_30s": False,
            "microsleep_recent_3s": False,
            "coverage": "LOCKED",
        },
        0.0,
    )
    # FI = 35 + 25 + 20 + 10 = 90 -> RED
    assert tp.fatigue >= ALERT_THRESHOLD
    assert tp.severity == "RED"


# ---------------------------------------------------------------------------
# Microsleep forces RED
# ---------------------------------------------------------------------------
def test_recent_3s_microsleep_forces_red_even_when_fi_low():
    f = FatigueFusion()
    m = _healthy()
    m["microsleep_recent_30s"] = True
    m["microsleep_recent_3s"] = True
    m["microsleep_count_total"] = 1
    tp = f.update(m, 0.0)
    # FI would be 10.75 + 20 = 30.75 (GREEN zone) but the recent microsleep
    # must force RED regardless of the computed index.
    assert tp.fatigue < CAUTION_THRESHOLD
    assert tp.severity == "RED"
    assert tp.microsleeps == 1


def test_no_microsleep_no_force_red():
    f = FatigueFusion()
    tp = f.update(_healthy(), 0.0)
    assert tp.severity == "GREEN"


# ---------------------------------------------------------------------------
# FI clamping
# ---------------------------------------------------------------------------
def test_fi_clamped_to_100():
    f = FatigueFusion()
    m = {
        "perclos": 20.0,       # 100
        "bpm": 0.0,            # 100
        "avg_blink_ms": 500.0,  # 100
        "head_off": 1.0,       # 100
        "microsleep_count_total": 0,
        "microsleep_recent_30s": True,   # +20
        "microsleep_recent_3s": False,
        "coverage": "LOCKED",
    }
    tp = f.update(m, 0.0)
    # unreduced FI = 100 + 20 = 120 -> clamped to 100
    assert tp.fatigue == pytest.approx(100.0)
    assert tp.severity == "RED"


# ---------------------------------------------------------------------------
# NO_FACE guard: never silently GREEN
# ---------------------------------------------------------------------------
def test_no_face_with_no_prior_state_is_yellow_not_green():
    f = FatigueFusion()
    tp = f.update(_healthy(coverage="NO_FACE"), 0.0)
    assert tp.severity == "YELLOW"  # not silently GREEN
    assert tp.coverage == "NO_FACE"


def test_no_face_preserves_prior_severity_then_yellow():
    f = FatigueFusion()
    # Prior GREEN state under LOCKED coverage.
    f.update(_healthy(coverage="LOCKED", t=0.0), 0.0)
    # NO_FACE within the 5 s grace window -> preserve last severity (GREEN).
    tp1 = f.update(_healthy(coverage="NO_FACE", t=1.0), 1.0)
    assert tp1.severity == "GREEN"
    assert tp1.coverage == "NO_FACE"
    # After the grace window expires -> YELLOW (never silent GREEN).
    tp2 = f.update(_healthy(coverage="NO_FACE", t=6.0), 6.0)
    assert tp2.severity == "YELLOW"


def test_no_face_grace_is_configurable():
    f = FatigueFusion({"NO_FACE_GRACE_SECONDS": 2.0})
    f.update(_healthy(coverage="LOCKED", t=0.0), 0.0)
    tp1 = f.update(_healthy(coverage="NO_FACE", t=1.0), 1.0)
    assert tp1.severity == "GREEN"          # 1s < 2s grace
    tp2 = f.update(_healthy(coverage="NO_FACE", t=3.0), 3.0)
    assert tp2.severity == "YELLOW"         # 2s grace elapsed


def test_no_face_does_not_pollute_normal_recovery():
    f = FatigueFusion()
    f.update(_healthy(coverage="NO_FACE", t=0.0), 0.0)
    # Face restored -> back to computed GREEN under LOCKED coverage.
    tp = f.update(_healthy(coverage="LOCKED", t=1.0), 1.0)
    assert tp.severity == "GREEN"


# ---------------------------------------------------------------------------
# reset & robustness
# ---------------------------------------------------------------------------
def test_reset_clears_state():
    f = FatigueFusion()
    f.update(_healthy(coverage="LOCKED", t=0.0), 0.0)
    f.update(_healthy(coverage="NO_FACE", t=6.0), 6.0)
    f.reset()
    tp = f.update(_healthy(coverage="NO_FACE", t=0.0), 0.0)
    assert tp.severity == "YELLOW"  # no prior state after reset


def test_missing_metrics_fall_back_safely():
    f = FatigueFusion()
    tp = f.update({}, 0.0)  # empty dict -> conservative defaults
    # no coverage -> DEGRADED, never silently GREEN
    assert tp.coverage == "DEGRADED"
    assert 0.0 <= tp.fatigue <= 100.0
    assert tp.ear_avg is None