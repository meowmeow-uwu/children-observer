"""
Mock AI Service - Giả lập kết quả AI cho team Edge.

Sử dụng khi team AI chưa hoàn thành model thật.
Cứ mỗi 100 frames thì inject 1 tình huống nguy hiểm (incident).

Cách dùng trong EdgePipeline:
    from module_edge_firmware.inference.mock_ai_service import MockAIService
    runner = MockAIService()
    analysis = runner.analyze_frame(frame)
"""

from __future__ import annotations

import time

import numpy as np

from module_ai_core.models.object_detector import DetectionResult
from module_ai_core.models.pose_estimator import PoseResult
from module_ai_core.models.behavior_classifier import BehaviorResult
from module_edge_firmware.inference.multi_task_runner import FrameAnalysis


class MockAIService:
    """
    Giả lập MultiTaskRunner khi chưa có model thật.

    Scenarios được mock:
    - Normal (frames 1-99, 101-199, ...): Chỉ có trẻ, không nguy hiểm.
    - Incident (frame 100, 200, ...): Trẻ + dao + hành vi bạo lực.
    """

    def __init__(self, incident_every: int = 100):
        """
        Args:
            incident_every: Tạo incident mỗi N frames (default: 100).
        """
        self.incident_every = incident_every
        self.frame_count = 0

    def analyze_frame(self, frame: np.ndarray) -> FrameAnalysis:
        """
        Giả lập phân tích frame AI.

        Args:
            frame: BGR numpy array (H, W, 3). Chỉ dùng shape, không xử lý.

        Returns:
            FrameAnalysis với dữ liệu mock.
        """
        self.frame_count += 1
        h, w = frame.shape[:2]
        is_incident = (self.frame_count % self.incident_every == 0)

        # --- Mock Detection ---
        if is_incident:
            # Trẻ em (class 0) + Dao (class 1)
            detection = DetectionResult(
                boxes=np.array([
                    [int(w * 0.2), int(h * 0.1), int(w * 0.5), int(h * 0.9)],  # child
                    [int(w * 0.5), int(h * 0.3), int(w * 0.65), int(h * 0.5)], # knife
                ], dtype=np.float32),
                scores=np.array([0.92, 0.87], dtype=np.float32),
                class_ids=np.array([0, 1], dtype=int),
                class_names=["child", "knife"],
            )
        else:
            # Chỉ trẻ em
            detection = DetectionResult(
                boxes=np.array([
                    [int(w * 0.2), int(h * 0.1), int(w * 0.5), int(h * 0.9)],
                ], dtype=np.float32),
                scores=np.array([0.94], dtype=np.float32),
                class_ids=np.array([0], dtype=int),
                class_names=["child"],
            )

        # --- Mock Pose (17 keypoints COCO, zeros = uncertain) ---
        pose = PoseResult(
            keypoints=np.zeros((1, 17, 3), dtype=np.float32),
            scores=np.array([0.88], dtype=np.float32),
            boxes=np.array([[
                int(w * 0.2), int(h * 0.1), int(w * 0.5), int(h * 0.9)
            ]], dtype=np.float32),
        )

        # --- Mock Behavior ---
        if is_incident:
            behavior = BehaviorResult(
                class_id=1,
                class_name="hitting",
                confidence=0.91,
                probabilities={
                    "normal": 0.05,
                    "hitting": 0.91,
                    "kicking": 0.02,
                    "pushing": 0.01,
                    "fall_injury": 0.01,
                    "fall_play": 0.00,
                    "grabbing": 0.00,
                    "throwing": 0.00,
                    "restraining": 0.00,
                },
            )
        else:
            behavior = BehaviorResult(
                class_id=0,
                class_name="normal",
                confidence=0.98,
                probabilities={
                    "normal": 0.98,
                    "hitting": 0.00,
                    "kicking": 0.00,
                    "pushing": 0.01,
                    "fall_injury": 0.00,
                    "fall_play": 0.01,
                    "grabbing": 0.00,
                    "throwing": 0.00,
                    "restraining": 0.00,
                },
            )

        return FrameAnalysis(
            frame_id=self.frame_count,
            timestamp=time.time(),
            detections=detection,
            poses=pose,
            behavior=behavior if is_incident else None,
            frame_size=(w, h),
            active_tasks=["roi_detection", "fall_detection"]
            + (["violence_detection"] if is_incident else []),
        )

    # Alias để tương thích với MultiTaskRunner interface
    def load_all(self) -> None:
        """No-op — Mock không cần load model."""
        from loguru import logger
        logger.info("MockAIService: No model loading required (mock mode)")

    def shutdown(self) -> None:
        """No-op."""
        pass
