"""
Demo Stream — pipeline duy nhất cho luồng demo.

Một tiến trình Edge duy nhất sở hữu VideoCapture, ONNX session và ByteTrack:

    DemoVideoSource (giải mã một lần, chạy đúng clock video)
        ├── WebRTC video (AIVideoTrack) ────────────────► Frontend
        ├── WebRTC DataChannel (track metadata/PTS) ────► Frontend overlay
        ├── /ws/detections/edge (relay qua backend) ────► các client web khác
        └── POST /api/alerts (alert queue worker) ─────► Backend DB/WS

Wire contract: schema_version=1, snake_case, stream_id + source_time_ms
(clock monotonic của pipeline) — frontend normalize một lần tại biên nhận.
"""

from module_edge_firmware.demo_stream.frame_source import DemoVideoSource, FrameStore
from module_edge_firmware.demo_stream.detector import OnnxDetector, letterbox, unletterbox_box
from module_edge_firmware.demo_stream.tracker import ByteTrackAdapter
from module_edge_firmware.demo_stream.roi_engine import RoiStateEngine
from module_edge_firmware.demo_stream.backend_sync import BackendSync
from module_edge_firmware.demo_stream.pipeline import DemoStreamPipeline, run

__all__ = [
    "DemoVideoSource",
    "FrameStore",
    "OnnxDetector",
    "letterbox",
    "unletterbox_box",
    "ByteTrackAdapter",
    "RoiStateEngine",
    "BackendSync",
    "DemoStreamPipeline",
    "run",
]
