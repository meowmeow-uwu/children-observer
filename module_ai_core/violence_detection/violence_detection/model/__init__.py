"""
Model components for Violence Detection.
"""

from violence_detection.model.x3d import ViolenceX3D
from violence_detection.model.loader import load_model

__all__ = ["ViolenceX3D", "load_model"]
