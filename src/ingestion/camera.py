"""Camera frame source: webcam (device index), video file path, or RTSP URL.

Owned by: ingestion agent.

A synchronous, single-threaded source. Frames are returned as
``(frame, timestamp)`` tuples where ``timestamp`` is a ``time.monotonic()``
float. Frames live only in memory — nothing is written to disk here, and the
source performs no network streaming by itself (an RTSP string is only honored
if the caller explicitly passes one).
"""

import time
from typing import Optional, Tuple, Union

import cv2

# Resolution/FPS property keys accepted from the camera config group.
_WIDTH_KEY = "width"
_HEIGHT_KEY = "height"
_FPS_KEY = "fps"

_DEFAULT_WIDTH = 1280
_DEFAULT_HEIGHT = 720
_DEFAULT_FPS = 30


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


class VideoSource:
    """Opens and reads frames from a webcam index, local file, or RTSP URL.

    Public API: ``start()``, ``read()``, ``release()``.

    - ``source`` may be an integer webcam index, a string file path, or an
      RTSP string. For the MVP, webcam indices and local file paths are the
      primary use cases.
    - Camera resolution and FPS are requested from ``config`` (``width``,
      ``height``, ``fps``) when present; the underlying backend decides what
      it can honor.
    - If the source cannot be opened, ``start()`` raises ``RuntimeError`` with
      a clear message.
    - ``read()`` returns ``(frame, timestamp)``; ``frame`` is an OpenCV BGR
      ``numpy.ndarray`` or ``None`` when no frame is available, and
      ``timestamp`` is a ``time.monotonic()`` float.
    """

    def __init__(self, source: Union[int, str], config: Optional[dict] = None):
        if not isinstance(source, (int, str)):
            raise TypeError(
                "source must be an integer webcam index or a string "
                "path/URL, got %r" % (source,)
            )
        self._source = source
        self._settings = _camera_settings(config)
        self._capture: Optional[cv2.VideoCapture] = None
        self._opened = False

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Open the capture device. Idempotent; raises RuntimeError on failure."""
        if self._opened:
            return

        capture = cv2.VideoCapture(self._source)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(
                "Could not open video source %r. "
                "If it is a camera index, make sure the camera is connected "
                "and not in use by another application. If it is a file path, "
                "make sure the file exists and is a readable video." % (self._source,)
            )

        # Best-effort camera property configuration (only meaningful for
        # live camera backends; harmless for files/URLs).
        if isinstance(self._source, int):
            self._try_set(capture, cv2.CAP_PROP_FRAME_WIDTH,
                          self._settings.get(_WIDTH_KEY, _DEFAULT_WIDTH))
            self._try_set(capture, cv2.CAP_PROP_FRAME_HEIGHT,
                          self._settings.get(_HEIGHT_KEY, _DEFAULT_HEIGHT))
            self._try_set(capture, cv2.CAP_PROP_FPS,
                          self._settings.get(_FPS_KEY, _DEFAULT_FPS))

        self._capture = capture
        self._opened = True

    def read(self) -> Tuple[Optional[object], float]:
        """Grab the next frame.

        Returns ``(frame, timestamp)``. ``frame`` is an OpenCV BGR image or
        ``None`` if no frame is currently available (e.g. end of file or a
        transient camera miss). The timestamp is captured with
        ``time.monotonic()`` as close to the grab as possible.
        """
        if not self._opened:
            self.start()

        capture = self._capture
        if capture is None or not capture.isOpened():
            return None, time.monotonic()

        ok, frame = capture.read()
        timestamp = time.monotonic()
        if not ok or frame is None:
            return None, timestamp
        return frame, timestamp

    def release(self) -> None:
        """Release the underlying capture object safely (idempotent)."""
        capture = self._capture
        self._capture = None
        self._opened = False
        if capture is not None:
            capture.release()

    # -- context manager convenience --------------------------------------

    def __enter__(self) -> "VideoSource":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _try_set(capture: cv2.VideoCapture, prop: int, value) -> None:
        """Request a capture property; failures are non-fatal and ignored."""
        try:
            capture.set(prop, int(value))
        except (ValueError, TypeError):
            pass
