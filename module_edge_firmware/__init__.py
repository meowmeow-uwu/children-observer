"""
Module Edge Firmware - Xử lý AI tại Camera/Edge.

Pipeline: Capture → Preprocess → Inference → Risk Analysis → Alert
"""

__all__ = ["EdgePipeline"]


def __getattr__(name: str):
    """Lazy-load heavy pipeline dependencies only when requested."""
    if name == "EdgePipeline":
        from module_edge_firmware.pipeline import EdgePipeline

        return EdgePipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
