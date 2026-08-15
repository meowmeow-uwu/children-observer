"""
Integration test — chạy pipeline demo qua 3 vòng video liên tục.

Tiêu chí (test.md T02/T09/T10):
- Mỗi loop 0/1/2 đều có frame + metadata tracks message (không chỉ tổng số).
- Message đúng wire contract (schema_version, stream_id, source_time_ms,
  source_pts_ms, loop_id; track có class_name/class_id/confirmed).
- Loop mới reset tracker (track id quay lại từ đầu).
- Không crash, RAM đạt plateau (RSS tăng < 150MB sau warm-up).
- Không có detection cũ replay sang loop mới (source_pts_ms của loop mới nhỏ hơn).

Chạy: uv run pytest tests/test_edge/test_demo_pipeline.py -m integration
"""

import json
import sys
import time
from pathlib import Path

import psutil
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from module_edge_firmware.demo_stream.pipeline import (  # noqa: E402
    DemoStreamConfig,
    DemoStreamPipeline,
    SCHEMA_VERSION,
)

pytestmark = pytest.mark.integration

VIDEO = Path("module_edge_firmware/test_video.mp4")
requires_video = pytest.mark.skipif(not VIDEO.exists(), reason="test_video.mp4 missing")


def _run_pipeline(duration_s: float) -> tuple[DemoStreamPipeline, list[dict], int]:
    cfg = DemoStreamConfig(
        ws_relay_enabled=False,
        camera_id="cam_integration",
        viewer_gated=False,
    )
    pipeline = DemoStreamPipeline(cfg)
    pipeline.detector.load()
    pipeline.source.start()

    import threading

    messages: list[dict] = []
    collector = threading.Thread(
        target=lambda: _drain_forever(pipeline, messages), daemon=True
    )

    pipeline._running = True
    thread = threading.Thread(target=pipeline._detection_loop, daemon=True)
    thread.start()
    collector.start()

    time.sleep(duration_s)

    pipeline._running = False
    thread.join(timeout=5)
    collector.join(timeout=2)
    pipeline.source.stop()
    return pipeline, messages, pipeline.store.loop_id


def _drain_forever(pipeline, messages: list[dict]) -> None:
    """Thu thập message liên tục (outbox bounded — drain cuối sẽ mất loop đầu)."""
    import queue

    while pipeline._running:
        try:
            msg = pipeline.outbox.get(timeout=0.2)
            messages.append(msg)
        except queue.Empty:
            continue


@requires_video
def test_three_loops_each_have_tracks_messages():
    """T02/T09: Mỗi loop 0, 1, 2 phải có message tracks — không được dừng sau loop đầu."""
    pipeline, messages, loops_seen = _run_pipeline(duration_s=95)

    assert loops_seen >= 3, f"chỉ chạy {loops_seen} vòng"

    tracks_msgs = [m for m in messages if m["type"] == "tracks"]
    assert len(tracks_msgs) > 50

    per_loop = {0: 0, 1: 0, 2: 0}
    for m in tracks_msgs:
        if m["loop_id"] in per_loop:
            per_loop[m["loop_id"]] += 1
    assert per_loop[0] > 0, "loop 0 không có tracks message"
    assert per_loop[1] > 0, "loop 1 không có tracks message — detection dừng sau loop đầu!"
    assert per_loop[2] > 0, "loop 2 không có tracks message — detection dừng sau loop đầu!"
    print(f"\n[integration] tracks/loop: {per_loop} total={len(tracks_msgs)} loops={loops_seen}")


@requires_video
def test_wire_contract_fields_and_json_safe():
    """T01: message đúng contract, JSON-safe, track đủ class_name/class_id/confirmed."""
    pipeline, messages, _ = _run_pipeline(duration_s=12)

    assert len(messages) > 20
    for m in messages:
        json.dumps(m)
        assert m.get("schema_version") == SCHEMA_VERSION
        assert m.get("camera_id") == "cam_integration"
        assert isinstance(m.get("stream_id"), str) and m["stream_id"]
        assert isinstance(m.get("sent_at_ms"), (int, float))
        if m["type"] == "tracks":
            assert isinstance(m.get("source_time_ms"), (int, float))
            assert isinstance(m.get("source_pts_ms"), (int, float))
            assert isinstance(m.get("loop_id"), int)
            assert isinstance(m["tracks"], list)
            for t in m["tracks"]:
                assert isinstance(t["track_id"], int)
                assert t["class_name"] == "child"
                assert t["class_id"] == 1
                assert isinstance(t["confirmed"], bool)
                x1, y1, x2, y2 = t["box"]
                assert 0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0


@requires_video
def test_no_stale_replay_across_loops():
    """T02: loop mới không replay detection cũ — source_pts_ms reset về nhỏ."""
    pipeline, messages, loops_seen = _run_pipeline(duration_s=95)

    tracks_msgs = [m for m in messages if m["type"] == "tracks"]
    assert loops_seen >= 3
    # loop 1: mọi source_pts_ms phải nhỏ hơn duration của loop 0
    pts_by_loop: dict[int, list[float]] = {}
    for m in tracks_msgs:
        pts_by_loop.setdefault(m["loop_id"], []).append(m["source_pts_ms"])

    for loop_id in (1, 2):
        if loop_id not in pts_by_loop:
            continue
        prev_max = max(pts_by_loop[loop_id - 1])
        # Frame đầu loop mới phải reset gần 0 (không phải tiếp tục timestamp cũ)
        assert min(pts_by_loop[loop_id]) < 2000, (
            f"loop {loop_id} bắt đầu ở source_pts_ms={min(pts_by_loop[loop_id]):.0f} — có thể replay stale"
        )
        assert max(pts_by_loop[loop_id]) <= prev_max + 1000, "timestamp vượt biên loop"


@requires_video
def test_memory_plateau_three_loops():
    """T10: RSS sau warm-up tăng < 150MB qua 3 loop."""
    process = psutil.Process()
    rss_before = process.memory_info().rss
    pipeline, messages, loops_seen = _run_pipeline(duration_s=95)
    rss_after = process.memory_info().rss
    growth_mb = (rss_after - rss_before) / (1024 * 1024)

    assert loops_seen >= 3
    assert growth_mb < 150, f"RAM growth quá lớn: {growth_mb:.1f}MB"
    print(f"\n[integration] loops={loops_seen} messages={len(messages)} rss_growth={growth_mb:.1f}MB")


@requires_video
def test_tracker_reset_on_loop_restart():
    """Track id sau khi loop mới phải bắt đầu lại từ đầu (tracker reset)."""
    from module_edge_firmware.demo_stream.detector import OnnxDetector
    from module_edge_firmware.demo_stream.tracker import ByteTrackAdapter

    detector = OnnxDetector("weights/roi_detection/best.onnx", conf_threshold=0.05)
    detector.load()
    tracker = ByteTrackAdapter(classes_to_track=("child",), frame_rate=8)

    import cv2

    cap = cv2.VideoCapture(str(VIDEO))
    try:
        for loop in range(2):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            tracker.reset()
            for _ in range(300):
                ret, frame = cap.read()
                if not ret:
                    break
                tracks = tracker.update(detector.detect(frame))
                for t in tracks:
                    assert t["track_id"] <= 20, f"track id không reset sau loop: {t['track_id']}"
    finally:
        cap.release()
