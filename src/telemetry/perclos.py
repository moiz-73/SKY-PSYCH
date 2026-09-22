"""Percentage of eyelid closure (PERCLOS) over a time window.

PERCLOS P80 is the percentage of time within a rolling window during which the
eyes are treated as closed (smoothed average EAR below the threshold).

The window is purely timestamp-based: samples are (``t``, ``closed_flag``)
pairs pushed into a deque and expired when ``t`` falls out of the window. No
frame counts, no fixed frame rate. PERCLOS is computed by integrating the time
intervals between consecutive samples (each sample represents the state from
its own timestamp until the next sample's timestamp), so irregular sampling
does not bias the result.

Missing EAR (None) samples are skipped entirely: they never add a false
closed/open sample.

Owned by: telemetry agent.
"""

from collections import deque

# ---------------------------------------------------------------------------
# Configurable thresholds (defaults per specification)
# ---------------------------------------------------------------------------
PERCLOS_WINDOW_SECONDS = 30.0
EAR_THRESHOLD = 0.22


class PerclosWindow:
    """Rolling, timestamp-based PERCLOS estimator over smoothed EAR."""

    def __init__(self, window_seconds: float = PERCLOS_WINDOW_SECONDS,
                 ear_threshold: float = EAR_THRESHOLD):
        self.window_seconds = float(window_seconds)
        self.ear_threshold = float(ear_threshold)
        self.reset()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def reset(self):
        """Clear all samples."""
        self._samples = deque()  # (t, closed_flag) ordered by t
        self._last_t = None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, ear_smoothed, t):
        """Record the closure state at monotonic time ``t`` (seconds).

        ``ear_smoothed`` of None (missing landmarks) is skipped: no sample is
        added, so the window is never corrupted by false open/closed data.
        """
        if ear_smoothed is None:
            return
        closed = ear_smoothed < self.ear_threshold
        self._samples.append((t, bool(closed)))
        self._last_t = t
        self._expire(t)

    def _expire(self, t):
        """Remove samples older than ``t - window_seconds``."""
        cutoff = t - self.window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    # ------------------------------------------------------------------
    # Readout
    # ------------------------------------------------------------------
    def value(self, t_now: float = None):
        """PERCLOS percentage (0-100) over the current window.

        Returns 0.0 when the window holds fewer than two samples
        (insufficient data -- callers handle coverage separately).

        Each sample is assumed to represent the eye state from its own
        timestamp until the next sample's timestamp. If ``t_now`` is provided
        and is newer than the last sample, the final sample's interval is
        extended to ``t_now`` (e.g. the current frame time).
        """
        if len(self._samples) < 2:
            return 0.0

        total_time = 0.0
        closed_time = 0.0

        prev_t, prev_closed = self._samples[0]
        for t, closed in list(self._samples)[1:]:
            dt = t - prev_t
            if dt > 0:
                total_time += dt
                if prev_closed:
                    closed_time += dt
            prev_t, prev_closed = t, closed

        # Extend the last interval to "now" when requested.
        if t_now is not None and t_now > prev_t:
            dt = t_now - prev_t
            total_time += dt
            if prev_closed:
                closed_time += dt

        if total_time <= 0:
            return 0.0
        return (closed_time / total_time) * 100.0
