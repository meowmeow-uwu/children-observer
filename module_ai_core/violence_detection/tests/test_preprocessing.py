"""
Unit tests for video preprocessing functions.
"""

import pytest
import numpy as np
import torch
from violence_detection.preprocessing.video import preprocess_frames


def test_preprocess_frames_shape_and_dtype():
    """Verify preprocessed clip output tensor shape, dtype, and batch size."""
    dummy_frames = [np.full((480, 640, 3), 128, dtype=np.uint8) for _ in range(16)]
    
    tensor = preprocess_frames(
        frames=dummy_frames,
        expected_clip_length=16,
        spatial_size=224,
        mean=[0.45, 0.45, 0.45],
        std=[0.225, 0.225, 0.225],
    )

    assert isinstance(tensor, torch.Tensor)
    assert tensor.dtype == torch.float32
    assert tensor.shape == (1, 3, 16, 224, 224)


def test_preprocess_frames_channel_conversion():
    """Verify BGR to RGB conversion by checking blue channel becomes red in RGB tensor."""
    # Create pure blue frame in OpenCV BGR format: B=255, G=0, R=0
    bgr_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    bgr_frame[:, :, 0] = 255  # Blue channel in BGR

    dummy_frames = [bgr_frame.copy() for _ in range(16)]

    tensor = preprocess_frames(
        frames=dummy_frames,
        expected_clip_length=16,
        spatial_size=224,
        mean=[0.0, 0.0, 0.0],
        std=[1.0, 1.0, 1.0],
    )

    # Output shape: [1, C, T, H, W]
    # Channel 0 should be Red (0.0), Channel 2 should be Blue (1.0)
    red_channel_mean = tensor[0, 0, :, :, :].mean().item()
    blue_channel_mean = tensor[0, 2, :, :, :].mean().item()

    assert pytest.approx(red_channel_mean, abs=1e-3) == 0.0
    assert pytest.approx(blue_channel_mean, abs=1e-3) == 1.0


def test_preprocess_frames_invalid_length():
    """Verify ValueError is raised if frames list has wrong length."""
    too_few_frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(10)]
    with pytest.raises(ValueError, match="Invalid clip length"):
        preprocess_frames(too_few_frames, expected_clip_length=16)

    empty_frames = []
    with pytest.raises(ValueError, match="Cannot preprocess empty frames list"):
        preprocess_frames(empty_frames, expected_clip_length=16)
