"""
Unit tests for ViolenceDetector using mock model.
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import torch
import torch.nn as nn

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.inference.detector import ViolenceDetector
from violence_detection.types import ViolencePrediction


class MockModel(nn.Module):
    """Mock PyTorch model returning specified logits."""

    def __init__(self, logits: torch.Tensor):
        super().__init__()
        self.logits = logits

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.logits


def test_predict_clip_non_violence_logits():
    """Logits [5.0, 1.0] -> Softmax for class 1 is ~0.018 (Non-Violence)."""
    mock_logits = torch.tensor([[5.0, 1.0]])  # Non-violence logits

    with patch("violence_detection.inference.detector.load_model") as mock_load:
        mock_load.return_value = MockModel(mock_logits)

        config = ViolenceDetectionConfig(violence_threshold=0.4, device="cpu")
        detector = ViolenceDetector(config)

        dummy_frames = [np.zeros((224, 224, 3), dtype=np.uint8) for _ in range(16)]
        pred = detector.predict_clip(dummy_frames, timestamp=1.5)

        assert isinstance(pred, ViolencePrediction)
        assert pred.violence is False
        assert pred.raw_probability < 0.1
        assert pred.timestamp == 1.5


def test_predict_clip_violence_logits():
    """Logits [1.0, 5.0] -> Softmax for class 1 is ~0.982 (Violence)."""
    mock_logits = torch.tensor([[1.0, 5.0]])  # Violence logits

    with patch("violence_detection.inference.detector.load_model") as mock_load:
        mock_load.return_value = MockModel(mock_logits)

        # Min consecutive = 1 for immediate alert testing
        config = ViolenceDetectionConfig(
            violence_threshold=0.4,
            alert_min_consecutive=1,
            device="cpu",
        )
        detector = ViolenceDetector(config)

        dummy_frames = [np.full((224, 224, 3), 200, dtype=np.uint8) for _ in range(16)]
        pred = detector.predict_clip(dummy_frames, timestamp=2.0)

        assert isinstance(pred, ViolencePrediction)
        assert pred.violence is True
        assert pred.raw_probability > 0.9
        assert pred.confidence > 0.9


def test_detector_stream_buffer():
    """Verify detector process_stream iterates clips properly with sliding window."""
    mock_logits = torch.tensor([[1.0, 5.0]])

    with patch("violence_detection.inference.detector.load_model") as mock_load:
        mock_load.return_value = MockModel(mock_logits)

        config = ViolenceDetectionConfig(clip_length=16, frame_stride=8, device="cpu")
        detector = ViolenceDetector(config)

        # Mock stream yielding 32 frames (should generate clips at frame 16 and frame 24, 32)
        mock_frames = [(np.zeros((224, 224, 3), dtype=np.uint8), i * 0.1) for i in range(32)]
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_frames
        mock_stream.__exit__.return_value = None

        results = list(detector.process_stream(stream=mock_stream))

        # Expected predictions triggered at clip 16 (stride 8 interval), 24, 32 -> 3 predictions
        assert len(results) >= 2
        for res in results:
            assert isinstance(res, ViolencePrediction)
