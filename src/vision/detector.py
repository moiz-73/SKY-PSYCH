"""MediaPipe FaceMesh landmark extraction with graceful no-face handling.

Owned by: vision agent.

Extracts 468/478 facial landmarks per frame in pixel space. The module:

* runs **only** MediaPipe FaceMesh (no other ML model),
* works fully locally — no cloud, no network egress,
* never persists frames and never writes image files,
* returns an explicit ``face_present=False`` result when no face is found
  (robust to face entry/exit and to MediaPipe runtime errors),
* runs in single-face mode for the MVP.

If MediaPipe is not installed this module raises a clear ``ImportError`` at
import time so failures are obvious instead of cryptic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.vision.landmarks import (
    CHIN,
    LEFT_EYE_OUTER,
    LEFT_MOUTH_CORNER,
    NOSE_TIP,
    RIGHT_EYE_OUTER,
    RIGHT_MOUTH_CORNER,
)

try:
    import mediapipe as _mp
    from mediapipe.python.solutions import face_mesh as _face_mesh_mod
except ImportError as _import_error:  # pragma: no cover - exercised in envs w/o mp
    raise ImportError(
        "MediaPipe is required by FaceMeshDetector (src/vision/detector.py). "
        "Install it with `pip install mediapipe` (see requirements.txt). "
        "Note: use a 0.10.x release — mediapipe 1.0 removed the "
        "mediapipe.python.solutions API this module relies on."
    ) from _import_error

# --- safe internal defaults (config file is optional) ---------------------
_DEFAULT_MAX_NUM_FACES = 1
_DEFAULT_MIN_DETECTION_CONFIDENCE = 0.5
_DEFAULT_MIN_TRACKING_CONFIDENCE = 0.5
_DEFAULT_REFINE_LANDMARKS = True
# Ingestion feeds OpenCV BGR frames; FaceMesh expects RGB.
_DEFAULT_FRAME_IS_BGR = True

# Quality heuristic: below this the face is considered DEGRADED (see occluder).
MIN_LANDMARK_QUALITY_LOCKED = 0.35
# A real FaceMesh output has >= 468 points; anything far below that is unusable.
_MIN_TRUSTED_LANDMARK_COUNT = 300
# Faces whose inter-eye span is below this fraction of the frame min-dimension
# are treated as too small to trust (face far away / not really there).
_MIN_INTER_EYE_FRAME_FRACTION = 0.015


@dataclass
class FaceMeshResult:
    """Landmark extraction result for one frame.

    Attributes
    ----------
    face_present:
        True only when MediaPipe returned a face this frame. The system must
        never treat a missing face as a normal reading.
    landmarks_px:
        (N, 2) float32 array of pixel-space landmarks (N is 468 or 478), or
        ``None`` when no face is present.
    normalized_landmarks:
        Raw MediaPipe normalized (0..1) landmark list, or ``None``.
    frame_size:
        ``(width, height)`` of the frame the result was computed from.
    landmark_quality:
        Simple heuristic in [0.0, 1.0] scoring landmark validity (finite
        coordinates, positive eye geometry, sane inter-eye span, in-frame).
    """

    face_present: bool
    landmarks_px: Optional[np.ndarray]
    normalized_landmarks: Optional[list]
    frame_size: tuple
    landmark_quality: float


def _face_mesh_settings(config) -> dict:
    """Normalize ``config`` into the face-mesh settings group.

    Accepts ``{"vision": {...}}``, ``{"face_mesh": {...}}``, or a plain dict of
    face-mesh options. Returns ``{}`` for anything else (safe internal defaults
    are then used by the caller).
    """
    if not isinstance(config, dict):
        return {}
    for key in ("face_mesh", "vision"):
        group = config.get(key)
        if isinstance(group, dict):
            return group
    return config


def _normalized_to_pixel(normalized_landmarks, frame_size) -> np.ndarray:
    """Convert a list of normalized landmarks to a (N, 2) pixel-space array.

    MediaPipe normalizes each coordinate to [0, 1] relative to the frame;
    multiplying by width/height yields pixel space. Returns a float32 array
    with one row per landmark, ordered identically to the input list.
    """
    width, height = frame_size
    n = len(normalized_landmarks)
    points_px = np.zeros((n, 2), dtype=np.float32)
    for i, landmark in enumerate(normalized_landmarks):
        points_px[i, 0] = landmark.x * width
        points_px[i, 1] = landmark.y * height
    return points_px


def _euclidean(a, b) -> float:
    """Euclidean distance between two (x, y) points."""
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _landmark_quality(points_px, frame_size) -> float:
    """Basic landmark validity heuristic in [0.0, 1.0].

    Pure geometric checks, no learned model and no telemetry math:

    * landmarks exist and are numerous enough to be a usable mesh,
    * every coordinate is finite,
    * eye widths and eye vertical (EAR-style) distances are positive,
    * inter-eye distance is positive and the face is not extremely small
      relative to the frame,
    * coordinates lie (mostly) inside the frame.

    A normal, well-framed face scores close to 1.0; missing/degenerate/tiny
    faces score 0.0.
    """
    if points_px is None or not isinstance(points_px, np.ndarray):
        return 0.0
    if points_px.ndim != 2 or points_px.shape[1] != 2 or points_px.shape[0] == 0:
        return 0.0
    if frame_size is None:
        return 0.0
    width, height = frame_size
    if width is None or height is None or width <= 0 or height <= 0:
        return 0.0

    n = points_px.shape[0]
    if n < _MIN_TRUSTED_LANDMARK_COUNT:
        return 0.0

    required = (
        LEFT_EYE_OUTER,
        RIGHT_EYE_OUTER,
        NOSE_TIP,
        CHIN,
        LEFT_MOUTH_CORNER,
        RIGHT_MOUTH_CORNER,
        133,  # left eye inner corner
        160, 158, 153, 144, 145,  # left eye lids
        385, 387, 386, 380, 374,  # right eye lids
    )
    if max(required) >= n:
        return 0.0

    if not np.isfinite(points_px).all():
        return 0.0

    p = points_px

    # Eye widths must be positive (non-degenerate geometry).
    left_eye_width = _euclidean(p[LEFT_EYE_OUTER], p[133])
    right_eye_width = _euclidean(p[RIGHT_EYE_OUTER], p[133])
    if left_eye_width <= 0.0 or right_eye_width <= 0.0:
        return 0.0

    # Eye vertical (EAR-style) distances must be positive.
    eye_verticals = (
        _euclidean(p[160], p[144]),
        _euclidean(p[158], p[153]),
        _euclidean(p[385], p[380]),
        _euclidean(p[387], p[373]),
    )
    if min(eye_verticals) <= 0.0:
        return 0.0

    inter_eye = _euclidean(p[LEFT_EYE_OUTER], p[RIGHT_EYE_OUTER])
    if inter_eye <= 0.0:
        return 0.0

    score = 1.0

    # Face must not be extremely small relative to the frame.
    frame_min = float(min(width, height))
    relative_span = inter_eye / frame_min
    if relative_span < _MIN_INTER_EYE_FRAME_FRACTION:
        return 0.0
    score *= min(1.0, relative_span / 0.04)

    # Coordinates should lie (mostly) inside the frame.
    margin = max(8.0, frame_min * 0.02)
    in_bounds = (
        (p[:, 0] >= -margin)
        & (p[:, 0] <= width + margin)
        & (p[:, 1] >= -margin)
        & (p[:, 1] <= height + margin)
    ).mean()
    score *= float(in_bounds)

    return float(np.clip(score, 0.0, 1.0))


class FaceMeshDetector:
    """Thin wrapper around MediaPipe FaceMesh.

    Parameters
    ----------
    config : dict or None
        Optional settings. Reads ``{"face_mesh": ...}`` or ``{"vision": ...}``
        groups (or a flat dict). Safe internal defaults are used when unset:
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
        frame_is_bgr=True. A missing config file is fine.
    """

    def __init__(self, config=None):
        settings = _face_mesh_settings(config)

        def _bool_setting(*keys, default):
            for key in keys:
                if key in settings:
                    return bool(settings[key])
            return default

        def _float_setting(key, default):
            try:
                return float(settings.get(key, default))
            except (TypeError, ValueError):
                return default

        def _int_setting(key, default):
            try:
                return int(settings.get(key, default))
            except (TypeError, ValueError):
                return default

        self.frame_is_bgr = _bool_setting(
            "frame_is_bgr", "input_is_bgr", default=_DEFAULT_FRAME_IS_BGR
        )

        # Instantiate lazily; __init__ may raise if the runtime cannot start
        # FaceMesh, and callers must be able to observe that at construction.
        try:
            self._face_mesh = _face_mesh_mod.FaceMesh(
                static_image_mode=False,
                max_num_faces=_int_setting(
                    "max_num_faces", _DEFAULT_MAX_NUM_FACES
                ),
                refine_landmarks=_bool_setting(
                    "refine_landmarks", default=_DEFAULT_REFINE_LANDMARKS
                ),
                min_detection_confidence=_float_setting(
                    "min_detection_confidence",
                    _DEFAULT_MIN_DETECTION_CONFIDENCE,
                ),
                min_tracking_confidence=_float_setting(
                    "min_tracking_confidence",
                    _DEFAULT_MIN_TRACKING_CONFIDENCE,
                ),
            )
        except Exception as exc:  # pragma: no cover - runtime-specific
            raise RuntimeError(
                "Failed to initialize MediaPipe FaceMesh: %r" % (exc,)
            ) from exc

    # ------------------------------------------------------------------ API

    def detect(self, frame):
        """Extract face landmarks from one RGB/BGR frame.

        Parameters
        ----------
        frame : np.ndarray or None
            Image with shape (H, W) or (H, W, 3) (OpenCV BGR by default,
            see ``frame_is_bgr`` config). ``None`` yields a no-face result.

        Returns
        -------
        FaceMeshResult
            Always a result object, never raises on detection problems.
        """
        if frame is None:
            return self._no_face_result((0, 0))

        try:
            height, width = frame.shape[:2]
        except (AttributeError, IndexError, ValueError):
            return self._no_face_result((0, 0))
        frame_size = (int(width), int(height))

        rgb = self._prepare_frame(frame)
        if rgb is None:
            return self._no_face_result(frame_size)

        try:
            results = self._face_mesh.process(rgb)
        except Exception:
            # Never let MediaPipe take down the pipeline; treat as no-face.
            return self._no_face_result(frame_size)

        if results is None or not getattr(results, "multi_face_landmarks", None):
            return self._no_face_result(frame_size)

        try:
            normalized_landmarks = results.multi_face_landmarks[0].landmark
            points_px = _normalized_to_pixel(normalized_landmarks, frame_size)
        except Exception:
            return self._no_face_result(frame_size)

        quality = _landmark_quality(points_px, frame_size)
        return FaceMeshResult(
            face_present=True,
            landmarks_px=points_px,
            normalized_landmarks=normalized_landmarks,
            frame_size=frame_size,
            landmark_quality=quality,
        )

    def close(self) -> None:
        """Release MediaPipe resources. Safe to call more than once."""
        face_mesh = getattr(self, "_face_mesh", None)
        if face_mesh is not None:
            close = getattr(face_mesh, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            self._face_mesh = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    # --------------------------------------------------------------- helpers

    def _prepare_frame(self, frame):
        """Return an RGB uint8 array MediaPipe can process, or None."""
        try:
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            if frame.ndim == 2:
                # Grayscale -> fake 3-channel RGB.
                return np.repeat(frame[..., None], 3, axis=2)
            if frame.ndim == 3 and frame.shape[2] == 3:
                if self.frame_is_bgr:
                    return frame[..., ::-1].copy()  # BGR -> RGB
                return frame
        except Exception:
            return None
        return None

    def _no_face_result(self, frame_size):
        """Build the explicit no-face result (never pretends a face exists)."""
        return FaceMeshResult(
            face_present=False,
            landmarks_px=None,
            normalized_landmarks=None,
            frame_size=frame_size,
            landmark_quality=0.0,
        )
