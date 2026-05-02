"""AI model wrappers for object detection, pose estimation, and behavior classification."""

from module_ai_core.models.object_detector import ObjectDetector
from module_ai_core.models.pose_estimator import PoseEstimator
from module_ai_core.models.behavior_classifier import BehaviorClassifier

__all__ = ["ObjectDetector", "PoseEstimator", "BehaviorClassifier"]
