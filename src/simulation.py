"""Camera- and MediaPipe-free fatigue simulation for demos and tests.

This module provides a fully synthetic, in-memory fatigue timeline so a
presenter can exercise the *same* HUD, ``FatigueFusion``, alert dispatcher,
telemetry schema and headless export as the real camera pipeline -- without a
webcam and without MediaPipe face detection.

:class:`SimulatedFatigueTimeline.metrics_at(t)` returns a metrics dict with the
exact keys ``main.run`` feeds into ``FatigueFusion.update``:

    ear_l, ear_r, ear_avg, perclos, bpm, avg_blink_ms, head_off,
    pitch, yaw, roll, microsleep_count_total, microsleep_recent_30s,
    microsleep_recent_3s, coverage

The 45-second timeline walks through every severity state the fusion layer
supports, in order: GREEN -> YELLOW -> RED -> MICROSLEEP (forced RED) ->
NO_FACE (degraded, never GREEN) -> RECOVERY.

:func:`make_sim_frame` renders a non-biometric synthetic canvas (dark base with
drifting geometric shapes -- no human faces, no text) so the HUD has something
to draw on in GUI mode. No frame is ever written to disk.

Owned by: simulation agent.
"""

import math

import cv2
import numpy as np

# Default total timeline length in simulated seconds (same as the CLI default).
DURATION = 45.0

# Phase windows over the timeline, in order. t is in the half-open interval
# [start, end).
PHASE_LABELS = {
    "GREEN": (0.0, 10.0),
    "YELLOW": (10.0, 20.0),
    "RED": (20.0, 26.0),
    "MICROSLEEP": (26.0, 30.0),
    "NO_FACE": (30.0, 36.0),
    "RECOVERY": (36.0, 45.0),
}

# Steady-state severity each phase should map to once fusion interprets it.
# MICROSLEEP forces RED via ``microsleep_recent_3s``; NO_FACE is never GREEN.
PHASE_SEVERITY = {
    "GREEN": "GREEN",
    "YELLOW": "YELLOW",
    "RED": "RED",
    "MICROSLEEP": "RED",
    "NO_FACE": "YELLOW",
    "RECOVERY": "GREEN",
}
# Alias kept for clarity: the documented "forced severity" map.
FORCED_SEVERITY = PHASE_SEVERITY

# Signal keyframes on the "face locked" path: (t, perclos, bpm, avg_blink_ms,
# head_off). Signals are linearly interpolated between consecutive keyframes.
_SIGNAL_KEYFRAMES = (
    (0.0, (5.0, 18.0, 120.0, 0.02)),
    (10.0, (5.0, 18.0, 120.0, 0.02)),
    (20.0, (45.0, 10.0, 260.0, 0.35)),
    (26.0, (70.0, 6.0, 500.0, 0.70)),
    (30.0, (45.0, 8.0, 320.0, 0.45)),
    (36.0, (20.0, 12.0, 200.0, 0.15)),
    (45.0, (8.0, 18.0, 130.0, 0.02)),
)

# When the face is absent (NO_FACE), conservative, safe signal values are
# reported -- never fabricated "normal" readings.
_NO_FACE_PERCLOS = 4.0
_NO_FACE_BPM = 12.0
_NO_FACE_AVG_BLINK_MS = 110.0
_NO_FACE_HEAD_OFF = 0.05


def _lerp(a, b, f):
    return a + (b - a) * f


