"""
Multi-Task Runner.

Chạy song song 3 AI task trên mỗi frame (từ Sequence Diagram):
1. Object Detection (trẻ em, dao, ổ điện...)
2. Pose Estimation (skeleton keypoints)
3. Action Recognition (bạo lực/té ngã)

Hỗ trợ Partial Loading:
- Tự động đọc weights/registry.json để biết model nào sẵn sàng.
- Nếu chỉ có 1 hoặc 2 model, vẫn chạy được pipeline với các model đó.
- Các task thiếu model sẽ trả về None (graceful degradation).
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field

import numpy as np
from loguru import logger

from module_ai_core.models.object_detector import ObjectDetector, DetectionResult
from module_ai_core.models.pose_estimator import PoseEstimator, PoseResult
from module_ai_core.models.behavior_classifier import BehaviorClassifier, BehaviorResult
from module_ai_core.model_registry import ModelRegistry


@dataclass
class FrameAnalysis:
    """Kết quả phân tích tổng hợp của một frame."""

    frame_id: int = 0
    timestamp: float = 0.0
    detections: DetectionResult | None = None
    poses: PoseResult | None = None
    behavior: BehaviorResult | None = None
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    active_tasks: list[str] = field(default_factory=list)

    @property
    def has_children(self) -> bool:
        if self.detections is None:
            return False
        children = self.detections.get_children()
        return len(children) > 0

    @property
    def has_dangerous_objects(self) -> bool:
        if self.detections is None:
            return False
        dangerous = self.detections.get_dangerous_objects()
        return len(dangerous) > 0

    @property
    def has_violence(self) -> bool:
        if self.behavior is None:
            return False
        return self.behavior.is_violent

    @property
    def has_fall(self) -> bool:
        if self.behavior is None:
            return False
        return self.behavior.is_fall

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "has_children": self.has_children,
            "has_dangerous_objects": self.has_dangerous_objects,
            "has_violence": self.has_violence,
            "has_fall": self.has_fall,
            "latency_ms": self.latency_ms,
            "active_tasks": self.active_tasks,
            "detections": self.detections.to_dict() if self.detections else [],
            "behavior": self.behavior.to_dict() if self.behavior else None,
        }


class MultiTaskRunner:
    """
    Chạy Object Detection + Pose Estimation + Action Recognition song song.

    Hỗ trợ Partial Loading:
    - Đọc Model Registry để biết model nào sẵn sàng.
    - Chỉ load và chạy model available.
    - Ghi log rõ ràng model nào đang active, model nào bị skip.
    """

    def __init__(
        self,
        detector: ObjectDetector | None = None,
        pose_estimator: PoseEstimator | None = None,
        behavior_classifier: BehaviorClassifier | None = None,
        max_workers: int = 3,
    ):
        self._detector = detector
        self._pose_estimator = pose_estimator
        self._behavior_classifier = behavior_classifier
        self.max_workers = max_workers

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._skeleton_buffer: list[np.ndarray] = []
        self._buffer_size = 30  # frames cho behavior analysis
        self._frame_counter = 0

        # Track which tasks are loaded
        self._det_loaded = False
        self._pose_loaded = False
        self._behavior_loaded = False

        self.registry = ModelRegistry()

    def load_all(self) -> None:
        """
        Load tất cả models có sẵn theo Registry.

        Nếu model chưa ready trong registry, skip và log warning.
        Pipeline vẫn chạy với các model đã load thành công.
        """
        self.registry.reload()
        logger.info(self.registry.summary())

        active = []

        # === ROI Detection (P3) ===
        if self._detector or self.registry.is_ready("roi_detection"):
            try:
                if self._detector is None:
                    model_path = self.registry.get_model_path("roi_detection")
                    self._detector = ObjectDetector(model_path=model_path)
                self._detector.load()
                self._det_loaded = True
                active.append("roi_detection")
                logger.info("✅ ROI Detection: LOADED")
            except Exception as e:
                logger.warning(f"⚠️ ROI Detection: FAILED - {e}")
        else:
            logger.warning("⏭️ ROI Detection: SKIPPED (model not ready)")

        # === Fall Detection / Pose (P5) ===
        if self._pose_estimator or self.registry.is_ready("fall_detection"):
            try:
                if self._pose_estimator is None:
                    model_path = self.registry.get_model_path("fall_detection")
                    self._pose_estimator = PoseEstimator(model_path=model_path)
                self._pose_estimator.load()
                self._pose_loaded = True
                active.append("fall_detection")
                logger.info("✅ Fall Detection (Pose): LOADED")
            except Exception as e:
                logger.warning(f"⚠️ Fall Detection: FAILED - {e}")
        else:
            logger.warning("⏭️ Fall Detection: SKIPPED (model not ready)")

        # === Violence Detection (P4) ===
        if self._behavior_classifier or self.registry.is_ready("violence_detection"):
            try:
                if self._behavior_classifier is None:
                    model_path = self.registry.get_model_path("violence_detection")
                    self._behavior_classifier = BehaviorClassifier(model_path=model_path)
                self._behavior_classifier.load()
                self._behavior_loaded = True
                active.append("violence_detection")
                logger.info("✅ Violence Detection: LOADED")
            except Exception as e:
                logger.warning(f"⚠️ Violence Detection: FAILED - {e}")
        else:
            logger.warning("⏭️ Violence Detection: SKIPPED (model not ready)")

        # Summary
        total = len(active)
        logger.info(f"{'=' * 50}")
        logger.info(f"MultiTaskRunner: {total}/3 models loaded → {active}")
        if total == 0:
            logger.warning("⚠️ Không có model nào! Sử dụng MockAIService để test.")
        logger.info(f"{'=' * 50}")

    def analyze_frame(self, frame: np.ndarray) -> FrameAnalysis:
        """
        Phân tích một frame với các model đã load.

        Chỉ chạy các task có model. Task thiếu model sẽ trả về None.
        """
        start_time = time.perf_counter()
        self._frame_counter += 1

        analysis = FrameAnalysis(
            frame_id=self._frame_counter,
            timestamp=time.time(),
        )

        futures: dict[str, Future] = {}

        # Submit tasks song song (chỉ submit nếu model đã load)
        if self._det_loaded:
            futures["detection"] = self._executor.submit(self._run_detection, frame)
            analysis.active_tasks.append("roi_detection")

        if self._pose_loaded:
            futures["pose"] = self._executor.submit(self._run_pose, frame)
            analysis.active_tasks.append("fall_detection")

        # Collect Detection result
        if "detection" in futures:
            try:
                analysis.detections = futures["detection"].result(timeout=5.0)
            except Exception as e:
                analysis.errors.append(f"Detection error: {e}")
                logger.error(f"Detection failed: {e}")

        # Collect Pose result
        if "pose" in futures:
            try:
                analysis.poses = futures["pose"].result(timeout=5.0)
            except Exception as e:
                analysis.errors.append(f"Pose error: {e}")
                logger.error(f"Pose estimation failed: {e}")

        # Behavior analysis (cần pose data + behavior model)
        if self._behavior_loaded and analysis.poses and len(analysis.poses) > 0:
            skeleton_frame = analysis.poses.to_skeleton_sequence_frame()
            self._skeleton_buffer.append(skeleton_frame[0])
            analysis.active_tasks.append("violence_detection")

            if len(self._skeleton_buffer) >= self._buffer_size:
                try:
                    seq = np.array(self._skeleton_buffer[-self._buffer_size:])
                    analysis.behavior = self._behavior_classifier.predict(seq)
                except Exception as e:
                    analysis.errors.append(f"Behavior error: {e}")
                    logger.error(f"Behavior classification failed: {e}")

                # Keep buffer manageable
                if len(self._skeleton_buffer) > self._buffer_size * 2:
                    self._skeleton_buffer = self._skeleton_buffer[-self._buffer_size:]

        analysis.latency_ms = (time.perf_counter() - start_time) * 1000
        return analysis

    def _run_detection(self, frame: np.ndarray) -> DetectionResult:
        return self._detector.predict(frame)

    def _run_pose(self, frame: np.ndarray) -> PoseResult:
        return self._pose_estimator.predict(frame)

    def shutdown(self) -> None:
        """Shutdown executor."""
        self._executor.shutdown(wait=True)
        logger.info("MultiTaskRunner shut down")
