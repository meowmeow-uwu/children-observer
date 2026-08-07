"""
Video preprocessing pipelines for X3D model input.
"""

from __future__ import annotations

import cv2
import numpy as np
import torch


def preprocess_frames(
    frames: list[np.ndarray],
    expected_clip_length: int = 16,
    spatial_size: int = 224,
    mean: list[float] | None = None,
    std: list[float] | None = None,
) -> torch.Tensor:
    """
    Preprocess a sequence of OpenCV video frames into a PyTorch tensor for X3D-M.

    Flow:
        OpenCV BGR -> RGB -> Resize -> float32 [0, 1] -> Normalize -> T H W C -> C T H W -> B C T H W

    Args:
        frames: List of BGR numpy image arrays (frames).
        expected_clip_length: Expected number of frames (default: 16).
        spatial_size: Target height and width in pixels (default: 224).
        mean: Normalization RGB mean values (default: [0.45, 0.45, 0.45]).
        std: Normalization RGB std values (default: [0.225, 0.225, 0.225]).

    Returns:
        Tensor of shape [1, 3, T, H, W] in float32 format.

    Raises:
        ValueError: If len(frames) != expected_clip_length or frames list is empty.
    """
    if not frames:
        raise ValueError("Cannot preprocess empty frames list.")

    if len(frames) != expected_clip_length:
        raise ValueError(
            f"Invalid clip length: expected {expected_clip_length} frames, got {len(frames)}."
        )

    if mean is None:
        mean = [0.45, 0.45, 0.45]
    if std is None:
        std = [0.225, 0.225, 0.225]

    mean_tensor = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
    std_tensor = np.array(std, dtype=np.float32).reshape(1, 1, 3)

    processed_frames = []
    for idx, frame in enumerate(frames):
        if frame is None or frame.size == 0:
            raise ValueError(f"Frame at index {idx} is invalid or empty.")

        # Convert BGR to RGB
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        elif len(frame.shape) == 2:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            rgb_frame = frame

        # Resize to target spatial size
        resized_frame = cv2.resize(
            rgb_frame, (spatial_size, spatial_size), interpolation=cv2.INTER_LINEAR
        )

        # Scale to [0, 1] float32
        norm_frame = resized_frame.astype(np.float32) / 255.0

        # Normalize with mean and std
        norm_frame = (norm_frame - mean_tensor) / std_tensor

        processed_frames.append(norm_frame)

    # Stack along temporal dimension: [T, H, W, C]
    clip_np = np.stack(processed_frames, axis=0)

    # Convert to PyTorch Tensor: [T, H, W, C] -> torch.Tensor
    clip_tensor = torch.from_numpy(clip_np)

    # Permute from [T, H, W, C] to [C, T, H, W]
    clip_tensor = clip_tensor.permute(3, 0, 1, 2)

    # Add batch dimension: [1, C, T, H, W]
    clip_tensor = clip_tensor.unsqueeze(0)

    return clip_tensor
