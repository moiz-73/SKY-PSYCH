"""Face landmark indexes for MediaPipe FaceMesh extraction.

Owned by: vision agent.

These constants are the stable contract that the telemetry layer (EAR, PERCLOS,
blinks, head pose, coverage) reads from. They reference the canonical MediaPipe
FaceMesh/CanonicalFaceLandmarker indices. With ``refine_landmarks=True``
MediaPipe returns 478 landmarks; without it returns 468. The iris indexes
(LEFT_IRIS/RIGHT_IRIS) only exist in the 478-landmark refined output.

This module is pure data: it has no dependency on MediaPipe, NumPy, or the
camera, so it can be imported even where MediaPipe is not installed.
"""

# Eye landmark polygons (EAR). Each list is the 6 canonical FaceMesh points
# used by the EAR / blink / PERCLOS downstream stages (outer, upper, lower,
# inner corners plus upper/lower lid midpoints).
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Single-point anchors used for head pose and geometry.
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263
NOSE_TIP = 1
CHIN = 152
LEFT_MOUTH_CORNER = 61
RIGHT_MOUTH_CORNER = 291

# Iris centers (only present in the 478-landmark refined mesh output).
LEFT_IRIS = 468
RIGHT_IRIS = 473

# Sparse 3D model point ids used by the head-pose (solvePnP) stage.
HEAD_MODEL_POINT_IDS = [
    NOSE_TIP,
    CHIN,
    LEFT_EYE_OUTER,
    RIGHT_EYE_OUTER,
    LEFT_MOUTH_CORNER,
    RIGHT_MOUTH_CORNER,
]