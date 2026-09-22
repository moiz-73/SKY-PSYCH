"""SkyPsych - vision subpackage (MediaPipe FaceMesh).

Owned by: vision agent.

Public surface of the vision layer:

* :class:`FaceMeshDetector` — MediaPipe FaceMesh wrapper producing
  pixel-space landmarks per frame.
* :class:`FaceMeshResult` — per-frame extraction result (explicit no-face
  support; landmarks never fabricated).
* :func:`classify_face_presence` — preliminary LOCKED / DEGRADED / NO_FACE
  coverage classification.
* Landmark index constants (``LEFT_EYE``, ``RIGHT_EYE``,
  ``HEAD_MODEL_POINT_IDS``, ...) from :mod:`src.vision.landmarks`.

No raw frames are stored, no images are written, and nothing in this package
touches the network.
"""

from src.vision.landmarks import (
    HEAD_MODEL_POINT_IDS,
    LEFT_EYE,
    LEFT_EYE_OUTER,
    LEFT_IRIS,
    LEFT_MOUTH_CORNER,
    NOSE_TIP,
    RIGHT_EYE,
    RIGHT_EYE_OUTER,
    RIGHT_IRIS,
    RIGHT_MOUTH_CORNER,
    CHIN,
)
from src.vision.occluder import (
    classify_face_presence,
    classify_coverage,
    is_pose_valid,
)
from src.vision.detector import FaceMeshDetector, FaceMeshResult

__all__ = [
    "FaceMeshDetector",
    "FaceMeshResult",
    "classify_face_presence",
    "classify_coverage",
    "is_pose_valid",
    "LEFT_EYE",
    "RIGHT_EYE",
    "HEAD_MODEL_POINT_IDS",
    "LEFT_EYE_OUTER",
    "RIGHT_EYE_OUTER",
    "NOSE_TIP",
    "CHIN",
    "LEFT_MOUTH_CORNER",
    "RIGHT_MOUTH_CORNER",
    "LEFT_IRIS",
    "RIGHT_IRIS",
]