class SimulatedFatigueTimeline:
    """A synthetic fatigue timeline sampled at logical time ``t`` seconds.

    Parameters
    ----------
    duration : float, optional
        Total simulated timeline length in seconds (default ``45.0``).
    loop : bool, optional
        If True, times beyond ``duration`` wrap via ``t % duration`` so the
        timeline repeats indefinitely.
    """

    def __init__(self, duration=DURATION, loop=False):
        self.duration = float(duration) if float(duration) > 0 else DURATION
        self.loop = bool(loop)

    # ------------------------------------------------------------- time bookkeeping
    def normalize(self, t):
        """Map ``t`` into a valid timeline position (wrap or clamp)."""
        t = float(t)
        if self.loop and self.duration > 0:
            return t % self.duration
        if t < 0.0:
            return 0.0
        if t > self.duration:
            return self.duration
        return t

    def phase_at(self, t):
        """Return the phase label containing time ``t`` (see ``PHASE_LABELS``)."""
        t = self.normalize(t)
        for label, (start, end) in PHASE_LABELS.items():
            if start <= t < end:
                return label
        return "RECOVERY"

    # ------------------------------------------------------------- metrics
    def metrics_at(self, t):
        """Return the fully-populated metrics dict for simulated time ``t``."""
        t = self.normalize(t)
        phase = self.phase_at(t)

        if phase == "NO_FACE":
            # Conservative, safe values -- the face is gone, nothing is real.
            perclos = _NO_FACE_PERCLOS
            bpm = _NO_FACE_BPM
            avg_blink_ms = _NO_FACE_AVG_BLINK_MS
            head_off = _NO_FACE_HEAD_OFF
            ear_avg = ear_l = ear_r = None
            pitch = yaw = roll = None
            coverage = "NO_FACE"
        else:
            perclos, bpm, avg_blink_ms, head_off = self._interp_signals(t)
            ear_avg = self._ear_from(perclos, head_off)
            ear_l = ear_r = ear_avg
            pitch = 3.0 * math.sin(t * 0.5)
            yaw = -2.0 * math.cos(t * 0.4)
            roll = 1.0 * math.sin(t * 0.3)
            coverage = "LOCKED"

        microsleep_recent_3s = phase == "MICROSLEEP"
        # A microsleep is "recent" for 30 s after the event at t == 26.
        microsleep_recent_30s = microsleep_recent_3s or 26.0 <= t < 56.0
        microsleep_count_total = 1 if t >= 26.0 else 0

        return {
            "ear_l": ear_l,
            "ear_r": ear_r,
            "ear_avg": ear_avg,
            "perclos": perclos,
            "bpm": bpm,
            "avg_blink_ms": avg_blink_ms,
            "head_off": head_off,
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "microsleep_count_total": microsleep_count_total,
            "microsleep_recent_30s": microsleep_recent_30s,
            "microsleep_recent_3s": microsleep_recent_3s,
            "coverage": coverage,
        }

    # ------------------------------------------------------------- helpers
    def _interp_signals(self, t):
        """Linearly interpolate the four locked-path signals at ``t``."""
        keys = _SIGNAL_KEYFRAMES
        for i in range(len(keys) - 1):
            ta, va = keys[i]
            tb, vb = keys[i + 1]
            if ta <= t <= tb:
                f = 0.0 if tb == ta else (t - ta) / (tb - ta)
                return tuple(_lerp(va[j], vb[j], f) for j in range(4))
        return keys[-1][1]

    @staticmethod
    def _ear_from(perclos, head_off):
        """Smoothed EAR that drifts downward as fatigue rises (locked path)."""
        value = 0.32 - perclos * 0.001 - head_off * 0.10
        return max(0.05, min(0.35, value))


def make_sim_frame(width, height, t):
    """Render a non-biometric synthetic canvas for the HUD (BGR uint8).

    Dark base with slowly drifting geometric shapes -- circles, rectangles and
    lines. No human faces and no text are ever rendered here. The returned
    array has shape ``(H, W, 3)`` and dtype ``uint8``.
    """
    width = max(int(width), 1)
    height = max(int(height), 1)
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (12, 14, 18)  # dark base

    t = float(t)

    # Drifting circle.
    cx = int(width * (0.5 + 0.30 * math.sin(t * 0.30)))
    cy = int(height * (0.42 + 0.20 * math.cos(t * 0.22)))
    cv2.circle(frame, (cx, cy), 42, (34, 62, 96), -1)

    # Drifting rectangle.
    rx = int(width * (0.5 + 0.34 * math.cos(t * 0.26)))
    ry = int(height * (0.62 + 0.18 * math.sin(t * 0.40)))
    x2 = min(width - 1, rx + 72)
    y2 = min(height - 1, ry + 46)
    cv2.rectangle(frame, (rx, ry), (x2, y2), (54, 42, 78), -1)

    # Slowly waving lines.
    for i in range(5):
        base_y = int(height * (0.5 + 0.45 * math.sin(t * 0.5 + i * 1.3)))
        x0 = max(0, int((width / 5.0) * i))
        x1 = min(width - 1, x0 + width // 5)
        cv2.line(frame, (x0, base_y), (x1, base_y),
                 (30 + i * 12, 70 + i * 8, 100), 2)

    return frame