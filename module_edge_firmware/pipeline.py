"""
Edge Pipeline Orchestrator.

Main loop: Capture → Preprocess → AI Inference → Risk Assessment → Alert
Đây là entry point chính cho xử lý tại camera/edge.
"""

from __future__ import annotations
import asyncio
import cv2

import signal
import time

import numpy as np
from loguru import logger
import psutil
import threading

from pathlib import Path

from configs.settings import get_settings
from configs.logging_config import setup_logging
from module_edge_firmware.ingestion.rtsp_capture import RTSPCapture
from module_edge_firmware.ingestion.preprocessor import FramePreprocessor
from module_edge_firmware.inference.multi_task_runner import MultiTaskRunner
from module_edge_firmware.analysis.risk_assessor import RiskAssessor
from module_edge_firmware.buffer.circular_buffer import CircularBuffer
from module_edge_firmware.buffer.storage_manager import StorageManager
from module_edge_firmware.alert.alert_manager import AlertManager
from module_edge_firmware.feedback_accuracy import AccuracyFeedbackTracker
from module_edge_firmware.mobile_gateway import MobileGateway

from module_edge_firmware.webrtc.video_track import AIVideoTrack
from module_edge_firmware.webrtc.client import EdgeWebRTCClient


class EdgePipeline:
    """
    Main edge processing pipeline.

    Kết nối toàn bộ các thành phần:
    1. RTSP Capture → thu nhận video
    2. Preprocessor → tiền xử lý frame
    3. MultiTaskRunner → AI inference (3 tasks song song)
    4. RiskAssessor → đánh giá rủi ro (branching logic)
    5. AlertManager → gửi cảnh báo (snapshot + clip + E2EE)
    """

    def __init__(self):
        self.settings = get_settings()

        # Components
        self.capture = RTSPCapture()
        self.preprocessor = FramePreprocessor()
        self.ai_runner = MultiTaskRunner()
        self.risk_assessor = RiskAssessor()
        self.buffer = CircularBuffer()
        self.storage_manager = StorageManager(
            dirs=[self.buffer.output_dir, Path("./snapshots")],
            min_free_gb=1.0
        )
        self.alert_manager = AlertManager(buffer=self.buffer)
        self.feedback_tracker = AccuracyFeedbackTracker()
        self.mobile_gateway: MobileGateway | None = None
        if self.settings.mobile_gateway_enabled:
            self.mobile_gateway = MobileGateway(
                host=self.settings.mobile_gateway_host,
                port=self.settings.mobile_gateway_port,
                request_handler=self._handle_mobile_message,
            )
        self.alert_manager.on_alert(self._on_alert_created)

        self._running = False
        self._health_thread: threading.Thread | None = None
        self._stats = {"frames_processed": 0, "alerts_sent": 0, "avg_latency_ms": 0.0}

    def start(self) -> None:
        """Khởi động pipeline."""
        setup_logging()
        logger.info("=" * 60)
        logger.info("AI Child Guardian - Edge Pipeline Starting")
        logger.info("=" * 60)

        # Load AI models
        logger.info("Loading AI models...")
        self.ai_runner.load_all()
        self._maybe_enable_mock_ai()

        # Warmup models to stabilize latency
        logger.info("Warming up models...")
        dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        for _ in range(5):
            self.ai_runner.analyze_frame(dummy_frame)
        logger.info("Warmup completed.")

        if self.mobile_gateway:
            self.mobile_gateway.start()

        # Start RTSP capture
        self.capture.start()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._running = True
        
        # Start health monitor
        self._health_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self._health_thread.start()
        
        logger.info("Pipeline started. Monitoring...")

        # Main processing loop
        self._process_loop()

    def stop(self) -> None:
        """Dừng pipeline."""
        logger.info("Stopping pipeline...")
        self._running = False
        if self.mobile_gateway:
            self.mobile_gateway.stop()
        self.capture.stop()
        self.ai_runner.shutdown()
        self.buffer.shutdown()
        logger.info(f"Pipeline stopped. Stats: {self._stats}")

    def _process_loop(self) -> None:
        """Main processing loop."""
        latency_sum = 0.0

        while self._running:
            try:
                frame = self.capture.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                self._process_frame(frame)

            except Exception as e:
                logger.error(f"❌ Critical error in pipeline loop: {e}")
                time.sleep(1)

    def _process_frame(self, frame: np.ndarray) -> None:
        """Xử lý một frame đơn lẻ qua toàn bộ pipeline."""
        start = time.perf_counter()

        # 1. Add frame to buffer
        self.buffer.add_frame(frame)

        # 2. AI inference (3 tasks song song)
        analysis = self.ai_runner.analyze_frame(frame)

        # 3. Risk assessment (branching logic)
        assessment = self.risk_assessor.assess(analysis)

        # 4. Alert nếu cần
        if assessment.should_alert:
            event_box = None
            if analysis.detections and analysis.has_children:
                children = analysis.detections.get_children()
                if len(children) > 0:
                    event_box = children.boxes[0]

            alert = self.alert_manager.process_risk(assessment, frame, event_box)
            if alert:
                self._stats["alerts_sent"] += 1

        # Update stats
        latency = (time.perf_counter() - start) * 1000
        self._stats["frames_processed"] += 1
        
        if latency > 100: # Cảnh báo nếu frame xử lý > 100ms
            logger.warning(f"⚠️ Late frame detected: {latency:.1f}ms (Target < 33ms)")

        # Cập nhật trung bình động (moving average) cho latency
        alpha = 0.05 # Lấy 5% giá trị mới, 95% cũ
        if self._stats["avg_latency_ms"] == 0:
            self._stats["avg_latency_ms"] = latency
        else:
            self._stats["avg_latency_ms"] = (1 - alpha) * self._stats["avg_latency_ms"] + alpha * latency

        # Log periodic stats
        if self._stats["frames_processed"] % 100 == 0:
            buffer_mem = self.buffer.get_memory_usage_mb()
            logger.info(
                f"Stats: {self._stats['frames_processed']} frames | "
                f"avg_latency={self._stats['avg_latency_ms']:.1f}ms | "
                f"alerts={self._stats['alerts_sent']} | "
                f"buffer={buffer_mem:.1f} MB"
            )

    def _health_monitor_loop(self) -> None:
        """Theo dõi sức khỏe hệ thống (CPU, RAM, Camera) trên thread riêng."""
        process = psutil.Process()
        while self._running:
            try:
                # 1. Thu thập stats
                cpu_percent = process.cpu_percent(interval=1.0)
                mem_mb = process.memory_info().rss / (1024 * 1024)
                disk_free_gb = psutil.disk_usage(str(self.buffer.output_dir)).free / (1024**3)
                
                # 2. Log health status (INFO to be visible)
                logger.info(
                    f"HEALTH: CPU={cpu_percent}% | RAM={mem_mb:.1f}MB | "
                    f"Disk={disk_free_gb:.1f}GB | "
                    f"Camera={self.capture.is_running} | FPS={self.capture.actual_fps:.1f}"
                )
                
                # 3. Cảnh báo rủi ro & Tự động dọn dẹp
                if disk_free_gb < 1.0:
                    self.storage_manager.check_and_cleanup()
                
                if not self.capture.is_running and self._running:
                    logger.error("🚨 CAMERA DISCONNECTED! Pipeline is waiting for reconnect...")
                
                # Sleep 30s trước lần check tiếp theo
                for _ in range(30):
                    if not self._running: break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Health Monitor error: {e}")
                time.sleep(5)

    def _signal_handler(self, signum, frame) -> None:
        logger.info(f"Signal {signum} received. Shutting down...")
        self.stop()

    def update_roi(self, zones_json: list[dict]) -> None:
        """Cập nhật ROI zones từ Mobile App."""
        self.risk_assessor.roi_checker.update_zones(zones_json)
        logger.info(f"ROI updated: {len(zones_json)} zones")

    def _maybe_enable_mock_ai(self) -> None:
        """Use mock inference only when explicitly enabled for local edge testing."""
        active_count = getattr(self.ai_runner, "active_task_count", 0)
        if active_count > 0:
            logger.info(f"AI model integration ready: {self.ai_runner.active_tasks}")
            return

        logger.warning("No trained AI model loaded from registry.")
        if not self.settings.edge_use_mock_ai_when_no_model:
            logger.warning("EDGE_USE_MOCK_AI_WHEN_NO_MODEL=false; pipeline will run without AI alerts.")
            return

        from module_edge_firmware.inference.mock_ai_service import MockAIService

        self.ai_runner.shutdown()
        self.ai_runner = MockAIService()
        self.ai_runner.load_all()
        logger.warning("MockAIService enabled for local integration testing.")

    def _on_alert_created(self, alert) -> None:
        """Register predictions and push alert events to connected mobile clients."""
        self.feedback_tracker.register_alert(alert)
        if self.mobile_gateway:
            self.mobile_gateway.broadcast("alert", alert.to_dict())

    def _handle_mobile_message(self, message: dict) -> dict:
        """Handle one JSON command from mobile."""
        msg_type = message.get("type")

        if msg_type == "ping":
            return {"ok": True, "type": "pong"}

        if msg_type == "status":
            return {"ok": True, "type": "status", "payload": self._status_payload()}

        if msg_type == "get_alerts":
            limit = int(message.get("limit", 50))
            return {
                "ok": True,
                "type": "alerts",
                "payload": self.alert_manager.get_history(limit=limit),
            }

        if msg_type == "update_roi":
            zones = message.get("zones")
            if not isinstance(zones, list):
                return {"ok": False, "error": "zones_must_be_list"}
            self.update_roi(zones)
            return {
                "ok": True,
                "type": "roi_updated",
                "payload": {"zone_count": self.risk_assessor.roi_checker.zone_count},
            }

        if msg_type == "feedback":
            alert_id = message.get("alert_id")
            is_correct = message.get("is_correct")
            if not alert_id or not isinstance(is_correct, bool):
                return {"ok": False, "error": "alert_id_and_is_correct_required"}
            summary = self.feedback_tracker.submit_feedback(
                alert_id=alert_id,
                is_correct=is_correct,
                correct_label=message.get("correct_label"),
                notes=message.get("notes", ""),
            )
            return {"ok": True, "type": "feedback_recorded", "payload": summary}

        return {"ok": False, "error": f"unknown_type: {msg_type}"}

    def _status_payload(self) -> dict:
        active_tasks = getattr(self.ai_runner, "active_tasks", [])
        if callable(active_tasks):
            active_tasks = active_tasks()
        return {
            "running": self._running,
            "stats": self._stats,
            "models": {
                "active_tasks": active_tasks,
                "registry_ready": self.ai_runner.registry.get_ready_tasks()
                if hasattr(self.ai_runner, "registry")
                else [],
            },
            "roi": {
                "enabled": self.risk_assessor.roi_checker.has_zones,
                "zone_count": self.risk_assessor.roi_checker.zone_count,
            },
            "feedback": self.feedback_tracker.summary(),
            "mobile": {
                "enabled": self.mobile_gateway is not None,
                "clients": self.mobile_gateway.client_count if self.mobile_gateway else 0,
            },
        }

