"""Tests for src/alerts/: dispatcher, logger, audio.

Verifies the anti-spam contract of the alert layer: events fire only on
severity transitions, hysteresis prevents flapping, YELLOW/RED cooldowns
suppress repeats, microsleep RED bypasses both hysteresis and cooldown, and
the event logger persists abstract telemetry only (no image/frame fields).

Owned by: alerts agent.
"""

import json

import pytest

from src.alerts import AlertDispatcher, TelemetryEventLogger, AudioAlerter
from src.telemetry import TelemetryPoint


def _point(severity, fatigue=0.0, microsleep_3s=False, t=0.0):
    """Build a TelemetryPoint with the dispatcher-facing microsleep flag."""
    p = TelemetryPoint(
        t=t,
        ear_l=None, ear_r=None, ear_avg=None,
        perclos=0.0, bpm=0.0, avg_blink_ms=0.0, head_off=0.0,
        pitch=None, yaw=None, roll=None,
        fatigue=fatigue,
        severity=severity,
        microsleeps=1 if microsleep_3s else 0,
        coverage="LOCKED",
    )
    p.microsleep_recent_3s = microsleep_3s
    p.microsleep_recent_30s = microsleep_3s
    return p


# ---------------------------------------------------------------------------
# Dispatcher: transitions
# ---------------------------------------------------------------------------
def test_severity_transition_produces_event():
    d = AlertDispatcher()
    assert d.dispatch(_point("GREEN"), 0.0) is None      # baseline
    assert d.dispatch(_point("YELLOW"), 1.0) is None     # hysteresis dwell
    ev = d.dispatch(_point("YELLOW"), 2.1)               # dwell satisfied
    assert ev is not None
    assert ev["severity"] == "YELLOW"
    assert ev["t"] == pytest.approx(2.1)
    assert isinstance(ev["fatigue"], float)
    assert isinstance(ev["message"], str) and ev["message"]
    assert set(ev.keys()) == {"t", "severity", "fatigue", "message"}


def test_no_event_when_severity_stays_same():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    assert d.dispatch(_point("GREEN"), 1.0) is None
    assert d.dispatch(_point("GREEN"), 10.0) is None
    assert d.events_count == 0


def test_hysteresis_suppresses_flapping():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("YELLOW"), 1.0)
    d.dispatch(_point("GREEN"), 1.5)   # reverts before 1 s dwell
    assert d.events_count == 0
    # A persistent YELLOW still alerts once dwell is met.
    d.dispatch(_point("YELLOW"), 2.0)
    ev = d.dispatch(_point("YELLOW"), 3.1)
    assert ev is not None and ev["severity"] == "YELLOW"


def test_first_dispatch_red_is_not_swallowed():
    d = AlertDispatcher()
    ev = d.dispatch(_point("RED", fatigue=90.0), 0.0)
    assert ev is not None and ev["severity"] == "RED"


# ---------------------------------------------------------------------------
# Dispatcher: cooldowns
# ---------------------------------------------------------------------------
def test_repeated_yellow_inside_cooldown_no_duplicate():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("YELLOW"), 1.0)
    assert d.dispatch(_point("YELLOW"), 2.1) is not None   # event 1
    # Leave YELLOW (recovery GREEN event fires), then re-enter within 5 s.
    d.dispatch(_point("GREEN"), 3.0)
    d.dispatch(_point("GREEN"), 4.1)
    d.dispatch(_point("YELLOW"), 5.0)
    # 6.1 - 2.1 = 4.0 s < 5 s cooldown -> suppressed.
    assert d.dispatch(_point("YELLOW"), 6.1) is None
    assert d.events_count == 2  # YELLOW + GREEN recovery only


def test_repeated_red_inside_cooldown_no_duplicate():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("RED", fatigue=90.0), 1.0)
    assert d.dispatch(_point("RED", fatigue=90.0), 2.1) is not None  # event 1
    d.dispatch(_point("GREEN"), 3.0)
    d.dispatch(_point("GREEN"), 4.1)
    d.dispatch(_point("RED", fatigue=90.0), 5.0)
    # 6.1 - 2.1 = 4.0 s < 10 s cooldown -> suppressed.
    assert d.dispatch(_point("RED", fatigue=90.0), 6.1) is None
    assert d.events_count == 2
    # After the cooldown window (>= 10 s), a new RED transition fires again.
    d.dispatch(_point("GREEN"), 12.0)
    d.dispatch(_point("GREEN"), 13.1)
    d.dispatch(_point("RED", fatigue=95.0), 14.0)
    ev = d.dispatch(_point("RED", fatigue=95.0), 15.1)
    assert ev is not None and ev["severity"] == "RED"
    assert d.events_count == 4


