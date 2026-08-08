"""
Unit test for ONNX export script.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import torch
import torch.nn as nn

from scripts.export_onnx import export_to_onnx


class DummyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv3d(3, 2, kernel_size=1)

    def forward(self, x):
        # x: [B, C, T, H, W] -> mean over T, H, W -> logits [B, 2]
        return x.mean(dim=[-1, -2, -3])


@patch("scripts.export_onnx.load_model")
def test_export_to_onnx(mock_load_model, tmp_path: Path):
    mock_load_model.return_value = DummyModel()
    output_file = tmp_path / "test_model.onnx"

    exported_path = export_to_onnx(
        output_path=str(output_file),
        opset_version=14,
        dynamic_batch=True,
        verify=False,
    )

    assert exported_path.exists()
    assert exported_path.stat().st_size > 0
