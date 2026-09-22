"""Bounded, thread-safe, drop-oldest frame buffering.

Owned by: ingestion agent.

A thin wrapper over :class:`queue.Queue` that:
- is bounded (``maxsize``),
- drops the oldest item when full so producers never block,
- returns ``None`` from ``get()`` immediately when empty (non-blocking),
- stores generic items (typically ``(frame, timestamp)`` tuples).

Nothing is persisted by this module.
"""

import queue


class BoundedFrameQueue:
    """A thread-safe bounded queue that drops the oldest item when full."""

    def __init__(self, maxsize: int = 2):
        if maxsize <= 0:
            raise ValueError("maxsize must be a positive integer, got %r" % (maxsize,))
        self._queue = queue.Queue(maxsize=int(maxsize))

    def put(self, item) -> None:
        """Insert ``item``; if full, drop the oldest item first.

        Never blocks.
        """
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except queue.Empty:  # pragma: no cover - racy full()/get() window
                pass
        self._queue.put(item)

    def get(self):
        """Return the oldest item, or ``None`` immediately if empty."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def qsize(self) -> int:
        """Number of items currently in the queue."""
        return self._queue.qsize()

    def full(self) -> bool:
        """True when the queue has reached its capacity."""
        return self._queue.full()

    def empty(self) -> bool:
        """True when the queue has no items."""
        return self._queue.empty()
