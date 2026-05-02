"""
Mock AI Service - Giả lập kết quả AI cho team Edge (P2).

Sử dụng script này để kiểm tra logic Risk Assessor và Alert Manager 
khi team AI chưa hoàn thành model thật.
"""

import numpy as np
from module_edge_firmware.inference.multi_task_runner import FrameAnalysis, Detections, Poses, Behavior

class MockAIService:
    def __init__(self):
        self.frame_count = 0

    def analyze(self, frame: np.ndarray) -> FrameAnalysis:
        self.frame_count += 1
        h, w = frame.shape[:2]
        
        # Giả lập: Cứ mỗi 100 frames thì tạo một tình huống nguy hiểm
        is_incident = (self.frame_count % 100 == 0)
        
        # 1. Mock Detections (Trẻ em + Dao)
        det = Detections(
            boxes=np.array([[100, 100, 200, 300], [210, 110, 250, 150]]),
            confidences=np.array([0.9, 0.85]),
            class_ids=np.array([0, 1]), # 0: child, 1: knife
            class_names=["child", "knife"]
        ) if is_incident else Detections(
            boxes=np.array([[100, 100, 200, 300]]),
            confidences=np.array([0.9]),
            class_ids=np.array([0]),
            class_names=["child"]
        )

        # 2. Mock Poses (Skeleton đơn giản)
        poses = Poses(
            keypoints=np.zeros((1, 17, 3)),
            confidences=np.array([0.9])
        )

        # 3. Mock Behavior
        behavior = Behavior(
            class_id=1 if is_incident else 0,
            class_name="violence" if is_incident else "normal",
            confidence=0.95 if is_incident else 0.99
        )

        return FrameAnalysis(
            detections=det,
            poses=poses,
            behavior=behavior,
            has_children=True,
            has_dangerous_objects=is_incident,
            has_violence=is_incident
        )
