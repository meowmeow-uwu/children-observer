"""
Configuration dataclass for violence detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import torch


@dataclass
class ViolenceDetectionConfig:
    """
    Configuration settings for Violence Detection module.

    Attributes:
        repo_id: Hugging Face repository ID.
        checkpoint_filename: Path inside repository to checkpoint.
        cache_dir: Directory to cache downloaded models.
        clip_length: Number of frames per input video clip (default: 16).
        frame_stride: Frame stride for sliding window processing (default: 8).
        spatial_size: Spatial resolution height/width for model input (default: 224).
        mean: Normalization mean (RGB) (default: [0.45, 0.45, 0.45]).
        std: Normalization std (RGB) (default: [0.225, 0.225, 0.225]).
        violence_threshold: Probability threshold to classify violence (default: 0.4).
        smoothing_window: Temporal window size for smoothing predictions (default: 5).
        smoothing_method: Method for temporal smoothing ('moving_average' or 'median').
        alert_min_consecutive: Minimum consecutive positive predictions before alert (default: 2).
        device: 'auto', 'cuda', or 'cpu'.
    """
    repo_id: str = "visionlab-ai/school-violence-detection-models"
    checkpoint_filename: str = "final/final_x3d_realtime.pt"
    cache_dir: str | None = None

    clip_length: int = 16
    frame_stride: int = 8
    spatial_size: int = 224

    mean: list[float] = field(default_factory=lambda: [0.45, 0.45, 0.45])
    std: list[float] = field(default_factory=lambda: [0.225, 0.225, 0.225])

    violence_threshold: float = 0.4

    smoothing_window: int = 5
    smoothing_method: str = "moving_average"
    alert_min_consecutive: int = 2

    device: str = "auto"

    backend: str = "pytorch"  # 'pytorch', 'onnx', or 'auto'
    onnx_model_path: str = "weights/x3d_violence.onnx"
    onnx_providers: list[str] | None = None

    enable_person_filter: bool = False
    min_persons_required: int = 2
    person_conf_threshold: float = 0.35
    person_filter_backend: str = "auto"  # 'auto', 'yolo', or 'hog'

    def get_resolved_device(self) -> torch.device:
        """
        Resolve 'auto' device selection.
        If 'cuda' is requested or 'auto' resolves to CUDA when available, returns torch.device('cuda').
        Otherwise returns torch.device('cpu').
        """
        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)
