"""SkyPsych - shared telemetry contract.

This module defines the single dataclass and type aliases that every pipeline
stage (ingestion -> vision -> telemetry -> fusion -> alerts -> HUD) exchanges.
It is the shared contract between all future implementation agents.

Owned by: bootstrap agent (shared contract, do not change without updating all
consumers).
"""

from dataclasses import dataclass
from typing import Literal

Severity = Literal["GREEN", "YELLOW", "RED"]
Coverage = Literal["LOCKED", "DEGRADED", "NO_FACE"]


@dataclass
class TelemetryPoint:
    t: float
    ear_l: float
    ear_r: float
    ear_avg: float
    perclos: float
    bpm: float
    avg_blink_ms: float
    head_off: float
    pitch: float
    yaw: float
    roll: float
    fatigue: float
    severity: Severity
    microsleeps: int
    coverage: Coverage
