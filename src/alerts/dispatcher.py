"""Alert dispatcher: routes severity-state changes to advisory sinks.

The dispatcher is the anti-spam gate of the alert layer. It converts a stream
of ``TelemetryPoint`` severity values into a sparse stream of *events* (one
per meaningful transition) using three mechanisms:

* **Transition-only emission** — an event is produced only when the severity
  actually changes (first observation establishes the baseline and emits
  nothing, unless the very first severity is RED for safety).
* **Hysteresis (dwell)** — a new severity must persist for at least
  ``HYSTERESIS_SECONDS`` (1.0 s) before the transition is accepted, so brief
  flapping between GREEN/YELLOW never produces alerts. The exception is a RED
  caused by a recent microsleep (``microsleep_recent_3s``), which is treated
  as urgent and fires immediately.
* **Cooldowns** — repeated advisories of the same severity are throttled:
  at least ``YELLOW_COOLDOWN_SECONDS`` (5 s) between YELLOW events and
  ``RED_COOLDOWN_SECONDS`` (10 s) between RED events. Microsleep RED bypasses
  the RED cooldown (safety first).

Emitted events are plain abstract telemetry dictionaries:

    {"t": float, "severity": str, "fatigue": float, "message": str}

No raw frames, coordinates, or image data ever enter an event. Optional
sinks (a ``TelemetryEventLogger`` and/or an ``AudioAlerter``) may be supplied
through the config dict; sink failures are swallowed so dispatch never
crashes. Without sinks the dispatcher is pure: it only returns events.

Owned by: alerts agent.
"""

YELLOW_COOLDOWN_SECONDS = 5.0
RED_COOLDOWN_SECONDS = 10.0
HYSTERESIS_SECONDS = 1.0


class AlertDispatcher:
    """Detects severity transitions and emits rate-limited advisory events."""

    def __init__(self, config: dict = None):
        cfg = {
            "YELLOW_COOLDOWN_SECONDS": YELLOW_COOLDOWN_SECONDS,
            "RED_COOLDOWN_SECONDS": RED_COOLDOWN_SECONDS,
            "HYSTERESIS_SECONDS": HYSTERESIS_SECONDS,
            "logger": None,
            "audio": None,
        }
        if config:
            cfg.update(config)

        self.yellow_cooldown_seconds = float(cfg["YELLOW_COOLDOWN_SECONDS"])
        self.red_cooldown_seconds = float(cfg["RED_COOLDOWN_SECONDS"])
        self.hysteresis_seconds = float(cfg["HYSTERESIS_SECONDS"])
        self._logger = cfg.get("logger")
        self._audio = cfg.get("audio")

        self.reset()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def reset(self):
        """Clear all transition / cooldown state."""
        self._last_severity = None
        self._candidate_severity = None
        self._candidate_since_t = None
        self._emitted_severity = None
        self._last_yellow_t = None
        self._last_red_t = None
        self.last_event = None
        self.events_count = 0

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def dispatch(self, telemetry_point, t):
        """Feed one telemetry point at monotonic time ``t`` (seconds).

        Returns an event dict when a transition fires, otherwise None.
        """
        t = float(t)
        severity = getattr(telemetry_point, "severity", "GREEN")
        fatigue = float(getattr(telemetry_point, "fatigue", 0.0) or 0.0)
        is_microsleep = bool(
            getattr(telemetry_point, "microsleep_recent_3s", False)
        )

        # --- First observation: establish the baseline ----------------------
        if self._last_severity is None:
            self._last_severity = severity
            if severity == "RED":
                # Never swallow a RED that is present at startup.
                return self._emit(severity, t, fatigue, is_microsleep)
            return None

        # --- Same severity as the previous frame ----------------------------
        if severity == self._last_severity:
            if (
                self._candidate_severity == severity
                and self._candidate_since_t is not None
                and t - self._candidate_since_t >= self.hysteresis_seconds
            ):
                # Dwell satisfied: accept the pending transition.
                self._candidate_severity = None
                self._candidate_since_t = None
                return self._emit(severity, t, fatigue, is_microsleep)
            return None

        # --- Severity changed -----------------------------------------------
        self._last_severity = severity
        self._candidate_severity = severity
        self._candidate_since_t = t

        if severity == "RED" and is_microsleep:
            # Urgent: a recent microsleep forces immediate RED, bypassing both
            # hysteresis and cooldown.
            self._candidate_severity = None
            self._candidate_since_t = None
            return self._emit(severity, t, fatigue, is_microsleep)

        # Hysteresis: wait until the new severity has persisted.
        return None

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------
    def _emit(self, severity, t, fatigue, is_microsleep):
        """Apply cooldown, build the event, fan out to sinks.

        Returns the event dict, or None when suppressed by a cooldown.
        """
        if severity == "YELLOW":
            if (
                self._last_yellow_t is not None
                and t - self._last_yellow_t < self.yellow_cooldown_seconds
            ):
                return None  # repeated advisory too soon: suppress
            self._last_yellow_t = t
        elif severity == "RED":
            if not is_microsleep:
                if (
                    self._last_red_t is not None
                    and t - self._last_red_t < self.red_cooldown_seconds
                ):
                    return None  # repeated alert too soon: suppress
            self._last_red_t = t
        # GREEN (recovery) carries no cooldown.

        self._emitted_severity = severity
        event = {
            "t": t,
            "severity": severity,
            "fatigue": round(fatigue, 1),
            "message": self._message(severity, fatigue, is_microsleep),
        }
        self.last_event = event
        self.events_count += 1

        # Advisory sinks: never let a sink failure break dispatch.
        if self._logger is not None:
            try:
                self._logger.log_event(event)
            except Exception:
                pass
        if self._audio is not None:
            try:
                self._audio.alert(severity)
            except Exception:
                pass
        return event

    @staticmethod
    def _message(severity, fatigue, is_microsleep):
        """Advisory, privacy-safe human-readable message."""
        if severity == "RED" and is_microsleep:
            return "Microsleep detected - RED: stop and rest (advisory)"
        if severity == "RED":
            return (
                "Severe fatigue (RED, FI=%.1f): rest now (advisory)"
                % fatigue
            )
        if severity == "YELLOW":
            return (
                "Elevated fatigue (YELLOW, FI=%.1f): monitor alertness "
                "(advisory)" % fatigue
            )
        return "Fatigue back to GREEN (FI=%.1f)" % fatigue
