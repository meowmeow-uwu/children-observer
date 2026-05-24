"""
Module AI Core - Bộ não AI cho hệ thống AI Child Guardian.

Bao gồm:
- datasets: Quản lý tập dữ liệu ChildSUn và Violence
- models: YOLO26 Object Detection, Pose Estimation, Behavior Classification
- training: Pipeline huấn luyện, đánh giá và xuất mô hình
"""

__all__ = [
    "ObjectDetector",
    "PoseEstimator",
    "BehaviorClassifier",
]


def __getattr__(name: str):
    """Keep package imports light so dataset modules can load without model runtimes."""
    if name == "ObjectDetector":
        from module_ai_core.models.object_detector import ObjectDetector

        return ObjectDetector
    if name == "PoseEstimator":
        from module_ai_core.models.pose_estimator import PoseEstimator

        return PoseEstimator
    if name == "BehaviorClassifier":
        from module_ai_core.models.behavior_classifier import BehaviorClassifier

        return BehaviorClassifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
