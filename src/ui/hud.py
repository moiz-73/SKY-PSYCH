"""HUD window: dark aviation-style cockpit overlay driven by TelemetryPoint.

Owned by: ui agent (this goal).

:class:`HudOverlay` is the composite overlay. It takes one BGR frame and one
:class:`src.telemetry.TelemetryPoint` (plus the loop delta-t for FPS) and
draws the seven required element groups with the primitives from
:mod:`src.ui.renderer`:

1. Top-left panel   - SKYPSYCH AI title, coverage state, FPS, microsleep count
2. Top-center       - severity banner (GREEN / YELLOW / RED)
3. Right panel      - Fatigue Index %, PERCLOS bar, BPM, avg blink ms, head dev
4. Bottom-left      - EAR value + scrolling EAR waveform
5. Bottom-right     - pitch / yaw / roll + head-off indicator
6. NO_FACE coverage - large NO FACE warning; fatigue is never shown as valid
7. DEGRADED         - DEGRADED warning

Coverage honesty contract
-------------------------
When coverage is ``NO_FACE`` the fatigue number is replaced by ``--`` (the
fusion layer may still produce a numeric FI, but it is *not* a valid
measurement and must never be displayed as one). When coverage is
``DEGRADED`` the fatigue value is shown in amber with a DEGRADED warning.

Performance
-----------
The overlay adapts through :class:`src.ui.osd.PerformanceGovernor`:
``full`` -> ``no_waveform`` (waveform dropped first) -> ``minimal`` (only the
top-left panel, banner and warnings remain). Drawing is flat rectangles +
text only; the frame is mutated in place and no large buffers are allocated.
"""

import cv2

from src.ui import osd as _osd
from src.ui.renderer import (
    draw_arc_gauge,
    draw_bar,
    draw_panel,
    draw_severity_banner,
    draw_waveform,
    put_text,
)
from src.ui.osd import (
    AMBER,
    BOTTOM_LEFT_H,
    BOTTOM_LEFT_W,
    BOTTOM_RIGHT_H,
    BOTTOM_RIGHT_W,
    COVERAGE_COLORS,
    CYAN,
    GRAY,
    GREEN,
    MAGENTA,
    MARGIN,
    RED,
    RIGHT_H,
    RIGHT_W,
    SEVERITY_COLORS,
    TOP_LEFT_H,
    TOP_LEFT_W,
    WHITE,
)

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _fmt(value, digits=2, placeholder="--"):
    """Format a float for display; None/NaN -> ``placeholder``."""
    if value is None:
        return placeholder
    try:
        v = float(value)
    except (TypeError, ValueError):
        return placeholder
    if v != v:  # NaN
        return placeholder
    return f"{v:.{digits}f}"


def _severity_color(point):
    """Color for the severity banner, with a coverage-aware fallback."""
    severity = getattr(point, "severity", "GREEN")
    coverage = getattr(point, "coverage", "LOCKED")
    if severity == "RED":
        return RED
    if severity == "YELLOW":
        return AMBER
    # GREEN while coverage is lost would look like a false normal: fall back.
    if coverage == "NO_FACE":
        return GRAY
    if coverage == "DEGRADED":
        return AMBER
    return GREEN


# ---------------------------------------------------------------------------
# The overlay
# ---------------------------------------------------------------------------


