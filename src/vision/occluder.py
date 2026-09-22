"""Occlusion / coverage handling for the vision layer.

Owned by: vision agent.

Preliminary coverage classification: maps a :class:`FaceMeshResult` to one of
the shared coverage states (``LOCKED`` / ``DEGRADED`` / ``NO_FACE``) that the
fusion layer consumes. This is intentionally minimal — a later agent may refine
it (e.g. persistent dropout, occlusion heuristics).

Critical invariant: the system never reports a normal (``LOCKED``) state when
no face is present.
"""

import math

# FaceMesh results with quality below this threshold are DEGRADED.
DEGRADED_QUALITY_THRESHOLD = 0.35

# Shared coverage states (see src/telemetry/__init__.py).
NO_FACE = "NO_FACE"
DEGRADED = "DEGRADED"
LOCKED = "LOCKED"

# Head-pose angles beyond this magnitude are physically absurd and must be
# rejected (|pitch|/|yaw|/|roll| of a human head stays well under 90 deg).
ABSURD_ANGLE_LIMIT_DEG = 90.0


def classify_face_presence(face_result):
    """Classify a FaceMeshResult into LOCKED / DEGRADED / NO_FACE.

    Parameters
    ----------
    face_result : FaceMeshResult or None
        Output of ``FaceMeshDetector.detect`` (or None when the caller could
        not produce one at all).

    Returns
    -------
    str
        ``"NO_FACE"`` when the result is None or no face was detected,
        ``"DEGRADED"`` when the face is present but landmark quality is below
        the threshold, otherwise ``"LOCKED"``.
    """
    if face_result is None:
        return NO_FACE
    if not face_result.face_present:
        return NO_FACE
    try:
        quality = float(face_result.landmark_quality)
    except (TypeError, ValueError):
        return DEGRADED
    if quality < DEGRADED_QUALITY_THRESHOLD:
        return DEGRADED
    return LOCKED


def is_pose_valid(pitch, yaw, roll) -> bool:
    """Return True only when all three pose angles are usable.

    Rejects ``None``, non-numeric values, NaN/Inf, and magnitudes beyond
    :data:`ABSURD_ANGLE_LIMIT_DEG` (a human head never exceeds ~90 degrees of
    pitch/yaw/roll). Invalid angles must never be treated as normal pose.
    """
    for angle in (pitch, yaw, roll):
        if angle is None:
            return False
        try:
            value = float(angle)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(value):
            return False
        if abs(value) > ABSURD_ANGLE_LIMIT_DEG:
            return False
    return True


def classify_coverage(face_present, landmark_quality, pose_valid) -> str:
    """Classify overall coverage from face presence, quality, and pose validity.

    Parameters
    ----------
    face_present : bool
        Whether a face was detected this frame.
    landmark_quality : float or None
        FaceMesh landmark quality in [0.0, 1.0] (None -> DEGRADED).
    pose_valid : bool
        Whether head-pose angles were valid (see :func:`is_pose_valid`).

    Returns
    -------
    str
        ``"NO_FACE"`` when no face is present (dominates everything else),
        ``"DEGRADED"`` when quality is low/missing or pose is invalid,
        otherwise ``"LOCKED"``.
    """
    if not face_present:
        return NO_FACE
    if landmark_quality is None:
        return DEGRADED
    try:
        quality = float(landmark_quality)
    except (TypeError, ValueError):
        return DEGRADED
    if quality < DEGRADED_QUALITY_THRESHOLD:
        return DEGRADED
    if not pose_valid:
        return DEGRADED
    return LOCKED
