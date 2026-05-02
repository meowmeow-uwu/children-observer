"""
Behavior Classifier - ST-GCN based.

Phân loại hành vi bạo lực vs bình thường từ skeleton sequences.
Sử dụng Spatial-Temporal Graph Convolutional Network.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from loguru import logger

from configs.settings import get_settings
from module_ai_core.datasets.violence_loader import VIOLENCE_CLASSES


class GraphConvolution(nn.Module):
    """Spatial Graph Convolution layer."""

    def __init__(self, in_channels: int, out_channels: int, num_joints: int = 17):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        self.adj = nn.Parameter(torch.randn(num_joints, num_joints) * 0.01)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T, V) - batch, channels, time, vertices
        adj = torch.softmax(self.adj, dim=-1)
        x = torch.einsum("bctv,vw->bctw", x, adj)
        x = self.conv(x)
        x = self.bn(x)
        return self.relu(x)


class STGCNBlock(nn.Module):
    """Spatial-Temporal GCN block."""

    def __init__(self, in_ch: int, out_ch: int, num_joints: int = 17, stride: int = 1):
        super().__init__()
        self.gcn = GraphConvolution(in_ch, out_ch, num_joints)
        self.tcn = nn.Sequential(
            nn.Conv2d(out_ch, out_ch, kernel_size=(9, 1), padding=(4, 0), stride=(stride, 1)),
            nn.BatchNorm2d(out_ch),
        )
        self.relu = nn.ReLU(inplace=True)
        self.residual = (
            nn.Sequential(nn.Conv2d(in_ch, out_ch, 1, stride=(stride, 1)), nn.BatchNorm2d(out_ch))
            if in_ch != out_ch or stride != 1
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.residual(x)
        x = self.gcn(x)
        x = self.tcn(x)
        return self.relu(x + res)


class STGCN(nn.Module):
    """ST-GCN model cho behavior classification."""

    def __init__(self, num_classes: int = 9, in_channels: int = 3, num_joints: int = 17):
        super().__init__()
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)
        self.blocks = nn.Sequential(
            STGCNBlock(in_channels, 64, num_joints),
            STGCNBlock(64, 64, num_joints),
            STGCNBlock(64, 128, num_joints, stride=2),
            STGCNBlock(128, 128, num_joints),
            STGCNBlock(128, 256, num_joints, stride=2),
            STGCNBlock(256, 256, num_joints),
        )
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T, V)
        B, C, T, V = x.shape
        x_bn = x.permute(0, 3, 1, 2).reshape(B, V * C, T)
        x_bn = self.data_bn(x_bn)
        x = x_bn.reshape(B, V, C, T).permute(0, 2, 3, 1)
        x = self.blocks(x)
        x = self.pool(x).squeeze(-1).squeeze(-1)
        return self.fc(x)


class BehaviorResult:
    """Kết quả phân loại hành vi."""

    def __init__(self, class_id: int, class_name: str, confidence: float, probabilities: dict):
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = confidence
        self.probabilities = probabilities

    @property
    def is_violent(self) -> bool:
        return self.class_name not in ("normal", "fall_play")

    @property
    def is_fall(self) -> bool:
        return self.class_name in ("fall_injury", "fall_play")

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "is_violent": self.is_violent,
            "is_fall": self.is_fall,
        }


class BehaviorClassifier:
    """
    ST-GCN Behavior Classifier.

    Phân loại hành vi từ skeleton sequence: bạo lực, té ngã, bình thường.
    """

    def __init__(self, model_path=None, device=None, sequence_length: int = 30):
        settings = get_settings()
        self.model_path = Path(model_path) if model_path else settings.behavior_model_path
        self.device = device or settings.inference_device
        self.sequence_length = sequence_length
        self.classes = VIOLENCE_CLASSES
        self._model: STGCN | None = None
        self._is_loaded = False

    def load(self) -> None:
        self._model = STGCN(num_classes=len(self.classes))
        if self.model_path.exists():
            state = torch.load(str(self.model_path), map_location=self.device, weights_only=True)
            self._model.load_state_dict(state)
            logger.info(f"Loaded behavior model: {self.model_path}")
        else:
            logger.warning(f"Behavior weights not found: {self.model_path}. Using random init.")
        self._model.to(self.device)
        self._model.eval()
        self._is_loaded = True

    def predict(self, skeleton_sequence: np.ndarray) -> BehaviorResult:
        """
        Phân loại hành vi từ skeleton sequence.

        Args:
            skeleton_sequence: shape (T, 17, 3) hoặc (B, T, 17, 3)
        """
        if not self._is_loaded:
            self.load()

        if skeleton_sequence.ndim == 3:
            skeleton_sequence = skeleton_sequence[np.newaxis, ...]

        # (B, T, V, C) -> (B, C, T, V)
        x = torch.from_numpy(skeleton_sequence).float().permute(0, 3, 1, 2).to(self.device)

        with torch.no_grad():
            logits = self._model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        class_id = int(probs.argmax())
        return BehaviorResult(
            class_id=class_id,
            class_name=self.classes[class_id],
            confidence=float(probs[class_id]),
            probabilities={name: float(p) for name, p in zip(self.classes, probs)},
        )

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
