"""
Tests cho ByteTrackAdapter — track ID stability, output JSON-safe.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from module_edge_firmware.demo_stream.tracker import ByteTrackAdapter  # noqa: E402


def test_update_empty_returns_empty_list():
    tracker = ByteTrackAdapter(classes_to_track=("child",))
    assert tracker.update([]) == []


def test_track_id_stable_across_frames():
    """Track di chuyển nhẹ giữa các frame phải giữ nguyên track_id."""
    tracker = ByteTrackAdapter(classes_to_track=("child",))
    box = [0.3, 0.4, 0.5, 0.7]

    first = tracker.update([{"box": box, "class": "child", "class_id": 1, "score": 0.8}])
    assert len(first) == 1
    tid = first[0]["track_id"]

    # Box dịch chuyển nhẹ (5% mỗi bước) qua 5 frame
    for i in range(5):
        shift = 0.005 * i
        tracks = tracker.update(
            [
                {
                    "box": [box[0] + shift, box[1] + shift, box[2] + shift, box[3] + shift],
                    "class": "child",
                    "score": 0.8,
                }
            ]
        )
        assert len(tracks) == 1
        assert tracks[0]["track_id"] == tid

    json.dumps(tracks)


def test_non_child_classes_ignored():
    tracker = ByteTrackAdapter(classes_to_track=("child",))
    tracks = tracker.update(
        [
            {"box": [0.3, 0.4, 0.5, 0.7], "class": "adult", "score": 0.9},
            {"box": [0.1, 0.1, 0.2, 0.3], "class": "knife", "score": 0.9},
        ]
    )
    assert tracks == []


def test_low_confidence_filtered():
    tracker = ByteTrackAdapter(classes_to_track=("child",))
    tracks = tracker.update([{"box": [0.3, 0.4, 0.5, 0.7], "class": "child", "class_id": 1, "score": 0.01}])
    assert tracks == []


def test_reset_clears_state():
    tracker = ByteTrackAdapter(classes_to_track=("child",))
    tracker.update([{"box": [0.3, 0.4, 0.5, 0.7], "class": "child", "class_id": 1, "score": 0.8}])
    tracker.reset()
    # Sau reset + không có detection → không có track
    assert tracker.update([]) == []


@pytest.mark.skipif(
    not Path("module_edge_firmware/test_video.mp4").exists(), reason="video missing"
)
def test_stability_over_video_subset():
    """Chạy qua 300 frame đầu: track output luôn JSON-safe, box hợp lệ."""
    import cv2

    from module_edge_firmware.demo_stream.detector import OnnxDetector

    detector = OnnxDetector("weights/roi_detection/best.onnx", conf_threshold=0.05)
    detector.load()
    tracker = ByteTrackAdapter(classes_to_track=("child",))

    cap = cv2.VideoCapture("module_edge_firmware/test_video.mp4")
    try:
        for _ in range(300):
            ret, frame = cap.read()
            if not ret:
                break
            dets = detector.detect(frame)
            tracks = tracker.update(dets)
            json.dumps(tracks)  # không crash
            for t in tracks:
                x1, y1, x2, y2 = t["box"]
                assert 0.0 <= x1 <= 1.0 and 0.0 <= x2 <= 1.0 and x2 > x1
                assert 0.0 <= y1 <= 1.0 and 0.0 <= y2 <= 1.0 and y2 > y1
                assert t["class_name"] == "child"
                assert t["class_id"] == 1
                assert 0.0 < t["confidence"] <= 1.0
                assert isinstance(t["confirmed"], bool)
    finally:
        cap.release()