async def main():
    # 1. Khởi tạo rãnh Video WebRTC
    ai_video_track = AIVideoTrack()

    # 2. Khởi tạo WebRTC Client (Thay thế IP bằng IP thực tế của Backend Server)
    # Ví dụ backend chạy trên IP 192.168.1.100 port 8000
    SIGNALING_URL = "ws://localhost:8007/ws/signaling"
    CAMERA_ID = "camera_living_room_01"
    
    webrtc_client = EdgeWebRTCClient(SIGNALING_URL, CAMERA_ID, ai_video_track)

    # Chạy Signaling Client ở chế độ nền (background task)
    asyncio.create_task(webrtc_client.connect())

    # 3. Luồng xử lý AI chính (Mô phỏng vòng lặp pipeline của bạn)
    #cap = cv2.VideoCapture("rtsp://your_camera_ip/stream")
    cap = cv2.VideoCapture("test_video.mp4")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue
            
        # -- ĐOẠN XỬ LÝ AI CỦA BẠN SẼ NẰM Ở ĐÂY --
        # detections = inference_engine.run(frame)
        # frame_with_boxes = draw_boxes(frame, detections)
        # ----------------------------------------
        
        # 4. Bơm khung hình đã vẽ hộp nhận diện vào WebRTC Track
        # Trong ví dụ này ta ném luôn frame gốc vào
        ai_video_track.update_frame(frame)
        
        # Nhường CPU cho các async task khác (WebRTC) chạy
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    asyncio.run(main())