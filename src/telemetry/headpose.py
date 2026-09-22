"""Head pose estimation and head-deviation tracking.

Estimates the operator's head pitch / yaw / roll (degrees) from six
face-mesh landmarks using Perspective-n-Point (``cv2.solvePnP``) with a
canonical 3D face model (millimetres) and approximate camera intrinsics
derived from the frame size. Also provides a timestamp-windowed
``HeadDeviationTracker`` that computes the fraction of time in a rolling
window during which the head was turned away from neutral.

Safety contract
---------------
* Never fabricate normal values: if pose estimation fails (invalid
  landmarks, non-finite points, ``solvePnP`` failure, NaN output), return
  ``None`` angles so callers can classify coverage as DEGRADED / NO_FACE.
* All rolling windows are timestamp based, never frame-count based.

Owned by: telemetry agent.
"""

import math
from collections import deque

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Landmark IDs (official MediaPipe face-mesh indices)
# ---------------------------------------------------------------------------
try:
    from src.vision.landmarks import (  # type: ignore[import-not-found]
        NOSE_TIP,
        CHIN,
        LEFT_EYE_OUTER,
        RIGHT_EYE_OUTER,
        LEFT_MOUTH_CORNER,
        RIGHT_MOUTH_CORNER,
        HEAD_MODEL_POINT_IDS,
    )
except (ImportError, AttributeError):
    # The vision agent's landmarks.py is still a stub; keep the official values.
    NOSE_TIP = 1
    CHIN = 152
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_OUTER = 263
    LEFT_MOUTH_CORNER = 61
    RIGHT_MOUTH_CORNER = 291

    HEAD_MODEL_POINT_IDS = [
        NOSE_TIP,
        CHIN,
        LEFT_EYE_OUTER,
        RIGHT_EYE_OUTER,
        LEFT_MOUTH_CORNER,
        RIGHT_MOUTH_CORNER,
    ]

# ---------------------------------------------------------------------------
# Canonical 3D face model (millimetres). Row order matches HEAD_MODEL_POINT_IDS:
# nose tip, chin, left eye outer, right eye outer, left mouth, right mouth.
# z is positive away from the camera.
# ---------------------------------------------------------------------------
HEAD_MODEL_3D = np.array(
    [
        [0.0, 0.0, 0.0],        # nose tip
        [0.0, -63.6, -12.5],    # chin
        [-43.3, 32.7, -26.0],   # left eye outer
        [43.3, 32.7, -26.0],    # right eye outer
        [-28.9, -28.9, -24.1],  # left mouth corner
        [28.9, -28.9, -24.1],   # right mouth corner
    ],
    dtype=np.float64,
)

# Default deviation thresholds (degrees) and window length (seconds).
DEFAULT_WINDOW_SECONDS = 30.0
DEFAULT_PITCH_LIMIT_DEG = 20.0
DEFAULT_YAW_LIMIT_DEG = 25.0


def _normalize_angle_deg(angle_deg):
    """Wrap an angle in degrees into the range [-180, 180)."""
    return ((float(angle_deg) + 180.0) % 360.0) - 180.0


