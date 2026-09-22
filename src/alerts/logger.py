"""Local telemetry logging: abstract telemetry events, never raw frames.

Privacy guarantee
-----------------
The logger writes JSON Lines (one event per line) containing ONLY a strict
whitelist of abstract telemetry fields: ``schema_version``, ``t``,
``severity``, ``fatigue``, ``message`` and ``event_type``. Any other key in
the input event (image paths, raw frames, face coordinates, landmark arrays,
EAR values, ...) is silently dropped, never persisted. When ``output_path``
is None nothing is written to disk at all.

The logger is pure local I/O: no network, no cloud, no external export.

Owned by: alerts agent.
"""

import json

# Schema version of the emitted records (spec requirement).
SCHEMA_VERSION = 1

# Fields that are safe to persist. Anything else is refused.
_SAFE_FIELDS = ("schema_version", "t", "severity", "fatigue", "message",
                "event_type")

# Field names that must NEVER appear in a persisted record.
_FORBIDDEN_KEYS = {
    "image", "frame", "frame_path", "path", "file", "face", "landmark",
    "landmarks", "ear_l", "ear_r", "ear_avg", "pitch", "yaw", "roll",
    "pixels", "base64", "bbox", "coords", "coordinates", "photo",
}


class TelemetryEventLogger:
    """Appends abstract telemetry events as JSON Lines to one output file.

    ``output_path=None`` (default) keeps the logger in memory-only mode:
    ``log_event`` records nothing to disk (and is a safe no-op).
    """

    def __init__(self, output_path=None):
        self.output_path = output_path
        self._file = None
        self.count = 0
        self.last_event = None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def log_event(self, event):
        """Persist one abstract event (dict) as a JSON Lines record.

        Returns the sanitized record dict that was written, or None when in
        memory-only mode. Never raises for unknown fields: they are dropped.
        """
        record = self._sanitize(event or {})
        if record is None:
            return None
        self.count += 1
        self.last_event = record
        if self.output_path is not None:
            self._ensure_open()
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            self._file.write(line + "\n")
            self._file.flush()
        return record

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self):
        """Flush and close the underlying file (safe to call repeatedly)."""
        if self._file is not None:
            try:
                self._file.flush()
            finally:
                self._file.close()
                self._file = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_open(self):
        if self._file is None:
            self._file = open(self.output_path, "a", encoding="utf-8")

    def _sanitize(self, event):
        """Reduce an event dict to abstract telemetry fields only.

        Returns ``None`` if the event contains no safe field at all.
        """
        record = {}
        for key, value in event.items():
            if not isinstance(key, str):
                continue
            k = key.lower().strip()
            if k in _FORBIDDEN_KEYS:
                continue
            if k not in _SAFE_FIELDS:
                continue
            record[k] = self._coerce(k, value)
        record.setdefault("schema_version", SCHEMA_VERSION)
        if "schema_version" in record and not isinstance(
                record["schema_version"], int):
            record["schema_version"] = SCHEMA_VERSION
        return record if record else None

    @staticmethod
    def _coerce(key, value):
        """Coerce scalar values to JSON-safe types (dict/list/bytes dropped)."""
        if isinstance(value, (dict, list, tuple, set, bytes, bytearray)):
            return None
        try:
            if key in ("t", "fatigue"):
                return float(value)
            if key == "schema_version":
                return int(value)
            return str(value)
        except (TypeError, ValueError):
            return None
