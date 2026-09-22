"""Fatigue fusion: weighted composite Fatigue Index (0-100) + severity.

Fuses five upstream telemetry signals into a single Fatigue Index (FI):

    1. PERCLOS                    (eye-closure percentage)
    2. Blink-rate abnormality     (bpm outside the healthy band)
    3. Average blink duration     (slow blinks -> higher fatigue)
    4. Head-deviation fraction    (how often the head was turned away)
    5. Recent microsleep penalty  (+20 flat if a microsleep happened <= 30 s)

Severity is GREEN / YELLOW / RED from the clamped FI and the spec thresholds.
A microsleep within the last ``MICROSLEEP_RED_SECONDS`` (3 s) forces RED
regardless of the computed FI.

Coverage guard (never a false-normal state)
-------------------------------------------
If ``coverage == "NO_FACE"`` no eye/pose signal is trustworthy, so the module
never silently reports GREEN:

* no prior state          -> severity YELLOW
* prior state exists      -> keep the prior severity for up to 5 s
                             (display continuity), then YELLOW.

All outputs are clamped to safe ranges; missing metrics fall back to safe,
conservative defaults (never fabricated normal values).

Contract note
-------------
The shared ``TelemetryPoint`` dataclass (src/telemetry/__init__.py) has no
microsleep-recent fields, so this module attaches them as extra attributes on
the returned instance: ``tp.microsleep_recent_3s`` and
``tp.microsleep_recent_30s`` (used by the alert dispatcher), plus
``tp.fi_raw`` (pre-penalty FI, useful for debugging).

Owned by: telemetry agent.
"""

from src.telemetry import TelemetryPoint

# ---------------------------------------------------------------------------
# Configurable defaults (per specification)
# ---------------------------------------------------------------------------
PERCLOS_WEIGHT = 0.35
BLINK_RATE_WEIGHT = 0.25
BLINK_DURATION_WEIGHT = 0.20
HEAD_DEVIATION_WEIGHT = 0.20
MICROSLEEP_PENALTY = 20.0

CAUTION_THRESHOLD = 40.0
ALERT_THRESHOLD = 70.0
MICROSLEEP_RED_SECONDS = 3.0

# Seconds of prior-severity display continuity allowed after NO_FACE starts.
NO_FACE_GRACE_SECONDS = 5.0


