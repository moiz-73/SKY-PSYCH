"""SkyPsych AI - ingestion subpackage.

Owned by: ingestion agent.

Exposes the public ingestion API:

- :class:`VideoSource` - webcam/file/RTSP frame source (``start/read/release``)
- :func:`preprocess` - resize / mirror / optional CLAHE (NIR) enhancement
- :class:`BoundedFrameQueue` - bounded, thread-safe, drop-oldest frame buffer
"""

from .buffering import BoundedFrameQueue
from .camera import VideoSource
from .preprocess import preprocess

__all__ = ["BoundedFrameQueue", "VideoSource", "preprocess"]
