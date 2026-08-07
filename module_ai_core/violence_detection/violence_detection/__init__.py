"""
Violence Detection Module using Pretrained X3D-M.
"""

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.types import ViolencePrediction
from violence_detection.inference.detector import ViolenceDetector
from violence_detection.stream.capture import VideoStream

__all__ = [
    "ViolenceDetectionConfig",
    "ViolencePrediction",
    "ViolenceDetector",
    "VideoStream",
]
