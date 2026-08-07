"""
X3D-M Model Architecture definition compatible with PyTorchVideo pretrained weights.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import pytorchvideo.models.hub as hub


class ViolenceX3D(nn.Module):
    """
    X3D-M architecture wrapper for binary violence classification.

    Uses PyTorchVideo X3D-M backbone with replaced head (Dropout + Linear classifier).
    Input tensor shape: [B, C, T, H, W]
    Output tensor shape: [B, num_classes] (logits)
    """

    def __init__(self, num_classes: int = 2, dropout: float = 0.3):
        super().__init__()
        self.num_classes = num_classes
        self.dropout = dropout

        # Instantiate X3D-M backbone
        self.backbone = hub.x3d_m(pretrained=False, model_num_class=400)

        # Replace classification head to match fine-tuned checkpoint structure:
        # backbone.blocks[5].proj = Sequential(Dropout(p), Linear(2048, num_classes))
        in_features = self.backbone.blocks[5].proj.in_features
        self.backbone.blocks[5].proj = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input video tensor of shape [B, C, T, H, W]

        Returns:
            Logits tensor of shape [B, num_classes]
        """
        return self.backbone(x)
