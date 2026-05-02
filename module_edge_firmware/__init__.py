"""
Module Edge Firmware - Xử lý AI tại Camera/Edge.

Pipeline: Capture → Preprocess → Inference → Risk Analysis → Alert
"""

from module_edge_firmware.pipeline import EdgePipeline

__all__ = ["EdgePipeline"]
