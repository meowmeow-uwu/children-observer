"""
Preprocessing components.
"""

from violence_detection.preprocessing.video import preprocess_frames
from violence_detection.preprocessing.person_filter import PersonFilter

__all__ = ["preprocess_frames", "PersonFilter"]
