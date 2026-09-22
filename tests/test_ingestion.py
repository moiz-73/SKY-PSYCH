"""Tests for the ingestion layer (camera, preprocess, buffering).

Owned by: ingestion agent.

These tests never require a physical camera. VideoSource file-path behavior is
exercised with a tiny synthetic video written to a pytest-managed temp dir.
"""

import os
import time

import numpy as np
import pytest

from src.ingestion import BoundedFrameQueue, VideoSource, preprocess

# ---------------------------------------------------------------------------
# BoundedFrameQueue
# ---------------------------------------------------------------------------


def test_bounded_queue_drops_oldest_when_full():
    q = BoundedFrameQueue(maxsize=2)
    q.put("first")
    q.put("second")
    q.put("third")  # "first" must be evicted

    assert q.qsize() == 2
    assert q.get() == "second"
    assert q.get() == "third"
    assert q.get() is None  # drained


def test_bounded_queue_get_returns_none_when_empty():
    q = BoundedFrameQueue(maxsize=2)
    assert q.get() is None
    assert q.qsize() == 0


def test_bounded_queue_stores_frame_timestamp_tuples():
    q = BoundedFrameQueue(maxsize=3)
    now = time.monotonic()
    q.put((np.zeros((32, 32, 3), dtype=np.uint8), now))

    frame, timestamp = q.get()
    assert frame.shape == (32, 32, 3)
    assert timestamp == now


def test_bounded_queue_rejects_non_positive_maxsize():
    with pytest.raises(ValueError):
        BoundedFrameQueue(maxsize=0)


# ---------------------------------------------------------------------------
# preprocess
# ---------------------------------------------------------------------------


def test_preprocess_returns_none_when_input_none():
    assert preprocess(None, {}) is None
    assert preprocess(None, {"camera": {"mirror": True}}) is None


def test_preprocess_resizes_to_max_width():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out = preprocess(frame, {"camera": {"max_width": 1280}})

    assert out is not None
    assert out.shape[1] == 1280
    assert out.shape[0] == 720  # aspect ratio preserved: 1080 * 1280 / 1920


def test_preprocess_does_not_upscale_smaller_frames():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = preprocess(frame, {})

    assert out.shape == (480, 640, 3)  # untouched: already under the 1280 cap


def test_preprocess_mirror_flips_horizontally():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, 50, :] = 255  # bright vertical marker on the left

    out = preprocess(frame, {"camera": {"mirror": True}})

    # The marker must now sit on the right edge (x = width - 1 - 50).
    right_col = out.shape[1] - 51
    assert bool(out[:, right_col, :].any())
    assert not out[:, 50, :].any()  # original location emptied


def test_preprocess_mirror_defaults_off_for_files():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, 50, :] = 255

    out = preprocess(frame, {})  # mirror unset -> no flip
    assert bool(out[:, 50, :].any())
    assert not out[:, out.shape[1] - 51, :].any()


def test_preprocess_clahe_keeps_shape_and_dtype():
    frame = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
    out = preprocess(frame, {}, use_clahe=True)

    assert out is not None
    assert out.shape == frame.shape
    assert out.dtype == np.uint8


# ---------------------------------------------------------------------------
# VideoSource
# ---------------------------------------------------------------------------


def test_video_source_accepts_integer_and_string_sources():
    with pytest.raises(TypeError):
        VideoSource(None, {})

    src_int = VideoSource(0, {})  # instantiation must not require a camera
    assert isinstance(src_int, VideoSource)
    src_int.release()

    src_str = VideoSource("unused/path.mp4", {})
    assert isinstance(src_str, VideoSource)
    src_str.release()


def test_video_source_missing_file_raises_runtime_error():
    missing = os.path.join("does_not_exist_dir", "missing_clip.avi")
    src = VideoSource(missing, {})
    with pytest.raises(RuntimeError) as excinfo:
        src.start()
    assert "Could not open video source" in str(excinfo.value)
    src.release()


def test_video_source_reads_from_local_file(tmp_path):
    import cv2

    clip = tmp_path / "synthetic_clip.avi"
    writer = cv2.VideoWriter(
        str(clip),
        cv2.VideoWriter_fourcc(*"MJPG"),
        30,
        (320, 240),
    )
    try:
        assert writer.isOpened(), "cv2.VideoWriter could not open a temp clip"
        sample = np.zeros((240, 320, 3), dtype=np.uint8)
        writer.write(sample)
        writer.write(sample)
    finally:
        writer.release()

    assert clip.exists()

    src = VideoSource(str(clip), {})
    try:
        frame, timestamp = src.read()  # read() auto-starts

        assert frame is not None
        assert frame.shape == (240, 320, 3)
        assert isinstance(timestamp, float)
        # monotonic timestamps are comparable and sane
        assert timestamp >= time.monotonic() - 5.0
    finally:
        src.release()
