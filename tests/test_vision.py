"""Tests for the vision layer (MediaPipe FaceMesh landmark extraction).

Owned by: vision agent.

No physical camera is required. Deterministic tests use synthetic landmark
geometry and a blank frame for the no-face path. If MediaPipe is not installed
in the test environment, the detector-import surface is skipped via
``pytest.importorskip``.
"""

import numpy as np
import pytest

mp = pytest.importorskip("mediapipe")  # skip whole module when mediapipe absent

from src.vision import (  # noqa: E402  (after importorskip guard)
    HEAD_MODEL_POINT_IDS,
    LEFT_EYE,
    RIGHT_EYE,
    FaceMeshDetector,
    FaceMeshResult,
    classify_face_presence,
)
from src.vision.detector import _landmark_quality, _normalized_to_pixel  # noqa: E402
from src.vision.landmarks import (  # noqa: E402
    CHIN,
    LEFT_EYE_OUTER,
    LEFT_IRIS,
    LEFT_MOUTH_CORNER,
    NOSE_TIP,
    RIGHT_EYE_OUTER,
    RIGHT_IRIS,
    RIGHT_MOUTH_CORNER,
)

# ---------------------------------------------------------------------------
# Landmark constants
# ---------------------------------------------------------------------------


def test_landmark_constant_lengths():
    assert len(LEFT_EYE) == 6
    assert len(RIGHT_EYE) == 6
    assert len(HEAD_MODEL_POINT_IDS) == 6


def test_left_eye_exact_indices():
    assert LEFT_EYE == [33, 160, 158, 133, 153, 144]


def test_right_eye_exact_indices():
    assert RIGHT_EYE == [362, 385, 387, 263, 373, 380]


def test_anchor_constants_exact_values():
    assert LEFT_EYE_OUTER == 33
    assert RIGHT_EYE_OUTER == 263
    assert NOSE_TIP == 1
    assert CHIN == 152
    assert LEFT_MOUTH_CORNER == 61
    assert RIGHT_MOUTH_CORNER == 291


def test_iris_constants():
    assert LEFT_IRIS == 468
    assert RIGHT_IRIS == 473


def test_head_model_point_ids_exact_values():
    assert HEAD_MODEL_POINT_IDS == [1, 152, 33, 263, 61, 291]


# ---------------------------------------------------------------------------
# classify_face_presence
# ---------------------------------------------------------------------------


def _result(face_present, quality=1.0, landmarks=None):
    return FaceMeshResult(
        face_present=face_present,
        landmarks_px=landmarks,
        normalized_landmarks=None,
        frame_size=(640, 480),
        landmark_quality=quality,
    )


def test_classify_none_is_no_face():
    assert classify_face_presence(None) == "NO_FACE"


def test_classify_missing_face_is_no_face():
    assert classify_face_presence(_result(face_present=False)) == "NO_FACE"


def test_classify_low_quality_is_degraded():
    assert classify_face_presence(_result(True, quality=0.1)) == "DEGRADED"
    assert classify_face_presence(_result(True, quality=0.34)) == "DEGRADED"


def test_classify_good_face_is_locked():
    assert classify_face_presence(_result(True, quality=0.9)) == "LOCKED"


def test_classify_boundary_quality_is_locked():
    assert classify_face_presence(_result(True, quality=0.35)) == "LOCKED"


def test_classify_non_numeric_quality_is_degraded():
    assert classify_face_presence(_result(True, quality=None)) == "DEGRADED"


# ---------------------------------------------------------------------------
# FaceMeshDetector construction / lifecycle
# ---------------------------------------------------------------------------


def test_detector_instantiation_with_defaults():
    detector = FaceMeshDetector()
    try:
        assert detector._face_mesh is not None
    finally:
        detector.close()


def test_detector_instantiation_with_config_group():
    config = {
        "face_mesh": {
            "max_num_faces": 1,
            "min_detection_confidence": 0.6,
            "min_tracking_confidence": 0.6,
        }
    }
    detector = FaceMeshDetector(config)
    detector.close()


