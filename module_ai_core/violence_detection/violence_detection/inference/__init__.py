"""
Inference & smoothing components.
"""

from violence_detection.inference.smoothing import TemporalSmoother
from violence_detection.inference.detector import ViolenceDetector

__all__ = ["TemporalSmoother", "ViolenceDetector"]
