"""SkyPsych - alerts subpackage.

Advisory, rate-limited, privacy-preserving alerting built on the severity
stream produced by the fatigue fusion layer:

    AlertDispatcher        severity transitions -> sparse event stream
    TelemetryEventLogger   abstract telemetry JSON Lines (never images)
    AudioAlerter           optional local advisory beep stub (no deps)

Owned by: alerts agent.
"""

from src.alerts.dispatcher import AlertDispatcher
from src.alerts.logger import TelemetryEventLogger
from src.alerts.audio import AudioAlerter

__all__ = ["AlertDispatcher", "TelemetryEventLogger", "AudioAlerter"]