def _camera_matrix(frame_width, frame_height):
    """Approximate camera intrinsics derived from the frame size."""
    w = float(frame_width)
    h = float(frame_height)
    return np.array(
        [
            [w, 0.0, w / 2.0],
            [0.0, w, h / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def estimate_head_pose(landmarks_px, frame_width, frame_height):
    """Estimate head pitch / yaw / roll in degrees from six 2D landmarks.

    Parameters
    ----------
    landmarks_px : array-like of (N, 2) pixel coordinates (face-mesh layout)
    frame_width, frame_height : int or float, frame dimensions in pixels

    Returns
    -------
    (pitch, yaw, roll) in degrees, or (None, None, None) if estimation fails.
    Never returns NaN values.
    """
    if landmarks_px is None:
        return None, None, None

    # --- Validate frame size -------------------------------------------------
    try:
        w = float(frame_width)
        h = float(frame_height)
    except (TypeError, ValueError):
        return None, None, None
    if not (math.isfinite(w) and math.isfinite(h)) or w <= 0.0 or h <= 0.0:
        return None, None, None

    # --- Extract the six 2D image points -------------------------------------
    try:
        pts = np.asarray(landmarks_px, dtype=np.float64)
    except (TypeError, ValueError):
        return None, None, None
    if pts.ndim != 2 or pts.shape[1] < 2:
        return None, None, None

    image_points = np.empty((len(HEAD_MODEL_POINT_IDS), 2), dtype=np.float64)
    for i, idx in enumerate(HEAD_MODEL_POINT_IDS):
        if int(idx) >= pts.shape[0]:
            return None, None, None
        x = float(pts[int(idx), 0])
        y = float(pts[int(idx), 1])
        if not (math.isfinite(x) and math.isfinite(y)):
            return None, None, None
        image_points[i, 0] = x
        image_points[i, 1] = y

    # --- Reject points that are wildly out of bounds --------------------------
    # Generous margin (a couple of frame widths) so near-edge landmarks survive
    # while garbage coordinates (e.g. 1e9) are rejected.
    min_x, max_x = -2.0 * w, w + 2.0 * w
    min_y, max_y = -2.0 * h, h + 2.0 * h
    if (
        np.any(image_points[:, 0] < min_x)
        or np.any(image_points[:, 0] > max_x)
        or np.any(image_points[:, 1] < min_y)
        or np.any(image_points[:, 1] > max_y)
    ):
        return None, None, None

    # --- solvePnP -------------------------------------------------------------
    camera_matrix = _camera_matrix(w, h)
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)
    try:
        ret, rvec, _tvec = cv2.solvePnP(
            HEAD_MODEL_3D, image_points, camera_matrix, dist_coeffs
        )
        if not ret or rvec is None:
            return None, None, None
        rotation_matrix, _ = cv2.Rodrigues(rvec)
        R = np.asarray(rotation_matrix, dtype=np.float64)
    except cv2.error:
        # Degenerate inputs (e.g. all points identical) raise inside OpenCV.
        return None, None, None
    except Exception:
        return None, None, None

    # --- Euler angle extraction (radians) -------------------------------------
    pitch = math.atan2(-R[1][2], R[2][2])
    yaw = math.asin(max(-1.0, min(1.0, R[0][2])))
    roll = math.atan2(-R[0][1], R[0][0])

    pitch_deg = _normalize_angle_deg(math.degrees(pitch))
    yaw_deg = _normalize_angle_deg(math.degrees(yaw))
    roll_deg = _normalize_angle_deg(math.degrees(roll))

    for angle in (pitch_deg, yaw_deg, roll_deg):
        if not math.isfinite(angle):
            return None, None, None

    return pitch_deg, yaw_deg, roll_deg


class HeadDeviationTracker:
    """Timestamp-windowed fraction of time the head was turned away.

    A sample is HEAD_OFF when ``abs(pitch) > pitch_limit_deg`` or
    ``abs(yaw) > yaw_limit_deg``. ``update`` stores ``(t, head_off)`` in a
    deque, prunes samples older than ``t - window_seconds`` and ``value()``
    integrates the head-off state over time (piecewise-constant), returning a
    float in ``[0.0, 1.0]``. Invalid (None/NaN) angles are skipped and never
    treated as normal.
    """

    def __init__(self, window_seconds=30.0, pitch_limit_deg=20.0, yaw_limit_deg=25.0):
        self.window_seconds = float(window_seconds)
        self.pitch_limit_deg = float(pitch_limit_deg)
        self.yaw_limit_deg = float(yaw_limit_deg)
        self._samples = deque()
        self._last_t = None

    def update(self, pitch, yaw, t):
        """Record a pose sample at timestamp ``t`` (monotonic seconds)."""
        if pitch is None or yaw is None:
            return  # skip invalid frames; never treat missing data as normal
        if not (math.isfinite(pitch) and math.isfinite(yaw)):
            return
        t = float(t)
        head_off = (
            abs(pitch) > self.pitch_limit_deg
            or abs(yaw) > self.yaw_limit_deg
        )
        self._samples.append((t, bool(head_off)))
        self._last_t = t
        self._prune(t)

    def _prune(self, t):
        cutoff = float(t) - self.window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def value(self):
        """Return the time-integrated HEAD_DEV_FRACTION over the window."""
        if self._last_t is not None:
            self._prune(self._last_t)
        if not self._samples:
            return 0.0
        now = self._samples[-1][0]
        window_start = now - self.window_seconds
        off_time = 0.0
        total_time = 0.0
        for i, (t0, head_off) in enumerate(self._samples):
            t1 = self._samples[i + 1][0] if i + 1 < len(self._samples) else now
            a = max(t0, window_start)
            b = min(t1, now)
            if b > a:
                total_time += b - a
                if head_off:
                    off_time += b - a
        if total_time <= 0.0:
            return 0.0
        return min(1.0, off_time / total_time)

    def reset(self):
        """Clear all stored samples."""
        self._samples.clear()
        self._last_t = None
