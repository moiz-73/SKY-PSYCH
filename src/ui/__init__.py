"""SkyPsych - ui subpackage (dark aviation-style HUD).

Owned by: ui agent (this goal).

Public API:
    HudOverlay   - composite dark-mode HUD overlay drawn onto a BGR frame
    draw_landmarks - optional face-mesh landmark overlay (used by main.py
                     when ``--show-landmarks`` is given)
    OsdState     - OSD runtime state (FPS, waveform buffer, perf governor)
"""

from src.ui.hud import HudOverlay
from src.ui.renderer import draw_landmarks
from src.ui.osd import (
    OsdState,
    FpsEstimator,
    EarWaveform,
    PerformanceGovernor,
)

__all__ = [
    "HudOverlay",
    "draw_landmarks",
    "OsdState",
    "FpsEstimator",
    "EarWaveform",
    "PerformanceGovernor",
]