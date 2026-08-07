"""
Type definitions for violence detection module.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ViolencePrediction:
    """
    Prediction result from ViolenceDetector.

    Attributes:
        violence: Whether violence is detected after thresholding & smoothing.
        confidence: Post-smoothing probability (or raw probability if smoothing disabled).
        raw_probability: Raw probability of violence from model softmax.
        smoothed_probability: Temporal smoothed probability of violence.
        timestamp: Video/stream timestamp in seconds.
        inference_ms: Inference latency in milliseconds.
    """
    violence: bool
    confidence: float
    raw_probability: float
    smoothed_probability: float | None = None
    timestamp: float | None = None
    inference_ms: float | None = None
