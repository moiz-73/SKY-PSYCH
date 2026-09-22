"""Frame renderer: OpenCV drawing primitives for the aviation-style HUD.

Owned by: ui agent (this goal).

Every function here draws with OpenCV primitives only (``putText``,
``rectangle``, ``line``, ``circle``, ``ellipse``, ``polylines``). There is no
PIL, no pygame, no external font, no alpha blending: panels are flat dark
rectangles with a 1 px border, which keeps per-frame cost low and guarantees
readability over arbitrary video content.

The primitives are deliberately small and stateless; the composite overlay
lives in :mod:`src.ui.hud` and the state/colors/layout in :mod:`src.ui.osd`.
"""

import math

import cv2
import numpy as np

from src.ui.osd import (
    BAR_BG,
    BLACK,
    CYAN,
    EAR_THRESHOLD_DISPLAY,
    EAR_WAVEFORM_MAX,
    EAR_WAVEFORM_MIN,
    PANEL_BORDER,
    PANEL_BG,
    WHITE,
)

_FONT = cv2.FONT_HERSHEY_SIMPLEX


# ---------------------------------------------------------------------------
# Face-mesh contour index lists (standard MediaPipe FaceMesh topology).
# All indices are < 468, so the mesh renders for both the 468- and 478-point
# landmark outputs.
# ---------------------------------------------------------------------------
FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]
LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LEFT_EYEBROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_EYEBROW = [276, 283, 282, 295, 285, 300, 293, 334, 296, 336]
NOSE = [168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 97, 98, 327, 326, 45, 44, 275, 156, 220, 49, 48, 279]
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]

_FACE_CONTOURS = (
    FACE_OVAL,
    LEFT_EYE,
    RIGHT_EYE,
    LEFT_EYEBROW,
    RIGHT_EYEBROW,
    NOSE,
    LIPS,
)


def put_text(frame, text, org, scale=0.5, color=WHITE, thickness=1,
             shadow=True):
    """Draw text with an optional 1 px black shadow for readability.

    ``org`` is the bottom-left baseline coordinate (OpenCV convention).
    """
    x, y = int(org[0]), int(org[1])
    if shadow:
        cv2.putText(frame, str(text), (x + 1, y + 1), _FONT, scale,
                    BLACK, thickness, cv2.LINE_AA)
    cv2.putText(frame, str(text), (x, y), _FONT, scale, color, thickness,
                cv2.LINE_AA)


def draw_panel(frame, x, y, w, h, title=None, title_color=CYAN):
    """Flat dark panel with a 1 px border and an optional cyan title."""
    cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)),
                  PANEL_BG, -1)
    cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)),
                  PANEL_BORDER, 1)
    if title:
        put_text(frame, title, (int(x) + 8, int(y) + 18), 0.45,
                 title_color, 1)


def draw_bar(frame, x, y, w, h, fraction, fill_color):
    """Horizontal progress bar; ``fraction`` clamped to [0, 1]."""
    fraction = float(fraction)
    if fraction != fraction:  # NaN
        fraction = 0.0
    fraction = min(1.0, max(0.0, fraction))
    cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)),
                  BAR_BG, -1)
    fill_w = int(round(w * fraction))
    if fill_w > 0:
        cv2.rectangle(frame, (int(x), int(y)), (int(x + fill_w), int(y + h)),
                      fill_color, -1)
    cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)),
                  PANEL_BORDER, 1)


def draw_severity_banner(frame, center_x, y, text, color, w=230, h=46):
    """Top-center severity/coverage banner: dark fill + colored border/text.

    The banner text is centered horizontally on ``center_x``.
    """
    x0 = int(center_x - w / 2.0)
    y0 = int(y)
    cv2.rectangle(frame, (x0, y0), (x0 + int(w), y0 + int(h)), (24, 24, 28), -1)
    cv2.rectangle(frame, (x0, y0), (x0 + int(w), y0 + int(h)), color, 2)
    text_w = cv2.getTextSize(text, _FONT, 0.85, 2)[0][0]
    text_x = int(center_x - text_w / 2.0)
    put_text(frame, text, (text_x, y0 + int(h) - 15), 0.85, color, 2)


def draw_arc_gauge(frame, cx, cy, radius, fraction, color):
    """180-degree arc gauge (left sweep to right) used for the Fatigue Index."""
    cx, cy, r = int(cx), int(cy), int(radius)
    fraction = min(1.0, max(0.0, fraction))
    cv2.ellipse(frame, (cx, cy), (r, r), 0, 180, 360, (60, 60, 68), 4)
    if fraction > 0.01:
        cv2.ellipse(frame, (cx, cy), (r, r), 0, 180,
                    180 + 180.0 * fraction, color, 4)
    angle = math.radians(180 + 180.0 * fraction)
    nx = int(cx + (r - 14) * math.cos(angle))
    ny = int(cy + (r - 14) * math.sin(angle))
    cv2.line(frame, (cx, cy), (nx, ny), WHITE, 2)


def draw_waveform(frame, x, y, w, h, values, color,
                  min_v=EAR_WAVEFORM_MIN, max_v=EAR_WAVEFORM_MAX,
                  threshold=EAR_THRESHOLD_DISPLAY):
    """Scrolling line graph of recent values (e.g. smoothed EAR).

    Values are clamped to ``[min_v, max_v]``; the oldest value is drawn at the
    left edge. A dashed reference line is drawn at ``threshold`` when given.
    """
    x, y, w, h = int(x), int(y), int(w), int(h)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (34, 34, 40), -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), PANEL_BORDER, 1)

    span = max_v - min_v
    if span <= 0:
        return
    if threshold is not None:
        ty = int(y + h - (threshold - min_v) / span * h)
        for tx in range(x, x + w, 8):
            cv2.line(frame, (tx, ty), (min(tx + 4, x + w), ty),
                     (110, 110, 120), 1)

    if not values:
        return
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        if v is None or v != v:  # skip NaN
            continue
        v = min(max_v, max(min_v, float(v)))
        px = x + int(round(w * (i + 1) / n))
        py = y + int(round(h - (v - min_v) / span * h))
        pts.append((px, py))
    if len(pts) >= 2:
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], False, color, 1,
                      cv2.LINE_AA)
    elif len(pts) == 1:
        cv2.circle(frame, pts[0], 2, color, -1)


def draw_landmarks(frame, landmarks_px, color=CYAN, thickness=1,
                   draw_dots=True):
    """Draw a lightweight face-mesh overlay from pixel landmarks.

    Uses only static MediaPipe contour index lists + sparse dots, so it never
    depends on MediaPipe being importable at HUD render time.
    """
    if landmarks_px is None:
        return
    try:
        pts = np.asarray(landmarks_px, dtype=np.float32)
    except (TypeError, ValueError):
        return
    if pts.ndim != 2 or pts.shape[1] < 2 or pts.shape[0] == 0:
        return

    for contour in _FACE_CONTOURS:
        if max(contour) >= pts.shape[0]:
            continue
        poly = pts[list(contour)].astype(np.int32)
        cv2.polylines(frame, [poly], False, color, thickness, cv2.LINE_AA)

    if draw_dots:
        for i in range(0, min(pts.shape[0], 478), 4):
            cv2.circle(frame, (int(pts[i, 0]), int(pts[i, 1])), 1, color, -1)


def dim_frame(frame, factor=0.45):
    """Return a darkened copy of ``frame`` (used behind NO_FACE warnings).

    Uses a plain scaled copy — no alpha blending — and only when the warning
    is active, so the steady-state path never allocates a full copy.
    """
    return cv2.multiply(frame, np.array([factor, factor, factor],
                                        dtype=np.float64))
