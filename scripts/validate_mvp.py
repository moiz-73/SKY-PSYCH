"""SkyPsych AI MVP validation script (camera-free, deterministic).

Runs the full set of contract checks against the production modules using
synthetic inputs only. Nothing here requires a camera, a live video source,
or a real human face. Each check prints ``PASS`` or ``FAIL``; the process
exits 0 only when every check passes.

Checks
------
  a. IMPORTS            core deps + ``main`` + ``src.telemetry`` import
  b. CONFIG LOADING     main.load_config('config/settings.yaml') groups
  c. TELEMETRY CONTRACT TelemetryPoint field order == CSV_COLUMNS == 15 names
  d. SYNTHETIC GREEN    low-fatigue inputs -> severity GREEN, fatigue < 40
  e. SYNTHETIC YELLOW   elevated inputs   -> severity YELLOW (40 <= fi < 70)
  f. SYNTHETIC RED      severe inputs     -> severity RED, fatigue >= 70
  g. MICROSLEEP RED     microsleep_recent_3s forces RED at low fatigue
  h. NO_FACE SAFETY     coverage NO_FACE never GREEN (YELLOW), incl. >5 s grace
  i. HEADLESS CSV SCHEMA CsvSink header + 15-field rows
  j. ALERT LOGGER       privacy whitelist enforced in-memory and on disk

Run from the repository root::

    .\\.venv\\Scripts\\python.exe scripts\\validate_mvp.py
"""

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS = []
_EXIT = 0


def check(name, ok, detail=""):
    """Record one check result and print a PASS/FAIL line."""
    global _EXIT
    tag = "PASS" if ok else "FAIL"
    suffix = ("  [" + detail + "]") if detail else ""
    print("%-22s %s%s" % (name, tag, suffix))
    RESULTS.append((name, ok, detail))
    if not ok:
        _EXIT = 1


