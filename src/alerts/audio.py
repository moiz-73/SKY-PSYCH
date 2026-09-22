"""Local audio alerting (advisory chimes only, no cloud TTS).

MVP behavior
------------
``AudioAlerter`` is a deliberately dependency-free stub: by default it only
records the last alerted severity (and an alert counter) so the rest of the
pipeline can observe that an alert was raised, without any audio library.

Optional beep
-------------
When ``enabled=True`` a short advisory beep is attempted with the standard
library ``winsound`` on Windows. Every audio operation is wrapped so any
failure (missing library, no audio device, console restrictions) is swallowed
silently: the alert layer must never crash or spam because sound is
unavailable. On non-Windows platforms the beep is a no-op.

Owned by: alerts agent.
"""

import sys

# Severities that deserve an audio cue. GREEN (recovery) stays silent.
_AUDIBLE_SEVERITIES = ("YELLOW", "RED")


class AudioAlerter:
    """Advisory audio cue stub. Records state; beeps only if safe."""

    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)
        self.last_severity = None
        self.alert_count = 0
        # Whether the most recent alert() actually played a beep.
        self.last_played = False

    # ------------------------------------------------------------------
    # Alerting
    # ------------------------------------------------------------------
    def alert(self, severity):
        """Handle one alert of ``severity`` (GREEN / YELLOW / RED).

        Always records the severity. Attempts a beep only for YELLOW / RED and
        only when enabled; any audio failure is silently ignored.
        """
        severity = str(severity).upper() if severity is not None else None
        if severity in ("YELLOW", "RED"):
            self.alert_count += 1
            self.last_severity = severity
            self.last_played = self._beep(severity) if self.enabled else False
        else:
            # GREEN recovery: record the state, never beep.
            self.last_severity = severity
            self.last_played = False
        return self.last_severity

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _beep(self, severity):
        """Attempt a short beep; returns True only if a sound was produced."""
        try:
            if sys.platform.startswith("win"):
                import winsound  # standard library on Windows

                winsound.Beep(
                    _frequency_for(severity), _duration_ms_for(severity)
                )
                return True
        except Exception:
            # Audio unavailable: fail silently, never raise.
            pass
        return False


def _frequency_for(severity):
    """Beep frequency in Hz (YELLOW calm, RED more urgent)."""
    return 880 if severity == "RED" else 660


def _duration_ms_for(severity):
    """Beep duration in milliseconds."""
    return 250 if severity == "RED" else 150
