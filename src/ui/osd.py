"""On-screen display (OSD) state, colors, layout, and text configuration.

Owned by: ui agent (this goal).

This module is *pure state and constants*: it defines the dark aviation-style
look (colors, panel geometry, labels) and small runtime helpers the HUD needs
(FPS estimator, scrolling EAR waveform buffer, and a performance governor that
degrades the overlay richness when the frame rate falls below target).

No drawing happens here; all OpenCV drawing lives in :mod:`src.ui.renderer`
and the composite overlay in :mod:`src.ui.hud`.

Only OpenCV-compatible BGR colors are used (no PIL, pygame, or external
fonts).
"""

import time
from collections import deque

# ---------------------------------------------------------------------------
# Colors (OpenCV BGR)
# ---------------------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (235, 235, 235)
DIM_TEXT = (150, 150, 162)
PANEL_BG = (16, 16, 20)
PANEL_BORDER = (82, 82, 94)
BAR_BG = (52, 52, 60)

GREEN = (70, 190, 70)
AMBER = (0, 190, 255)
RED = (40, 40, 235)
CYAN = (230, 200, 60)
MAGENTA = (210, 80, 200)
GRAY = (120, 120, 128)

# Severity / coverage -> color mapping (shared by every panel).
SEVERITY_COLORS = {
    "GREEN": GREEN,
    "YELLOW": AMBER,
    "RED": RED,
}
COVERAGE_COLORS = {
    "LOCKED": GREEN,
    "DEGRADED": AMBER,
    "NO_FACE": RED,
}

# ---------------------------------------------------------------------------
# Layout (pixel geometry; anchored to frame edges by the HUD)
# ---------------------------------------------------------------------------
MARGIN = 10

TOP_LEFT_W = 260
TOP_LEFT_H = 122
RIGHT_W = 250
RIGHT_H = 320
BOTTOM_LEFT_W = 340
BOTTOM_LEFT_H = 118
BOTTOM_RIGHT_W = 250
BOTTOM_RIGHT_H = 118

BANNER_W = 230
BANNER_H = 46

# Waveform capacity (small fixed buffer, no per-frame large allocations).
EAR_WAVEFORM_CAPACITY = 150
EAR_THRESHOLD_DISPLAY = 0.22  # reference line drawn on the EAR waveform
EAR_WAVEFORM_MIN = 0.0
EAR_WAVEFORM_MAX = 0.45

# Performance governor defaults.
DEFAULT_TARGET_FPS = 25.0
DEFAULT_DEGRADE_AFTER_S = 3.0
DEFAULT_MINIMAL_AFTER_S = 8.0


def _ui_settings(config):
    """Pull the ``ui`` group out of a settings dict; safe for any input."""
    if not isinstance(config, dict):
        return {}
    group = config.get("ui")
    return group if isinstance(group, dict) else {}


class FpsEstimator:
    """Exponential moving average of instantaneous frame rate (Hz)."""

    def __init__(self, alpha: float = 0.1):
        self.alpha = float(alpha)
        self._fps = 0.0

    def update(self, dt):
        """Feed one loop delta-t (seconds); returns the smoothed FPS."""
        if dt is None or dt <= 0:
            return self._fps
        instant = 1.0 / float(dt)
        if self._fps <= 0.0:
            self._fps = instant
        else:
            self._fps = self.alpha * instant + (1.0 - self.alpha) * self._fps
        return self._fps

    @property
    def fps(self):
        """Most recent smoothed FPS (0.0 before the first update)."""
        return self._fps

    def reset(self):
        self._fps = 0.0


class EarWaveform:
    """Fixed-capacity scrolling buffer of recent smoothed EAR values.

    ``None`` values (face absent) are skipped: the waveform must never plot
    fabricated eye data, and a coverage dropout simply stalls the trace.
    """

    def __init__(self, capacity: int = EAR_WAVEFORM_CAPACITY):
        self.capacity = int(capacity)
        self._buf = deque(maxlen=self.capacity)

    def push(self, value):
        if value is not None:
            try:
                self._buf.append(float(value))
            except (TypeError, ValueError):
                pass

    def values(self):
        """List of buffered values, oldest first."""
        return list(self._buf)

    def clear(self):
        self._buf.clear()

    def __len__(self):
        return len(self._buf)


class PerformanceGovernor:
    """Degrades HUD richness when FPS stays below target.

    Modes (in degradation order):
      "full"        -> all overlays, including the EAR waveform
      "no_waveform" -> waveform dropped first (biggest per-frame cost)
      "minimal"     -> only top-left panel + severity banner + warnings

    Recovery to a richer mode is immediate when FPS is back above target.
    """

    def __init__(self, target_fps=DEFAULT_TARGET_FPS,
                 degrade_after_s=DEFAULT_DEGRADE_AFTER_S,
                 minimal_after_s=DEFAULT_MINIMAL_AFTER_S):
        self.target_fps = float(target_fps)
        self.degrade_after_s = float(degrade_after_s)
        self.minimal_after_s = float(minimal_after_s)
        self._slow_since = None
        self.mode = "full"

    def update(self, fps, t=None):
        """Feed the current FPS; returns the active mode string."""
        now = t if t is not None else time.monotonic()
        if fps < self.target_fps:
            if self._slow_since is None:
                self._slow_since = now
            duration = now - self._slow_since
            if self.mode != "minimal" and duration >= self.minimal_after_s:
                self.mode = "minimal"
            elif self.mode != "no_waveform" and duration >= self.degrade_after_s:
                self.mode = "no_waveform"
        else:
            self._slow_since = None
            self.mode = "full"
        return self.mode

    def reset(self):
        self._slow_since = None
        self.mode = "full"


class OsdState:
    """Per-run OSD state: FPS estimate, EAR waveform, performance governor.

    Also resolves UI preferences from the config ``ui`` group
    (``show_waveform``, ``show_bars``, ``target_fps``).
    """

    def __init__(self, config=None):
        settings = _ui_settings(config)
        self.show_waveform = bool(settings.get("show_waveform", True))
        self.show_bars = bool(settings.get("show_bars", True))
        target_fps = float(settings.get("target_fps", DEFAULT_TARGET_FPS))
        self.governor = PerformanceGovernor(target_fps=target_fps)
        self.fps = FpsEstimator()
        self.ear_waveform = EarWaveform()
        self.mode = "full"

    def update(self, dt, t=None):
        """Advance FPS + governor; returns (fps, mode)."""
        fps = self.fps.update(dt)
        if self.show_waveform:
            self.mode = self.governor.update(fps, t)
        else:
            # Waveform disabled by config: never run it.
            self.mode = "no_waveform" if self.mode != "minimal" else "minimal"
        return fps, self.mode

    def reset(self):
        self.fps.reset()
        self.ear_waveform.clear()
        self.governor.reset()
        self.mode = "full"