def main():
    import cv2  # noqa: F401
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import yaml  # noqa: F401
    import mediapipe  # noqa: F401
    import pytest  # noqa: F401
    import main as main_mod
    from src.telemetry import TelemetryPoint

    # --- a. IMPORTS ------------------------------------------------------
    try:
        cv2.CascadeClassifier, numpy.ndarray, scipy.fft, yaml.safe_load
        mediapipe.solutions, pytest.approx
        TelemetryPoint(t=0.0, ear_l=None, ear_r=None, ear_avg=None, perclos=0.0,
                       bpm=0.0, avg_blink_ms=0.0, head_off=0.0, pitch=None,
                       yaw=None, roll=None, fatigue=0.0, severity="GREEN",
                       microsleeps=0, coverage="NO_FACE")
        check("IMPORTS_OK", True)
    except Exception as exc:
        check("IMPORTS_OK", False, repr(exc))

    # --- b. CONFIG LOADING ------------------------------------------------
    cfg = main_mod.load_config("config/settings.yaml")
    ok = (isinstance(cfg, dict)
          and isinstance(cfg.get("ear"), dict)
          and isinstance(cfg.get("fatigue"), dict)
          and isinstance(cfg.get("severity"), dict))
    check("CONFIG_LOADING", ok,
          "groups=%s" % sorted(k for k in ("ear", "fatigue", "severity")
                               if isinstance(cfg.get(k), dict)))

    # --- c. TELEMETRY CONTRACT -------------------------------------------
    import dataclasses
    expected = [
        "t", "ear_l", "ear_r", "ear_avg", "perclos", "bpm", "avg_blink_ms",
        "head_off", "pitch", "yaw", "roll", "fatigue", "severity",
        "microsleeps", "coverage",
    ]
    field_names = [f.name for f in dataclasses.fields(TelemetryPoint)]
    ok = (field_names == main_mod.CSV_COLUMNS == expected)
    check("TELEMETRY_CONTRACT", ok,
          "order=%s" % ("ok" if ok else field_names))

    # --- d/e/f/g/h. FUSION SEVERITIES -------------------------------------
    from src.telemetry.fusion import FatigueFusion

    def base(**kw):
        m = {
            "perclos": 5.0, "bpm": 18.0, "avg_blink_ms": 120.0,
            "head_off": 0.02, "coverage": "LOCKED",
            "microsleep_recent_3s": False, "microsleep_recent_30s": False,
            "microsleep_count_total": 0, "ear_l": 0.30, "ear_r": 0.30,
            "ear_avg": 0.30, "pitch": 0.0, "yaw": 0.0, "roll": 0.0,
        }
        m.update(kw)
        return m

    fusion = FatigueFusion()

    tp_g = fusion.update(base(perclos=5.0, bpm=18.0,
                              avg_blink_ms=120.0, head_off=0.02), 1.0)
    ok = (tp_g.severity == "GREEN" and tp_g.fatigue < 40.0)
    check("SYNTHETIC_GREEN", ok,
          "severity=%s fatigue=%.2f" % (tp_g.severity, tp_g.fatigue))

    tp_y = fusion.update(base(perclos=50.0, bpm=18.0,
                              avg_blink_ms=300.0, head_off=0.10), 2.0)
    ok = (tp_y.severity == "YELLOW"
          and 40.0 <= tp_y.fatigue < 70.0)
    check("SYNTHETIC_YELLOW", ok,
          "severity=%s fatigue=%.2f" % (tp_y.severity, tp_y.fatigue))

    tp_r = fusion.update(base(perclos=85.0, bpm=5.0,
                              avg_blink_ms=600.0, head_off=0.9), 3.0)
    ok = (tp_r.severity == "RED" and tp_r.fatigue >= 70.0)
    check("SYNTHETIC_RED", ok,
          "severity=%s fatigue=%.2f" % (tp_r.severity, tp_r.fatigue))

    tp_ms = fusion.update(base(perclos=5.0, bpm=18.0, avg_blink_ms=120.0,
                               head_off=0.02, microsleep_recent_3s=True,
                               microsleep_recent_30s=True), 4.0)
    ok = (tp_ms.severity == "RED" and tp_ms.fatigue < 40.0)
    check("MICROSLEEP_FORCES_RED", ok,
          "severity=%s fatigue=%.2f" % (tp_ms.severity, tp_ms.fatigue))

    fusion.reset()
    nf = dict(base(perclos=5.0, bpm=18.0, avg_blink_ms=120.0, head_off=0.02,
                   coverage="NO_FACE", ear_l=None, ear_r=None, ear_avg=None,
                   pitch=None, yaw=None, roll=None))
    tp_n0 = fusion.update(nf, 0.0)
    tp_n6 = fusion.update(nf, 6.0)  # beyond NO_FACE_GRACE_SECONDS (5 s)
    ok = (tp_n0.severity != "GREEN" and tp_n6.severity != "GREEN"
          and tp_n0.severity == "YELLOW" and tp_n6.severity == "YELLOW")
    check("NO_FACE_NEVER_GREEN", ok,
          "t0=%s t6=%s" % (tp_n0.severity, tp_n6.severity))

    # --- i. HEADLESS CSV SCHEMA -------------------------------------------
    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        sink = main_mod.CsvSink(csv_path)
        sink.write(tp_g)
        sink.close()
        rows = list(csv.reader(open(csv_path, newline="", encoding="utf-8")))
        header_ok = bool(rows) and rows[0] == main_mod.CSV_COLUMNS
        rows_ok = all(len(row) == 15 for row in rows[1:]) and len(rows) == 2
        check("HEADLESS_CSV_SCHEMA", header_ok and rows_ok,
              "header=%s rows=%d fields=%s"
              % (header_ok, len(rows) - 1,
                 ",".join(str(len(r)) for r in rows)))
    finally:
        try:
            os.remove(csv_path)
        except OSError:
            pass

    # --- j. ALERT LOGGER PRIVACY WHITELIST --------------------------------
    from src.alerts.logger import TelemetryEventLogger

    fd, log_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    try:
        lg = TelemetryEventLogger(log_path)
        sanitized = lg.log_event({
            "t": 1.0, "severity": "RED", "fatigue": 80.0, "message": "x",
            "ear_l": 0.1, "landmarks": [1, 2], "frame_path": "C:/x.jpg",
            "pitch": 5.0, "image": "junk",
        })
        lg.close()

        whitelist = {"schema_version", "t", "severity", "fatigue",
                     "message", "event_type"}
        forbidden = {"ear_l", "landmarks", "frame_path", "pitch", "image"}

        def _assert(record):
            if not isinstance(record, dict):
                return False
            return (set(record.keys()) <= whitelist
                    and not (set(record.keys()) & forbidden))

        mem_ok = _assert(sanitized)
        disk_ok = False
        with open(log_path, encoding="utf-8") as fh:
            for line in fh:
                disk_ok = _assert(json.loads(line))
        check("ALERT_LOGGER_PRIVACY", mem_ok and disk_ok,
              "record=%s" % json.dumps(sanitized, sort_keys=True))
    finally:
        try:
            os.remove(log_path)
        except OSError:
            pass

    # --- summary ----------------------------------------------------------
    print()
    print("CHECK SUMMARY")
    print("-------------")
    for name, ok, detail in RESULTS:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    print("  passed=%d/%d" % (sum(1 for _, ok, _ in RESULTS if ok),
                              len(RESULTS)))
    print()
    print("VALIDATE_MVP: PASS" if _EXIT == 0 else "VALIDATE_MVP: FAIL")
    return _EXIT


if __name__ == "__main__":
    sys.exit(main())