def test_detector_close_is_idempotent():
    detector = FaceMeshDetector({})
    detector.close()
    detector.close()  # must not raise


def test_detector_context_manager():
    with FaceMeshDetector({}) as detector:
        assert detector._face_mesh is not None


def test_detector_detect_none_frame():
    detector = FaceMeshDetector({})
    try:
        result = detector.detect(None)
        assert result.face_present is False
        assert result.landmarks_px is None
        assert result.normalized_landmarks is None
        assert result.landmark_quality == 0.0
    finally:
        detector.close()


def test_detector_detect_garbage_input_does_not_crash():
    detector = FaceMeshDetector({})
    try:
        result = detector.detect([1, 2, 3])  # not an image
        assert result.face_present is False
        assert result.landmarks_px is None
    finally:
        detector.close()


# ---------------------------------------------------------------------------
# No-face path on a real blank frame (no physical camera needed)
# ---------------------------------------------------------------------------


def test_detector_blank_frame_returns_no_face():
    detector = FaceMeshDetector({})
    try:
        blank = np.zeros((240, 320, 3), dtype=np.uint8)
        result = detector.detect(blank)

        assert isinstance(result, FaceMeshResult)
        assert result.face_present is False
        assert result.landmarks_px is None
        assert result.normalized_landmarks is None
        assert result.frame_size == (320, 240)
        assert result.landmark_quality == 0.0
    finally:
        detector.close()


# ---------------------------------------------------------------------------
# Face-present path (deterministic, injected MediaPipe result)
# ---------------------------------------------------------------------------


class _FakeLandmark:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)


class _FakeFaceLandmarks:
    def __init__(self, landmarks):
        self.landmark = landmarks


class _FakeMeshResult:
    def __init__(self, landmarks):
        self.multi_face_landmarks = [_FakeFaceLandmarks(landmarks)]


class _FakeFaceMesh:
    def __init__(self, result):
        self._result = result

    def process(self, frame):
        return self._result

    def close(self):
        pass


def _synthetic_mesh(n=478, frame=(640, 480), inter_eye=48.0, eye_width=12.0,
                    eye_open=6.0):
    """Build a geometrically sane synthetic FaceMesh point set.

    Required landmark indices are placed at plausible relative positions; the
    remaining points are scattered uniformly inside the frame.
    """
    width, height = frame
    rng = np.random.default_rng(0)
    points = rng.uniform(0, [width, height], size=(n, 2)).astype(np.float32)

    cy = height * 0.4
    left_cx = width / 2 - inter_eye / 2
    right_cx = width / 2 + inter_eye / 2

    # Eye corners.
    points[33] = [left_cx - eye_width / 2, cy]   # left outer
    points[133] = [left_cx + eye_width / 2, cy]  # left inner
    points[362] = [right_cx - eye_width / 2, cy]  # right inner
    points[263] = [right_cx + eye_width / 2, cy]  # right outer

    # Eye lid verticals (EAR-style distances must be positive).
    points[160] = [left_cx, cy - eye_open / 2]
    points[144] = [left_cx, cy + eye_open / 2]
    points[158] = [left_cx - 1.0, cy - eye_open / 2]
    points[153] = [left_cx - 1.0, cy + eye_open / 2]
    points[385] = [right_cx, cy - eye_open / 2]
    points[380] = [right_cx, cy + eye_open / 2]
    points[387] = [right_cx + 1.0, cy - eye_open / 2]
    points[373] = [right_cx + 1.0, cy + eye_open / 2]

    # Anchors.
    points[NOSE_TIP] = [width / 2, cy + 10.0]
    points[CHIN] = [width / 2, height * 0.75]
    points[LEFT_MOUTH_CORNER] = [width / 2 - 20.0, height * 0.65]
    points[RIGHT_MOUTH_CORNER] = [width / 2 + 20.0, height * 0.65]

    return points