def _clamp(value, low, high):
    """Clamp ``value`` into ``[low, high]``, safe against non-finite input."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return low
    if v != v:  # NaN
        return low
    if v < low:
        return low
    if v > high:
        return high
    return v


def _perclos_norm(perclos):
    """``min(PERCLOS / 20.0, 1.0) * 100.0`` (0..100)."""
    return _clamp(min(_clamp(perclos, 0.0, 100.0) / 20.0, 1.0) * 100.0, 0.0, 100.0)


def _bpr_norm(bpm):
    """Blink-rate abnormality in 0..100.

    ``bpm < 15``   -> proportionally abnormal (15 bpm == 0, 0 bpm == 100)
    ``bpm > 30``   -> 50 (tachyblink-like, moderate)
    otherwise      -> 0 (healthy band).
    """
    bpm = _clamp(bpm, 0.0, 300.0)
    if bpm < 15.0:
        return _clamp((15.0 - bpm) / 15.0 * 100.0, 0.0, 100.0)
    if bpm > 30.0:
        return 50.0
    return 0.0


def _abd_norm(avg_blink_ms):
    """Average-blink-duration abnormality in 0..100.

    ``clamp((avg_blink_ms - 90) / 200, 0, 1) * 100``.
    """
    avg_blink_ms = _clamp(avg_blink_ms, 0.0, 10000.0)
    return _clamp((avg_blink_ms - 90.0) / 200.0, 0.0, 1.0) * 100.0


def _hdd_norm(head_dev_fraction):
    """Head-deviation fraction in 0..100."""
    return _clamp(head_dev_fraction, 0.0, 1.0) * 100.0


def _severity_for_fi(fi, microsleep_recent_3s):
    """Severity from clamped FI + forced RED on a recent microsleep."""
    fi = _clamp(fi, 0.0, 100.0)
    if microsleep_recent_3s:
        return "RED"
    if fi < CAUTION_THRESHOLD:
        return "GREEN"
    if fi < ALERT_THRESHOLD:
        return "YELLOW"
    return "RED"


class FatigueFusion:
    """Composite fatigue fusion: metrics dict -> TelemetryPoint."""

    def __init__(self, config: dict = None):
        cfg = {
            "PERCLOS_WEIGHT": PERCLOS_WEIGHT,
            "BLINK_RATE_WEIGHT": BLINK_RATE_WEIGHT,
            "BLINK_DURATION_WEIGHT": BLINK_DURATION_WEIGHT,
            "HEAD_DEVIATION_WEIGHT": HEAD_DEVIATION_WEIGHT,
            "MICROSLEEP_PENALTY": MICROSLEEP_PENALTY,
            "CAUTION_THRESHOLD": CAUTION_THRESHOLD,
            "ALERT_THRESHOLD": ALERT_THRESHOLD,
            "MICROSLEEP_RED_SECONDS": MICROSLEEP_RED_SECONDS,
            "NO_FACE_GRACE_SECONDS": NO_FACE_GRACE_SECONDS,
        }
        if config:
            cfg.update(config)

        self.perclos_weight = float(cfg["PERCLOS_WEIGHT"])
        self.blink_rate_weight = float(cfg["BLINK_RATE_WEIGHT"])
        self.blink_duration_weight = float(cfg["BLINK_DURATION_WEIGHT"])
        self.head_deviation_weight = float(cfg["HEAD_DEVIATION_WEIGHT"])
        self.microsleep_penalty = float(cfg["MICROSLEEP_PENALTY"])
        self.caution_threshold = float(cfg["CAUTION_THRESHOLD"])
        self.alert_threshold = float(cfg["ALERT_THRESHOLD"])
        self.microsleep_red_seconds = float(cfg["MICROSLEEP_RED_SECONDS"])
        self.no_face_grace_seconds = float(cfg["NO_FACE_GRACE_SECONDS"])

        self.reset()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def reset(self):
        """Clear prior state (last severity, NO_FACE onset, last FI)."""
        self._last_severity = None
        self._no_face_since_t = None
        self._last_fi = 0.0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, metrics, t):
        """Fuse one metrics dict at monotonic time ``t`` (seconds).

        Returns a fully-populated ``TelemetryPoint`` (see module docstring for
        the attached extra attributes). Never returns None.
        """
        t = float(t)

        coverage = metrics.get("coverage", "DEGRADED")
        if coverage not in ("LOCKED", "DEGRADED", "NO_FACE"):
            coverage = "DEGRADED"

        microsleep_recent_3s = bool(metrics.get("microsleep_recent_3s", False))
        microsleep_recent_30s = bool(metrics.get("microsleep_recent_30s", False))
        microsleep_count_total = int(
            metrics.get("microsleep_count_total", 0) or 0
        )

        # --- Signal normalization -------------------------------------------
        perclos_n = _perclos_norm(metrics.get("perclos", 0.0))
        bpr_n = _bpr_norm(metrics.get("bpm", 0.0))
        abd_n = _abd_norm(metrics.get("avg_blink_ms", 0.0))
        hdd_n = _hdd_norm(metrics.get("head_off", 0.0))

        ms_penalty = self.microsleep_penalty if microsleep_recent_30s else 0.0

        # --- Fatigue Index (clamped) ----------------------------------------
        fi_raw = (
            self.perclos_weight * perclos_n
            + self.blink_rate_weight * bpr_n
            + self.blink_duration_weight * abd_n
            + self.head_deviation_weight * hdd_n
        )
        fi = _clamp(fi_raw + ms_penalty, 0.0, 100.0)

        # --- Severity with NO_FACE coverage guard ---------------------------
        severity = _severity_for_fi(fi, microsleep_recent_3s)

        if coverage == "NO_FACE" and not microsleep_recent_3s:
            # Never silently report GREEN when the face is absent. A microsleep
            # within the last 3 s is the strongest signal and keeps RED.
            if self._no_face_since_t is None:
                self._no_face_since_t = t
            if self._last_severity is None:
                # No prior state: force YELLOW (degraded-unknown), keep FI as-is.
                severity = "YELLOW"
            elif t - self._no_face_since_t >= self.no_face_grace_seconds:
                # Grace expired: stop preserving the prior severity.
                severity = "YELLOW"
            else:
                # Preserve last known severity for up to 5 s (continuity).
                severity = self._last_severity
        else:
            self._no_face_since_t = None

        self._last_severity = severity
        self._last_fi = fi

        # --- Build TelemetryPoint (clamped fields) --------------------------
        point = TelemetryPoint(
            t=t,
            ear_l=metrics.get("ear_l"),
            ear_r=metrics.get("ear_r"),
            ear_avg=metrics.get("ear_avg"),
            perclos=_clamp(metrics.get("perclos", 0.0), 0.0, 100.0),
            bpm=_clamp(metrics.get("bpm", 0.0), 0.0, 1000.0),
            avg_blink_ms=_clamp(metrics.get("avg_blink_ms", 0.0), 0.0, 60000.0),
            head_off=_clamp(metrics.get("head_off", 0.0), 0.0, 1.0),
            pitch=metrics.get("pitch"),
            yaw=metrics.get("yaw"),
            roll=metrics.get("roll"),
            fatigue=fi,
            severity=severity,
            microsleeps=microsleep_count_total,
            coverage=coverage,
        )

        # Extra attributes consumed by the alert dispatcher (contract has no
        # microsleep-recent fields). Never written to logs by the logger.
        point.microsleep_recent_3s = microsleep_recent_3s
        point.microsleep_recent_30s = microsleep_recent_30s
        point.fi_raw = fi_raw

        return point
