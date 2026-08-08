"""
Unit test for Strategy Pattern Inference Engines.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import torch

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.inference.engine import (
    BaseInferenceEngine,
    PyTorchInferenceEngine,
    InferenceEngineFactory,
)
from violence_detection.inference.detector import ViolenceDetector


@patch("violence_detection.inference.engine.load_model")
def test_pytorch_strategy(mock_load_model):
    mock_model = MagicMock()
    # Mock output logits shape [1, 2] -> index 1 softmax
    mock_model.return_value = torch.tensor([[1.0, 3.0]])
    mock_load_model.return_value = mock_model

    config = ViolenceDetectionConfig(backend="pytorch", device="cpu")
    detector = ViolenceDetector(config)

    assert isinstance(detector.engine, PyTorchInferenceEngine)

    dummy_frames = [np.zeros((224, 224, 3), dtype=np.uint8) for _ in range(16)]
    result = detector.predict_clip(dummy_frames)

    assert result.raw_probability > 0.5
    assert result.inference_ms is not None


def test_factory_invalid_backend():
    config = ViolenceDetectionConfig(backend="invalid_backend")
    with pytest.raises(ValueError, match="Unsupported inference backend"):
        InferenceEngineFactory.create_engine(config)
