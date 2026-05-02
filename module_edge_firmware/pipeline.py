"""
Edge Pipeline Orchestrator.

Main loop: Capture → Preprocess → AI Inference → Risk Assessment → Alert
Đây là entry point chính cho xử lý tại camera/edge.
"""

from __future__ import annotations

import signal
import time

import numpy as np
from loguru import logger

from configs.settings import get_settings
from configs.logging_config import setup_logging
from module_edge_firmware.ingestion.rtsp_capture import RTSPCapture
from module_edge_firmware.ingestion.preprocessor import FramePreprocessor
from module_edge_firmware.inference.multi_task_runner import MultiTaskRunner
from module_edge_firmware.analysis.risk_assessor import RiskAssessor
from module_edge_firmware.buffer.circular_buffer import CircularBuffer
from module_edge_firmware.alert.alert_manager import AlertManager


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
        self.alert_manager = AlertManager(buffer=self.buffer)

        self._running = False
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

        # Start RTSP capture
        self.capture.start()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._running = True
        logger.info("Pipeline started. Monitoring...")

        # Main processing loop
        self._process_loop()

    def stop(self) -> None:
        """Dừng pipeline."""
        logger.info("Stopping pipeline...")
        self._running = False
        self.capture.stop()
        self.ai_runner.shutdown()
        logger.info(f"Pipeline stopped. Stats: {self._stats}")

    def _process_loop(self) -> None:
        """Main processing loop."""
        latency_sum = 0.0

        while self._running:
            frame = self.capture.get_frame()

            if frame is None:
                time.sleep(0.01)
                continue

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
            latency_sum += latency
            self._stats["avg_latency_ms"] = latency_sum / self._stats["frames_processed"]

            # Log periodic stats
            if self._stats["frames_processed"] % 100 == 0:
                logger.info(
                    f"Stats: {self._stats['frames_processed']} frames | "
                    f"avg_latency={self._stats['avg_latency_ms']:.1f}ms | "
                    f"alerts={self._stats['alerts_sent']}"
                )

    def _signal_handler(self, signum, frame) -> None:
        logger.info(f"Signal {signum} received. Shutting down...")
        self.stop()

    def update_roi(self, zones_json: list[dict]) -> None:
        """Cập nhật ROI zones từ Mobile App."""
        self.risk_assessor.roi_checker.update_zones(zones_json)
        logger.info(f"ROI updated: {len(zones_json)} zones")
