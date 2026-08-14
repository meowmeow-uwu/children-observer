"""
Tests cho letterbox/unletterbox — so sánh trực tiếp với Ultralytics trên frame thật.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from module_edge_firmware.demo_stream.detector import letterbox, unletterbox_box  # noqa: E402

VIDEO = Path("module_edge_firmware/test_video.mp4")
HAS_VIDEO = VIDEO.exists()


def _frame_210():
    cap = cv2.VideoCapture(str(VIDEO))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 210)
    ret, frame = cap.read()
    cap.release()
    assert ret
    return frame


@pytest.mark.skipif(not HAS_VIDEO, reason="test_video.mp4 missing")
def test_letterbox_matches_ultralytics_exactly():
    from ultralytics.data.augment import LetterBox as UltLetterbox

    frame = _frame_210()
    im_ult = UltLetterbox(new_shape=(640, 640))(image=frame.copy())
    im_ours, ratio, pad = letterbox(frame, (640, 640))

    assert im_ult.shape == im_ours.shape
    assert np.array_equal(im_ult, im_ours)
    assert 0.0 < ratio < 1.0
    assert pad[0] >= 0 and pad[1] >= 0


@pytest.mark.skipif(not HAS_VIDEO, reason="test_video.mp4 missing")
def test_unletterbox_roundtrip_preserves_normalized_coords():
    frame = _frame_210()
    h_orig, w_orig = frame.shape[:2]
    img, ratio, pad = letterbox(frame, (640, 640))

    # Box ở giữa frame, 100px trên ảnh letterbox
    cx_px, cy_px = img.shape[1] / 2, img.shape[0] / 2
    x1n, y1n, x2n, y2n = unletterbox_box(
        cx_px - 50, cy_px - 50, cx_px + 50, cy_px + 50, ratio, pad, w_orig, h_orig
    )

    assert 0.0 <= x1n <= 1.0
    assert 0.0 <= y1n <= 1.0
    assert x2n > x1n
    assert y2n > y1n
    # Box trung tâm → khoảng 0.5 ± vài %
    assert abs((x1n + x2n) / 2 - 0.5) < 0.05
    assert abs((y1n + y2n) / 2 - 0.5) < 0.05


def test_unletterbox_out_of_bounds_clamped():
    x1n, y1n, x2n, y2n = unletterbox_box(-1000, -1000, 5000, 5000, 0.5, (10, 10), 1920, 1080)
    assert x1n == 0.0 and y1n == 0.0
    assert x2n == 1.0 and y2n == 1.0