def test_detect_face_present_returns_pixel_space_array():
    detector = FaceMeshDetector({})
    try:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        points = _synthetic_mesh(frame=(640, 480))
        normalized = points / np.array([640.0, 480.0], dtype=np.float32)
        detector._face_mesh = _FakeFaceMesh(
            _FakeMeshResult([_FakeLandmark(x, y) for x, y in normalized])
        )

        result = detector.detect(frame)

        assert isinstance(result, FaceMeshResult)
        assert result.face_present is True
        assert result.landmarks_px is not None
        assert result.landmarks_px.shape == (478, 2)
        assert result.landmarks_px.dtype == np.float32
        assert result.normalized_landmarks is not None
        assert result.frame_size == (640, 480)
        # Pixel space: coordinates scaled into the frame, not normalized.
        assert np.allclose(result.landmarks_px, points.astype(np.float32), atol=1e-3)
        assert result.landmarks_px[:, 0].min() >= 0.0
        assert result.landmarks_px[:, 0].max() <= 640.0
        assert result.landmarks_px[:, 1].min() >= 0.0
        assert result.landmarks_px[:, 1].max() <= 480.0
    finally:
        detector.close()


def test_normalized_to_pixel_scales_by_frame_size():
    landmarks = [_FakeLandmark(x, y) for x, y in ((0.5, 0.25), (1.0, 1.0))]
    points_px = _normalized_to_pixel(landmarks, (1280, 720))

    assert points_px.shape == (2, 2)
    assert points_px[0, 0] == 640.0   # 0.5 * 1280
    assert points_px[0, 1] == 180.0   # 0.25 * 720
    assert points_px[1, 0] == 1280.0
    assert points_px[1, 1] == 720.0


# ---------------------------------------------------------------------------
# landmark_quality heuristic
# ---------------------------------------------------------------------------


def test_quality_high_for_sane_face():
    points = _synthetic_mesh()
    quality = _landmark_quality(points, (640, 480))
    assert 0.9 <= quality <= 1.0


def test_quality_zero_for_none_and_degenerate_inputs():
    assert _landmark_quality(None, (640, 480)) == 0.0
    assert _landmark_quality(np.zeros((10, 2), dtype=np.float32), (640, 480)) == 0.0
    assert _landmark_quality(np.zeros((478, 3), dtype=np.float32), (640, 480)) == 0.0
    assert _landmark_quality(np.zeros((478, 2), dtype=np.float32), None) == 0.0


def test_quality_zero_for_collapsed_eye_geometry():
    points = _synthetic_mesh()
    points[33] = points[133]  # left eye width collapses to zero
    assert _landmark_quality(points, (640, 480)) == 0.0


def test_quality_zero_for_tiny_face():
    points = _synthetic_mesh(inter_eye=2.0, eye_width=0.6, eye_open=0.4)
    assert _landmark_quality(points, (640, 480)) == 0.0


def test_quality_zero_for_non_finite_coordinates():
    points = _synthetic_mesh()
    points[CHIN] = [np.nan, np.nan]
    assert _landmark_quality(points, (640, 480)) == 0.0


def test_quality_zero_for_too_few_landmarks():
    points = np.zeros((50, 2), dtype=np.float32)
    assert _landmark_quality(points, (640, 480)) == 0.0


# ---------------------------------------------------------------------------
# Public API exports
# ---------------------------------------------------------------------------


def test_vision_package_exports():
    from src.vision import (
        HEAD_MODEL_POINT_IDS as exported_head,
        LEFT_EYE as exported_left,
        RIGHT_EYE as exported_right,
        classify_face_presence as exported_classify,
    )

    assert exported_left == LEFT_EYE
    assert exported_right == RIGHT_EYE
    assert exported_head == HEAD_MODEL_POINT_IDS
    assert callable(exported_classify)
    assert exported_classify(None) == "NO_FACE"