def test_microsleep_red_bypasses_cooldown():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("RED", fatigue=90.0), 1.0)
    assert d.dispatch(_point("RED", fatigue=90.0), 2.1) is not None  # event 1
    d.dispatch(_point("GREEN"), 3.0)
    d.dispatch(_point("GREEN"), 4.1)
    # A microsleep-forced RED only 5 s after the last RED (cooldown 10 s):
    # the microsleep bypasses the cooldown and fires immediately.
    ev = d.dispatch(_point("RED", fatigue=40.0, microsleep_3s=True), 5.0)
    assert ev is not None
    assert ev["severity"] == "RED"
    assert ev["fatigue"] == pytest.approx(40.0)
    assert d.events_count == 3


def test_microsleep_red_bypasses_hysteresis():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    # RED+microsleep fires on the very next frame (no 1 s dwell required).
    ev = d.dispatch(_point("RED", fatigue=35.0, microsleep_3s=True), 1.0)
    assert ev is not None and ev["severity"] == "RED"


# ---------------------------------------------------------------------------
# Dispatcher: optional sinks via config
# ---------------------------------------------------------------------------
def test_dispatcher_forwards_events_to_logger_sink(tmp_path):
    log_path = tmp_path / "sink.jsonl"
    logger = TelemetryEventLogger(str(log_path))
    d = AlertDispatcher({"logger": logger})
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("YELLOW"), 1.0)
    d.dispatch(_point("YELLOW"), 2.1)  # event
    logger.close()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["severity"] == "YELLOW"


def test_dispatcher_audio_sink_receives_alerts():
    audio = AudioAlerter(enabled=False)
    d = AlertDispatcher({"audio": audio})
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("YELLOW"), 1.0)
    d.dispatch(_point("YELLOW"), 2.1)
    assert audio.last_severity == "YELLOW"
    assert audio.alert_count == 1


def test_reset_clears_dispatcher_state():
    d = AlertDispatcher()
    d.dispatch(_point("GREEN"), 0.0)
    d.dispatch(_point("YELLOW"), 1.0)
    d.dispatch(_point("YELLOW"), 2.1)
    d.reset()
    assert d.dispatch(_point("GREEN"), 0.0) is None      # baseline again
    assert d.events_count == 0


# ---------------------------------------------------------------------------
# Logger: abstract telemetry only
# ---------------------------------------------------------------------------
def test_logger_output_contains_no_image_or_frame_fields(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = TelemetryEventLogger(str(log_path))
    logger.log_event(
        {
            "t": 1.5,
            "severity": "RED",
            "fatigue": 81.2,
            "message": "Severe fatigue (advisory)",
            # Forbidden / non-abstract fields that must never be persisted:
            "frame_path": "C:/frames/frame_00123.jpg",
            "image": "raw-frame-base64==",
            "landmarks": [[1.0, 2.0], [3.0, 4.0]],
            "ear_l": 0.31,
            "face": True,
            "pitch": 12.5,
        }
    )
    logger.close()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    # Only the abstract whitelist survived.
    assert set(record.keys()) == {"schema_version", "t", "severity",
                                  "fatigue", "message"}
    for forbidden in ("frame_path", "image", "landmarks", "ear_l", "face",
                      "pitch"):
        assert forbidden not in record
    assert record["schema_version"] == 1
    assert record["severity"] == "RED"
    assert record["fatigue"] == pytest.approx(81.2)


def test_logger_memory_only_writes_nothing(tmp_path):
    logger = TelemetryEventLogger(output_path=None)
    rec = logger.log_event({"t": 1.0, "severity": "YELLOW", "fatigue": 55.0,
                            "message": "m"})
    assert rec is not None
    assert rec["schema_version"] == 1
    assert logger.count == 1
    logger.close()
    # Nothing on disk: no file was ever created.
    assert not list(tmp_path.glob("*.jsonl"))


def test_logger_jsonl_one_record_per_line(tmp_path):
    log_path = tmp_path / "two.jsonl"
    logger = TelemetryEventLogger(str(log_path))
    logger.log_event({"t": 0.0, "severity": "GREEN", "fatigue": 10.0,
                      "message": "a"})
    logger.log_event({"t": 5.0, "severity": "RED", "fatigue": 90.0,
                      "message": "b"})
    logger.close()
    records = [json.loads(line) for line in
               log_path.read_text(encoding="utf-8").strip().splitlines()]
    assert [r["severity"] for r in records] == ["GREEN", "RED"]
    assert [r["schema_version"] for r in records] == [1, 1]


# ---------------------------------------------------------------------------
# Audio: dependency-free stub
# ---------------------------------------------------------------------------
def test_audio_stub_records_last_severity_only():
    a = AudioAlerter(enabled=False)
    assert a.alert("RED") == "RED"
    assert a.last_severity == "RED"
    assert a.alert_count == 1
    assert a.last_played is False  # disabled -> never attempts a beep


def test_audio_ignores_green():
    a = AudioAlerter(enabled=True)
    a.alert("GREEN")
    assert a.last_severity == "GREEN"
    assert a.alert_count == 0
