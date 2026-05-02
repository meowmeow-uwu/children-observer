"""
Model Exporter.

Export mô hình sang các format tối ưu cho edge deployment:
- ONNX (cross-platform)
- TensorRT (NVIDIA GPU/Jetson)
- OpenVINO (Intel)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from loguru import logger

from module_ai_core.models.object_detector import ObjectDetector
from module_ai_core.models.pose_estimator import PoseEstimator


class ModelExporter:
    """Export models cho edge deployment."""

    def __init__(self, output_dir: str | Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path("./weights/exported")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_detector(
        self,
        model_path: str | Path,
        format: Literal["onnx", "engine", "openvino"] = "onnx",
        img_size: int = 640,
        half: bool = False,
    ) -> Path:
        """Export YOLO detector."""
        logger.info(f"Exporting detector to {format}...")
        detector = ObjectDetector(model_path=model_path)
        detector.load()
        return detector.export(format=format, imgsz=img_size, half=half)

    def export_pose(
        self,
        model_path: str | Path,
        format: Literal["onnx", "engine", "openvino"] = "onnx",
        img_size: int = 640,
        half: bool = False,
    ) -> Path:
        """Export YOLO-Pose model."""
        logger.info(f"Exporting pose model to {format}...")
        estimator = PoseEstimator(model_path=model_path)
        estimator.load()
        return estimator.export(format=format, imgsz=img_size, half=half)

    def export_all(self, format: str = "onnx") -> dict[str, Path]:
        """Export tất cả models."""
        results = {}
        from configs.settings import get_settings
        settings = get_settings()

        if settings.yolo_model_path.exists():
            results["detector"] = self.export_detector(settings.yolo_model_path, format)

        if settings.pose_model_path.exists():
            results["pose"] = self.export_pose(settings.pose_model_path, format)

        logger.info(f"Exported {len(results)} models to {format}")
        return results
