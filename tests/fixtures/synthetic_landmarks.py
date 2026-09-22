"""Synthetic landmark generators for deterministic unit tests.

Produces NumPy arrays with at least 468 rows and 2 columns (pixel-space x, y),
matching the MediaPipe-style face-mesh landmark layout used by SkyPsych AI.

Eye geometry follows the EAR definition used by ``src/telemetry/ear.py``:

    ear = (dist(p2, p6) + dist(p3, p5)) / (2 * dist(p1, p4))

where ``p1``/``p4`` are the horizontal eye corners and ``p2``/``p3`` are the
upper lid, ``p5``/``p6`` the lower lid. With corners separated by ``2*W`` and
lid rise/fall by ``H``, this yields ``ear = H / W`` exactly, so callers can
request a precise EAR by choosing ``H``.

Default geometry (W = 30 px):
    * open eye   (H = 9.0)  -> EAR ~= 0.30  (spec: 0.25-0.33)
    * closed eye (H = 1.5)  -> EAR ~= 0.05  (spec: below 0.15)

Owned by: telemetry agent.
"""

import numpy as np

# Number of face-mesh landmarks. >= 468 as required by the specification.
NUM_LANDMARKS = 478

# Eye landmark indices per the specification.
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Eye geometry (pixel units).
_HALF_WIDTH = 30.0            # W: half the corner-to-corner eye width
_LID_OPEN = 9.0               # H: lid opening for an open eye   -> EAR 0.30
_LID_CLOSED = 1.5             # H: lid residual for a closed eye -> EAR 0.05

# Face oval anchor (landmarks not otherwise configured sit on this oval).
_FACE_CENTER = (320.0, 360.0)
_FACE_RADII = (180.0, 230.0)

# Left / right eye centers.
_LEFT_EYE_CENTER = (235.0, 300.0)
_RIGHT_EYE_CENTER = (415.0, 300.0)


def _base_face() -> np.ndarray:
    """Return a (NUM_LANDMARKS, 2) float array with an oval face outline."""
    angles = np.linspace(0.0, 2.0 * np.pi, NUM_LANDMARKS, endpoint=False)
    xs = _FACE_CENTER[0] + _FACE_RADII[0] * np.cos(angles)
    ys = _FACE_CENTER[1] + _FACE_RADII[1] * np.sin(angles)
    return np.column_stack([xs, ys])


def _apply_eye(landmarks: np.ndarray, eye_indices, center, lid_h: float) -> None:
    """Write the six eye-landmark positions for one eye in place.

    ``p1`` (index ``eye_indices[0]``) is the outer/left corner, ``p4``
    (``eye_indices[3]``) is the inner/right corner. Lid points are placed
    symmetrically so ``ear == lid_h / _HALF_WIDTH``.
    """
    cx, cy = center
    w = _HALF_WIDTH
    h = lid_h

    # p1 (index 0) -> left corner
    landmarks[eye_indices[0], 0] = cx - w
    landmarks[eye_indices[0], 1] = cy
    # p4 (index 3) -> right corner
    landmarks[eye_indices[3], 0] = cx + w
    landmarks[eye_indices[3], 1] = cy
    # upper lid: p2 (index 1), p3 (index 2)
    landmarks[eye_indices[1], 0] = cx - w / 2.0
    landmarks[eye_indices[1], 1] = cy - h
    landmarks[eye_indices[2], 0] = cx + w / 2.0
    landmarks[eye_indices[2], 1] = cy - h
    # lower lid: p5 (index 4), p6 (index 5)
    landmarks[eye_indices[4], 0] = cx + w / 2.0
    landmarks[eye_indices[4], 1] = cy + h
    landmarks[eye_indices[5], 0] = cx - w / 2.0
    landmarks[eye_indices[5], 1] = cy + h


def make_landmarks(left_lid: float = _LID_OPEN, right_lid: float = _LID_OPEN):
    """Build a (NUM_LANDMARKS, 2) landmark array with both eyes set to the
    given lid heights."""
    lm = _base_face()
    _apply_eye(lm, LEFT_EYE, _LEFT_EYE_CENTER, left_lid)
    _apply_eye(lm, RIGHT_EYE, _RIGHT_EYE_CENTER, right_lid)
    return lm


def make_landmarks_eye_open():
    """Landmarks with both eyes fully open (EAR ~= 0.30)."""
    return make_landmarks(_LID_OPEN, _LID_OPEN)


def make_landmarks_eye_closed():
    """Landmarks with both eyes closed (EAR ~= 0.05)."""
    return make_landmarks(_LID_CLOSED, _LID_CLOSED)


def make_landmarks_left_closed():
    """Landmarks with the left eye closed, right eye open."""
    return make_landmarks(_LID_CLOSED, _LID_OPEN)


def make_landmarks_right_closed():
    """Landmarks with the right eye closed, left eye open."""
    return make_landmarks(_LID_OPEN, _LID_CLOSED)


def set_eye_lids(landmarks, left_lid: float = None, right_lid: float = None):
    """Return a copy of ``landmarks`` with one/both eyelid heights overridden.

    ``None`` leaves that eye unchanged. Useful for building closure sequences.
    """
    out = landmarks.copy()
    if left_lid is not None:
        _apply_eye(out, LEFT_EYE, _LEFT_EYE_CENTER, left_lid)
    if right_lid is not None:
        _apply_eye(out, RIGHT_EYE, _RIGHT_EYE_CENTER, right_lid)
    return out