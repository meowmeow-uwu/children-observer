"""
Fall Detector - Phát hiện té ngã.

Phân biệt té ngã chấn thương thực sự vs chơi đùa dựa trên:
- Tốc độ thay đổi tư thế (velocity)
- Thời gian nằm bất động (duration)
- Tư thế cơ thể (body orientation)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

import numpy as np
from loguru import logger

from module_ai_core.models.pose_estimator import PoseResult, Keypoint


@dataclass
class FallEvent:
    """Sự kiện té ngã."""
    timestamp: float
    confidence: float
    is_injury: bool  # True = chấn thương, False = chơi đùa
    duration_still: float  # Thời gian bất động (seconds)
    velocity: float  # Tốc độ rơi

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "is_injury": self.is_injury,
            "duration_still": self.duration_still,
            "velocity": self.velocity,
        }


class FallDetector:
    """
    Phát hiện té ngã từ skeleton sequence.

    Logic phân biệt:
    - Té ngã thật: velocity cao + bất động > 2s + tư thế nằm
    - Chơi đùa: velocity thấp hơn + nhanh đứng dậy + chuyển động tiếp
    """

    def __init__(
        self,
        velocity_threshold: float = 50.0,
        still_threshold: float = 2.0,  # seconds
        height_ratio_threshold: float = 0.6,
        buffer_size: int = 30,  # frames
    ):
        self.velocity_threshold = velocity_threshold
        self.still_threshold = still_threshold
        self.height_ratio_threshold = height_ratio_threshold

        self._pose_history: deque = deque(maxlen=buffer_size)
        self._timestamps: deque = deque(maxlen=buffer_size)
        self._fall_start_time: float | None = None
        self._is_fallen = False

    def update(self, poses: PoseResult) -> FallEvent | None:
        """
        Cập nhật với frame mới và kiểm tra té ngã.

        Args:
            poses: Kết quả pose estimation.

        Returns:
            FallEvent nếu phát hiện té ngã, None nếu không.
        """
        if len(poses) == 0:
            return None

        current_time = time.time()
        kps = poses.get_person_keypoints(0)
        body_center = poses.get_body_center(0)

        self._pose_history.append(kps)
        self._timestamps.append(current_time)

        if len(self._pose_history) < 3:
            return None

        # Tính velocity (tốc độ di chuyển body center)
        velocity = self._calc_velocity()

        # Kiểm tra tư thế nằm (body height ratio)
        is_lying = self._check_lying_pose(kps)

        # Phát hiện té ngã (velocity đột ngột + tư thế nằm)
        if not self._is_fallen and velocity > self.velocity_threshold and is_lying:
            self._is_fallen = True
            self._fall_start_time = current_time
            logger.warning(f"Fall detected! velocity={velocity:.1f}")

        # Đánh giá mức độ nghiêm trọng
        if self._is_fallen:
            still_duration = current_time - self._fall_start_time

            # Kiểm tra đã đứng dậy chưa
            if not is_lying:
                self._is_fallen = False
                self._fall_start_time = None
                if still_duration < self.still_threshold:
                    # Đứng dậy nhanh → chơi đùa
                    return FallEvent(
                        timestamp=current_time,
                        confidence=0.6,
                        is_injury=False,
                        duration_still=still_duration,
                        velocity=velocity,
                    )
                return None

            # Nằm bất động quá lâu → chấn thương
            if still_duration >= self.still_threshold:
                return FallEvent(
                    timestamp=current_time,
                    confidence=min(0.5 + still_duration * 0.1, 0.95),
                    is_injury=True,
                    duration_still=still_duration,
                    velocity=velocity,
                )

        return None

    def _calc_velocity(self) -> float:
        """Tính tốc độ di chuyển trung bình body center."""
        if len(self._pose_history) < 2:
            return 0.0

        prev_kps = self._pose_history[-2]
        curr_kps = self._pose_history[-1]

        prev_valid = prev_kps[prev_kps[:, 2] > 0.3][:, :2]
        curr_valid = curr_kps[curr_kps[:, 2] > 0.3][:, :2]

        if len(prev_valid) == 0 or len(curr_valid) == 0:
            return 0.0

        prev_center = prev_valid.mean(axis=0)
        curr_center = curr_valid.mean(axis=0)

        return float(np.linalg.norm(curr_center - prev_center))

    def _check_lying_pose(self, kps: np.ndarray) -> bool:
        """Kiểm tra tư thế nằm dựa trên tỷ lệ cao/rộng skeleton."""
        valid_kps = kps[kps[:, 2] > 0.3][:, :2]
        if len(valid_kps) < 4:
            return False

        height = valid_kps[:, 1].max() - valid_kps[:, 1].min()
        width = valid_kps[:, 0].max() - valid_kps[:, 0].min()

        if height == 0:
            return True

        # Nếu width > height → tư thế nằm
        ratio = height / max(width, 1e-6)
        return ratio < self.height_ratio_threshold