class HudOverlay:
    """Dark aviation-style HUD drawn onto a BGR frame."""

    def __init__(self, config=None):
        self.osd = _osd.OsdState(config)
        self._head = {}
        if isinstance(config, dict):
            hp = config.get("head_pose")
            if isinstance(hp, dict):
                self._head = hp
        self.pitch_limit = float(self._head.get("pitch_limit_deg", 20.0))
        self.yaw_limit = float(self._head.get("yaw_limit_deg", 25.0))

    # ------------------------------------------------------------------ API

    def draw(self, frame, point, dt=None, t=None):
        """Draw the full HUD onto ``frame`` in place; returns the frame.

        ``dt`` is the measured loop delta-t (seconds); ``t`` an optional
        monotonic clock value for the performance governor.
        """
        fps, mode = self.osd.update(dt, t)
        h, w = frame.shape[:2]

        self._draw_top_left(frame, point, fps)
        self._draw_banner(frame, point, w)
        if mode != "minimal":
            self._draw_right_panel(frame, point)
            self._draw_bottom_right(frame, point)
            self._draw_bottom_left(frame, point, mode)
        self._draw_warnings(frame, point, w, h)
        return frame

    def push_ear(self, ear_value):
        """Feed one smoothed EAR value into the waveform buffer."""
        self.osd.ear_waveform.push(ear_value)

    def reset(self):
        self.osd.reset()

    # ------------------------------------------------------------- top-left

    def _draw_top_left(self, frame, point, fps):
        x, y = MARGIN, MARGIN
        w, h = TOP_LEFT_W, TOP_LEFT_H
        draw_panel(frame, x, y, w, h)
        put_text(frame, "SKYPSYCH AI", (x + 8, y + 22), 0.55, CYAN, 2)

        coverage = str(getattr(point, "coverage", "NO_FACE"))
        cov_color = COVERAGE_COLORS.get(coverage, GRAY)
        put_text(frame, "COV: " + coverage, (x + 8, y + 46), 0.5, cov_color, 1)
        put_text(frame, f"FPS: {fps:5.1f}", (x + 8, y + 68), 0.5, WHITE, 1)
        microsleeps = int(getattr(point, "microsleeps", 0) or 0)
        ms_color = RED if microsleeps > 0 else WHITE
        put_text(frame, f"MSLEEP: {microsleeps}", (x + 8, y + 90), 0.5,
                 ms_color, 1)

    # ------------------------------------------------------------ top-center

    def _draw_banner(self, frame, point, frame_w):
        banner_text = str(getattr(point, "severity", "GREEN"))
        color = _severity_color(point)
        draw_severity_banner(frame, frame_w // 2, MARGIN, banner_text, color)

    # ------------------------------------------------------------- right panel

    def _draw_right_panel(self, frame, point):
        h, w = frame.shape[:2]
        x = w - RIGHT_W - MARGIN
        y = MARGIN
        draw_panel(frame, x, y, RIGHT_W, RIGHT_H, title="TELEMETRY")

        coverage = str(getattr(point, "coverage", "NO_FACE"))
        fatigue = getattr(point, "fatigue", None)
        severity = str(getattr(point, "severity", "GREEN"))

        # --- Fatigue Index -------------------------------------------------
        put_text(frame, "FATIGUE", (x + 10, y + 42), 0.5, WHITE, 1)
        if coverage == "NO_FACE":
            put_text(frame, "--", (x + 10, y + 78), 1.5, GRAY, 2)
        else:
            fi_color = SEVERITY_COLORS.get(severity, GREEN)
            put_text(frame, _fmt(fatigue, 0), (x + 10, y + 78), 1.5,
                     fi_color, 2)
            put_text(frame, "%", (x + 92, y + 58), 0.6, fi_color, 1)

        # Arc gauge under the number.
        gauge_cy = y + 108
        if coverage == "NO_FACE":
            gauge_color = GRAY
        else:
            gauge_color = SEVERITY_COLORS.get(severity, GREEN)
        draw_arc_gauge(frame, x + 70, gauge_cy, 40, _frac(fatigue),
                       gauge_color)
        put_text(frame, "FI 0-100", (x + 46, gauge_cy + 56), 0.4, GRAY, 1)

        # --- PERCLOS bar ---------------------------------------------------
        perclos = getattr(point, "perclos", 0.0) or 0.0
        bar_y = gauge_cy + 66
        put_text(frame, "PERCLOS", (x + 10, bar_y), 0.45, WHITE, 1)
        draw_bar(frame, x + 96, bar_y - 11, 132, 12, perclos / 100.0, CYAN)
        put_text(frame, _fmt(perclos, 1) + "%", (x + 232, bar_y), 0.45,
                 WHITE, 1)

        # --- BPM / blink duration / head deviation -------------------------
        bpm = getattr(point, "bpm", 0.0) or 0.0
        avg_blink = getattr(point, "avg_blink_ms", 0.0) or 0.0
        head_off = getattr(point, "head_off", 0.0) or 0.0

        row = bar_y + 22
        put_text(frame, "BPM", (x + 10, row), 0.45, WHITE, 1)
        put_text(frame, _fmt(bpm, 1), (x + 96, row), 0.55, WHITE, 1)

        row += 24
        put_text(frame, "AVG BLINK", (x + 10, row), 0.45, WHITE, 1)
        put_text(frame, _fmt(avg_blink, 1) + " ms", (x + 96, row), 0.55,
                 WHITE, 1)

        row += 24
        put_text(frame, "HEAD DEV", (x + 10, row), 0.45, WHITE, 1)
        draw_bar(frame, x + 96, row - 11, 132, 12, head_off, MAGENTA)
        put_text(frame, _fmt(head_off * 100.0, 0) + "%", (x + 232, row),
                 0.45, WHITE, 1)

    # ------------------------------------------------------------ bottom-left

    def _draw_bottom_left(self, frame, point, mode):
        h, w = frame.shape[:2]
        x = MARGIN
        y = h - BOTTOM_LEFT_H - MARGIN
        draw_panel(frame, x, y, BOTTOM_LEFT_W, BOTTOM_LEFT_H)

        ear_avg = getattr(point, "ear_avg", None)
        coverage = str(getattr(point, "coverage", "NO_FACE"))
        ear_color = GRAY if coverage == "NO_FACE" else CYAN
        put_text(frame, "EAR", (x + 8, y + 22), 0.5, WHITE, 1)
        put_text(frame, _fmt(ear_avg, 3), (x + 8, y + 52), 0.8, ear_color, 1)

        if mode == "full" and self.osd.show_waveform:
            draw_waveform(frame, x + 88, y + 12, BOTTOM_LEFT_W - 98,
                          BOTTOM_LEFT_H - 22, self.osd.ear_waveform.values(),
                          CYAN)
        else:
            # Numeric-only fallback (waveform disabled for performance).
            put_text(frame, "waveform off", (x + 8, y + 76), 0.4, GRAY, 1)

    # ----------------------------------------------------------- bottom-right

    def _draw_bottom_right(self, frame, point):
        h, w = frame.shape[:2]
        x = w - BOTTOM_RIGHT_W - MARGIN
        y = h - BOTTOM_RIGHT_H - MARGIN
        draw_panel(frame, x, y, BOTTOM_RIGHT_W, BOTTOM_RIGHT_H)

        pitch = getattr(point, "pitch", None)
        yaw = getattr(point, "yaw", None)
        roll = getattr(point, "roll", None)
        coverage = str(getattr(point, "coverage", "NO_FACE"))
        pose_color = GRAY if coverage == "NO_FACE" else WHITE

        put_text(frame, "PITCH", (x + 10, y + 24), 0.45, WHITE, 1)
        put_text(frame, _fmt(pitch, 1) + " deg", (x + 92, y + 24), 0.5,
                 pose_color, 1)
        put_text(frame, "YAW", (x + 10, y + 48), 0.45, WHITE, 1)
        put_text(frame, _fmt(yaw, 1) + " deg", (x + 92, y + 48), 0.5,
                 pose_color, 1)
        put_text(frame, "ROLL", (x + 10, y + 72), 0.45, WHITE, 1)
        put_text(frame, _fmt(roll, 1) + " deg", (x + 92, y + 72), 0.5,
                 pose_color, 1)

        # Head-off indicator (current frame) based on pose thresholds.
        head_off_now = False
        if pitch is not None and yaw is not None:
            try:
                head_off_now = (
                    abs(float(pitch)) > self.pitch_limit
                    or abs(float(yaw)) > self.yaw_limit
                )
            except (TypeError, ValueError):
                head_off_now = False
        if coverage == "NO_FACE":
            dot = GRAY
            label = "NO DATA"
        elif head_off_now:
            dot = RED
            label = "HEAD OFF"
        else:
            dot = GREEN
            label = "HEAD OK"

        cv2.circle(frame, (x + 196, y + 50), 7, dot, -1)
        put_text(frame, label, (x + 150, y + 54), 0.45, dot, 1)

    # --------------------------------------------------------- coverage alerts

    def _draw_warnings(self, frame, point, frame_w, frame_h):
        coverage = str(getattr(point, "coverage", "NO_FACE"))
        if coverage == "NO_FACE":
            cx = frame_w // 2
            cy = frame_h // 2
            put_text(frame, "NO FACE", (cx - 62, cy + 10), 1.6, RED, 3)
            put_text(frame, "SIGNAL LOST - OPERATOR COVERAGE", (cx - 150, cy + 44),
                     0.5, RED, 1)
        elif coverage == "DEGRADED":
            cx = frame_w // 2
            put_text(frame, "COVERAGE DEGRADED", (cx - 118, frame_h // 2 - 40),
                     0.6, AMBER, 2)


def _frac(value):
    """Normalize a 0-100 value to 0..1 for bars/gauges; NaN-safe."""
    if value is None:
        return 0.0
    try:
        v = float(value) / 100.0
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return min(1.0, max(0.0, v))
