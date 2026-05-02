"""
Module AI Core - Bộ não AI cho hệ thống AI Child Guardian.

Bao gồm:
- datasets: Quản lý tập dữ liệu ChildSUn và Violence
- models: YOLO26 Object Detection, Pose Estimation, Behavior Classification
- training: Pipeline huấn luyện, đánh giá và xuất mô hình
"""

from module_ai_core.models.object_detector import ObjectDetector
from module_ai_core.models.pose_estimator import PoseEstimator
from module_ai_core.models.behavior_classifier import BehaviorClassifier

__all__ = [
    "ObjectDetector",
    "PoseEstimator",
    "BehaviorClassifier",
]
