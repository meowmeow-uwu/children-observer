"""
Model loader for downloading checkpoint and initializing ViolenceX3D model.
"""

from __future__ import annotations

import os
from pathlib import Path
import torch
from loguru import logger
from huggingface_hub import hf_hub_download

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.model.x3d import ViolenceX3D


def load_model(config: ViolenceDetectionConfig) -> torch.nn.Module:
    """
    Download checkpoint from HuggingFace and load ViolenceX3D model.

    Args:
        config: ViolenceDetectionConfig object.

    Returns:
        Loaded PyTorch model in eval mode on resolved device.
    """
    device = config.get_resolved_device()

    logger.info(
        f"Downloading/loading checkpoint '{config.checkpoint_filename}' "
        f"from HF repo '{config.repo_id}'..."
    )

    try:
        checkpoint_path = hf_hub_download(
            repo_id=config.repo_id,
            filename=config.checkpoint_filename,
            cache_dir=config.cache_dir,
        )
    except Exception as err:
        logger.error(f"Failed to download checkpoint from Hugging Face: {err}")
        raise RuntimeError(f"Could not download checkpoint from {config.repo_id}: {err}") from err

    logger.info(f"Checkpoint location: {checkpoint_path}")

    # PyTorch 2.6+ weights_only fallback handling for PyTorch dict checkpoints with scalar types
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except Exception as err:
        logger.error(f"Failed to load checkpoint file at {checkpoint_path}: {err}")
        raise RuntimeError(f"Failed to parse checkpoint file: {err}") from err

    if isinstance(checkpoint, dict) and "model" in checkpoint:
        state_dict = checkpoint["model"]
    elif isinstance(checkpoint, dict):
        state_dict = checkpoint
    else:
        state_dict = checkpoint.state_dict() if hasattr(checkpoint, "state_dict") else checkpoint

    model = ViolenceX3D(num_classes=2)

    try:
        missing_keys, unexpected_keys = model.load_state_dict(state_dict, strict=True)
        if missing_keys or unexpected_keys:
            logger.warning(
                f"State dict mismatch - Missing: {missing_keys}, Unexpected: {unexpected_keys}"
            )
    except Exception as err:
        logger.error(f"Strict state_dict load failed: {err}")
        raise RuntimeError(f"Incompatible state_dict format in checkpoint: {err}") from err

    model.to(device)
    model.eval()

    # Freeze all parameters for inference
    for param in model.parameters():
        param.requires_grad = False

    logger.info(f"Successfully loaded ViolenceX3D model onto device: {device}")
    return model
