"""Frame preprocessing: resize, mirror, optional NIR (CLAHE) enhancement.

Owned by: ingestion agent.

All operations happen in memory. This module never writes frames to disk and
never persists anything.
"""

import cv2
import numpy as np

# Default maximum width cap applied when config does not specify one.
_DEFAULT_MAX_WIDTH = 1280


def _camera_settings(config) -> dict:
    """Normalize ``config`` into the camera settings group.

    Accepts either the full settings mapping (``{"camera": {...}}``) or the
    camera group itself. Returns ``{}`` for anything else.
    """
    if not isinstance(config, dict):
        return {}
    group = config.get("camera")
    if isinstance(group, dict):
        return group
    return config


def preprocess(frame, config, mirror=None, use_clahe=False):
    """Return a processed copy of ``frame``, or ``None`` if ``frame`` is None.

    Parameters
    ----------
    frame : np.ndarray or None
        OpenCV BGR image to process.
    config : dict
        Settings mapping; the camera group (``config["camera"]``) is read for
        ``max_width``/``width``, ``mirror``, and ``use_clahe``/``nir``.
    mirror : bool or None
        When True, mirror horizontally. When None (default), fall back to
        ``config["camera"]["mirror"]`` (False when unset).
    use_clahe : bool
        When True, apply CLAHE to the value/luma channel for near-infrared
        enhancement. Also enabled if the camera config sets ``use_clahe`` or
        ``nir`` to true.

    Returns
    -------
    np.ndarray or None
        Processed BGR image. ``None`` propagates through unchanged.
    """
    if frame is None:
        return None

    settings = _camera_settings(config)

    # --- maximum width cap (aspect ratio preserved) ---------------------
    max_width = settings.get("max_width", settings.get("width", _DEFAULT_MAX_WIDTH))
    try:
        max_width = int(max_width)
    except (TypeError, ValueError):
        max_width = _DEFAULT_MAX_WIDTH
    if max_width <= 0:
        max_width = _DEFAULT_MAX_WIDTH

    result = frame

    if result.ndim != 3:
        result = np.asarray(result)
    if result.ndim == 2:
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

    height, width = result.shape[:2]
    if width > max_width:
        scale = max_width / float(width)
        new_size = (max_width, max(1, int(round(height * scale))))
        result = cv2.resize(result, new_size, interpolation=cv2.INTER_AREA)

    # --- mirroring (webcam convention; opt-in for files) ----------------
    if mirror is None:
        mirror = bool(settings.get("mirror", False))
    if mirror:
        result = cv2.flip(result, 1)

    # --- optional NIR enhancement via CLAHE ------------------------------
    effective_clahe = bool(
        use_clahe
        or settings.get("use_clahe", False)
        or settings.get("nir", False)
    )
    if effective_clahe:
        result = _apply_clahe(result)

    return result


def _apply_clahe(frame, clip_limit=2.0, tile_grid_size=(8, 8)):
    """Enhance local contrast with CLAHE on the luma (value) channel.

    Keeps the frame BGR on return. Works for color or already-gray inputs.
    """
    is_gray = frame.ndim == 2
    if is_gray:
        luma = frame
    else:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue, sat, luma = cv2.split(hsv)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    luma = clahe.apply(luma)

    if is_gray:
        return luma

    merged = cv2.merge((hue, sat, luma))
    return cv2.cvtColor(merged, cv2.COLOR_HSV2BGR)
