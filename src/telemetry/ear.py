"""Eye Aspect Ratio (EAR) computation per eye plus averaged value.

EAR is derived from six 2D landmarks per eye (pixel space):

    EAR = (dist(p2, p6) + dist(p3, p5)) / (2 * dist(p1, p4))

with ``p1``/``p4`` the horizontal eye corners and ``p2``/``p3`` the upper lid,
``p5``/``p6`` the lower lid. EAR drops when the eye closes.

All thresholds are module-level constants that default to the specification
values and may be overridden by callers.

Owned by: telemetry agent.
"""

import math

import numpy as np

# ---------------------------------------------------------------------------
# Configurable thresholds (defaults per specification)
# ---------------------------------------------------------------------------
EAR_THRESHOLD = 0.22
EAR_EMA_ALPHA = 0.15

# Eye landmark indices per specification.
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Anything at or below this magnitude is treated as a degenerate eye and the
# EAR is reported as None (avoids division by zero / unstable ratios).
_MIN_CORNER_DISTANCE = 1e-6


def _point(landmarks_px: np.ndarray, idx: int):
    """Return the (x, y) pair for landmark ``idx`` or None if invalid.

    A point is invalid if the index is out of range or the coordinates are
    non-finite (NaN/inf), which can happen when landmarks are missing.
    """
    if idx < 0 or idx >= len(landmarks_px):
        return None
    x = landmarks_px[idx, 0]
    y = landmarks_px[idx, 1]
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    return float(x), float(y)


def _euclid2d(a, b) -> float:
    """2D Euclidean distance in pixel space."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def eye_aspect_ratio(landmarks_px, eye_indices):
    """Compute EAR for one eye from six landmark indices.

    Args:
        landmarks_px: array-like of (N, 2) pixel coordinates, or None.
        eye_indices: iterable of exactly six landmark indices
                     (p1, p2, p3, p4, p5, p6).

    Returns:
        float EAR, or None if landmarks are missing/invalid or the eye is
        degenerate (corner distance ~ 0) -- never raises, never divides
        by zero.
    """
    if landmarks_px is None or eye_indices is None:
        return None

    try:
        pts = np.asarray(landmarks_px, dtype=np.float64)
    except (ValueError, TypeError):
        return None
    if pts.ndim != 2 or pts.shape[1] < 2:
        return None

    eye = list(eye_indices)
    if len(eye) < 6:
        return None

    p = []
    for idx in eye:
        pt = _point(pts, idx)
        if pt is None:
            return None
        p.append(pt)

    corner_dist = _euclid2d(p[0], p[3])  # distance(p1, p4)
    if corner_dist <= _MIN_CORNER_DISTANCE:
        return None  # degenerate eye; avoid division by zero

    vertical = _euclid2d(p[1], p[5]) + _euclid2d(p[2], p[4])
    return vertical / (2.0 * corner_dist)


def compute_ear(landmarks_px):
    """Compute left, right and averaged EAR.

    Args:
        landmarks_px: array-like of (N, 2) pixel coordinates, or None.

    Returns:
        (ear_l, ear_r, ear_avg) tuple of floats.
        - (None, None, None) when ``landmarks_px`` is None.
        - If an individual eye is missing/invalid, its EAR is None and
          ``ear_avg`` is None too: telemetry is never fabricated from
          partial data.
    """
    if landmarks_px is None:
        return None, None, None

    ear_l = eye_aspect_ratio(landmarks_px, LEFT_EYE)
    ear_r = eye_aspect_ratio(landmarks_px, RIGHT_EYE)
    if ear_l is None or ear_r is None:
        return ear_l, ear_r, None
    return ear_l, ear_r, (ear_l + ear_r) / 2.0


class EARSmoother:
    """Exponential moving average (EMA) over per-frame EAR values.

    ``smoothed = alpha * raw + (1 - alpha) * previous_smoothed``

    With no previous value the smoothed value equals the raw value.
    """

    def __init__(self, alpha: float = EAR_EMA_ALPHA):
        self.alpha = float(alpha)
        self._smoothed = None

    @property
    def value(self):
        """Most recent smoothed value, or None before the first update."""
        return self._smoothed

    def update(self, ear_value):
        """Feed one raw EAR value (may be None for missing landmarks).

        Returns the new smoothed value; None updates pass through without
        changing state and return the previous smoothed value.
        """
        if ear_value is None:
            return self._smoothed
        if self._smoothed is None:
            self._smoothed = float(ear_value)
        else:
            self._smoothed = (
                self.alpha * float(ear_value)
                + (1.0 - self.alpha) * self._smoothed
            )
        return self._smoothed

    def reset(self):
        """Forget the history; the next update seeds from its raw value."""
        self._smoothed = None
