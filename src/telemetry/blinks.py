"""Blink dynamics: blink detection, rate (bpm), duration, microsleep events.

Deterministic state machine over smoothed average EAR:

    OPEN  --(EAR < threshold)-->  CLOSED  --(EAR >= threshold)-->  OPEN

On each completed closure the elapsed time classifies the event:
    * <  VALID_BLINK_MIN_MS          -> ignored as noise
    * in [min, microsleep_min_ms)    -> valid blink
    * >= MICROSLEEP_MIN_MS           -> microsleep

All timing uses caller-supplied monotonic timestamps in seconds (no frame
counts, no fixed frame rate assumption). Missing EAR (None) never mutates
state and never fabricates telemetry.

Owned by: telemetry agent.
"""

from collections import deque

# ---------------------------------------------------------------------------
# Configurable thresholds (defaults per specification)
# ---------------------------------------------------------------------------
EAR_THRESHOLD = 0.22
VALID_BLINK_MIN_MS = 60
VALID_BLINK_MAX_MS = 500
MICROSLEEP_MIN_MS = 500

# Blink-per-minute window and average-duration sample count.
BPM_WINDOW_SECONDS = 60.0
AVG_BLINK_SAMPLES = 10

# Microsleep recency flags.
MICROSLEEP_RECENT_30S_SECONDS = 30.0
MICROSLEEP_RECENT_3S_SECONDS = 3.0


def _default_result():
    return {
        "blink_completed": False,
        "microsleep_completed": False,
        "blink_duration_ms": None,
        "closure_active": False,
        "bpm": 0.0,
        "avg_blink_ms": 0.0,
        "microsleep_count_total": 0,
        "microsleep_recent_30s": False,
        "microsleep_recent_3s": False,
        "valid_blink_count_total": 0,
    }


class BlinkTracker:
    """Tracks eye open/closed transitions and classifies blink/microsleeps."""

    def __init__(self, config: dict = None):
        cfg = {
            "EAR_THRESHOLD": EAR_THRESHOLD,
            "VALID_BLINK_MIN_MS": VALID_BLINK_MIN_MS,
            "VALID_BLINK_MAX_MS": VALID_BLINK_MAX_MS,
            "MICROSLEEP_MIN_MS": MICROSLEEP_MIN_MS,
            "BPM_WINDOW_SECONDS": BPM_WINDOW_SECONDS,
            "AVG_BLINK_SAMPLES": AVG_BLINK_SAMPLES,
        }
        if config:
            cfg.update(config)

        self.ear_threshold = float(cfg["EAR_THRESHOLD"])
        self.min_blink_ms = float(cfg["VALID_BLINK_MIN_MS"])
        self.max_blink_ms = float(cfg["VALID_BLINK_MAX_MS"])
        self.microsleep_min_ms = float(cfg["MICROSLEEP_MIN_MS"])
        self.bpm_window_seconds = float(cfg["BPM_WINDOW_SECONDS"])
        self.avg_blink_samples = max(1, int(cfg["AVG_BLINK_SAMPLES"]))

        self.reset()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def reset(self):
        """Reset all internal state (no events, no history)."""
        self._is_closed = False
        self._closure_start_t = None
        self._blink_end_times = deque()          # seconds (monotonic)
        self._blink_durations_ms = deque(maxlen=self.avg_blink_samples)
        self.valid_blink_count_total = 0
        self.microsleep_count_total = 0
        self._last_microsleep_end_t = None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, ear_avg_smoothed, t):
        """Feed one smoothed average EAR value at monotonic time ``t`` (s).

        Returns a dict (see module docstring / brief) summarising the update:
        completed event classification, current closure state, and rolling
        blink-rate / duration statistics.
        """
        result = _default_result()
        result["valid_blink_count_total"] = self.valid_blink_count_total
        result["microsleep_count_total"] = self.microsleep_count_total

        if ear_avg_smoothed is None:
            # Missing landmarks: do not mutate state. Report current history
            # (expiring with the given t) but never a fabricated closure.
            self._prune_blink_history(t)
            self._fill_statistics(result, t)
            return result

        closed = ear_avg_smoothed < self.ear_threshold

        if closed and not self._is_closed:
            # OPEN -> CLOSED
            self._is_closed = True
            self._closure_start_t = t
        elif not closed and self._is_closed:
            # CLOSED -> OPEN: complete and classify the event.
            self._is_closed = False
            duration_ms = (t - self._closure_start_t) * 1000.0
            self._closure_start_t = None
            result["blink_duration_ms"] = duration_ms

            if duration_ms >= self.microsleep_min_ms:
                self.microsleep_count_total += 1
                self._last_microsleep_end_t = t
                result["microsleep_completed"] = True
            elif (
                self.min_blink_ms <= duration_ms <= self.max_blink_ms
            ):
                self.valid_blink_count_total += 1
                self._blink_end_times.append(t)
                self._blink_durations_ms.append(duration_ms)
                result["blink_completed"] = True
            # else: < VALID_BLINK_MIN_MS -> noise, ignored.

        self._prune_blink_history(t)
        result["valid_blink_count_total"] = self.valid_blink_count_total
        result["microsleep_count_total"] = self.microsleep_count_total
        result["closure_active"] = self._is_closed
        self._fill_statistics(result, t)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _prune_blink_history(self, t):
        """Drop blink completions older than the BPM window at time ``t``."""
        cutoff = t - self.bpm_window_seconds
        while self._blink_end_times and self._blink_end_times[0] < cutoff:
            self._blink_end_times.popleft()

    def _fill_statistics(self, result, t):
        """Populate bpm / avg blink duration / microsleep recency fields."""
        result["bpm"] = float(len(self._blink_end_times))

        if self._blink_durations_ms:
            result["avg_blink_ms"] = (
                sum(self._blink_durations_ms) / len(self._blink_durations_ms)
            )
        else:
            result["avg_blink_ms"] = 0.0

        if self._last_microsleep_end_t is not None:
            age = t - self._last_microsleep_end_t
            result["microsleep_recent_30s"] = (
                age <= MICROSLEEP_RECENT_30S_SECONDS
            )
            result["microsleep_recent_3s"] = (
                age <= MICROSLEEP_RECENT_3S_SECONDS
            )
