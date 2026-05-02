"""
Proximity Detector - Phát hiện trẻ đưa vật vào miệng.

Tính khoảng cách giữa keypoints tay (wrist) và miệng (nose proxy)
để cảnh báo khi trẻ cầm vật nguy hiểm đưa gần miệng.
"""

from __future__ import annotations

import numpy as np
from loguru import logger

from module_ai_core.models.pose_estimator import PoseResult, Keypoint
from module_ai_core.models.object_detector import DetectionResult


class ProximityAlert:
    """Thông tin cảnh báo proximity."""

    def __init__(self, person_idx: int, hand: str, distance: float,
                 nearby_object: str | None = None):
        self.person_idx = person_idx
        self.hand = hand  # "left" or "right"
        self.distance = distance
        self.nearby_object = nearby_object

    def to_dict(self) -> dict:
        return {
            "person_idx": self.person_idx,
            "hand": self.hand,
            "distance": self.distance,
            "nearby_object": self.nearby_object,
        }


class ProximityDetector:
    """
    Phát hiện hand-mouth proximity.

    Cảnh báo khi tay trẻ (đặc biệt khi cầm vật nguy hiểm) đưa gần miệng.
    """

    def __init__(self, distance_threshold: float = 80.0, min_confidence: float = 0.3):
        self.distance_threshold = distance_threshold  # pixels
        self.min_confidence = min_confidence

    def check(
        self,
        poses: PoseResult,
        detections: DetectionResult | None = None,
    ) -> list[ProximityAlert]:
        """
        Kiểm tra hand-mouth proximity cho tất cả người trong frame.

        Args:
            poses: Kết quả pose estimation.
            detections: Kết quả object detection (tùy chọn).
        """
        alerts = []

        for person_idx in range(len(poses)):
            kps = poses.get_person_keypoints(person_idx)

            # Check confidence
            nose_conf = kps[Keypoint.NOSE][2]
            if nose_conf < self.min_confidence:
                continue

            mouth_pos = poses.get_mouth_position(person_idx)
            left_wrist, right_wrist = poses.get_hand_positions(person_idx)

            # Check left hand
            left_conf = kps[Keypoint.LEFT_WRIST][2]
            if left_conf >= self.min_confidence:
                dist = np.linalg.norm(left_wrist - mouth_pos)
                if dist < self.distance_threshold:
                    nearby = self._find_nearby_object(left_wrist, detections)
                    alerts.append(ProximityAlert(person_idx, "left", float(dist), nearby))

            # Check right hand
            right_conf = kps[Keypoint.RIGHT_WRIST][2]
            if right_conf >= self.min_confidence:
                dist = np.linalg.norm(right_wrist - mouth_pos)
                if dist < self.distance_threshold:
                    nearby = self._find_nearby_object(right_wrist, detections)
                    alerts.append(ProximityAlert(person_idx, "right", float(dist), nearby))

        return alerts

    def _find_nearby_object(
        self,
        hand_pos: np.ndarray,
        detections: DetectionResult | None,
        search_radius: float = 100.0,
    ) -> str | None:
        """Tìm vật thể nguy hiểm gần tay nhất."""
        if detections is None or len(detections) == 0:
            return None

        dangerous = detections.get_dangerous_objects()
        if len(dangerous) == 0:
            return None

        for i in range(len(dangerous)):
            box = dangerous.boxes[i]
            box_center = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
            dist = np.linalg.norm(hand_pos - box_center)
            if dist < search_radius:
                return dangerous.class_names[i]

        return None
