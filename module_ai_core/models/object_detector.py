"""
YOLO26 Object Detector.

Wrapper cho Ultralytics YOLO26 để phát hiện vật thể nguy hiểm
trong môi trường gia đình: dao, kéo, nĩa, phích nước, ổ điện...

Features:
- Train trên dataset ChildSUn
- Predict với confidence threshold tùy chỉnh
- Export sang ONNX/TensorRT cho edge deployment
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from configs.settings import get_settings
from module_ai_core.datasets.childsun_loader import CHILDSUN_CLASSES


class DetectionResult:
    """Kết quả phát hiện vật thể cho một frame."""

    def __init__(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        class_ids: np.ndarray,
        class_names: list[str],
    ):
        """
        Args:
            boxes: np.ndarray shape (N, 4) - [x1, y1, x2, y2] absolute coords
            scores: np.ndarray shape (N,) - confidence scores
            class_ids: np.ndarray shape (N,) - class IDs
            class_names: list[str] - corresponding class names
        """
        self.boxes = boxes
        self.scores = scores
        self.class_ids = class_ids
        self.class_names = class_names

    def __len__(self) -> int:
        return len(self.boxes)

    def filter_by_class(self, target_classes: list[str]) -> "DetectionResult":
        """Lọc kết quả theo danh sách class cụ thể."""
        mask = np.array([name in target_classes for name in self.class_names])
        return DetectionResult(
            boxes=self.boxes[mask],
            scores=self.scores[mask],
            class_ids=self.class_ids[mask],
            class_names=[n for n, m in zip(self.class_names, mask) if m],
        )

    def get_dangerous_objects(self) -> "DetectionResult":
        """Lọc chỉ các vật thể nguy hiểm (không bao gồm 'child')."""
        dangerous = [c for c in CHILDSUN_CLASSES if c != "child"]
        return self.filter_by_class(dangerous)

    def get_children(self) -> "DetectionResult":
        """Lọc chỉ phát hiện trẻ em."""
        return self.filter_by_class(["child"])

    def to_dict(self) -> list[dict]:
        """Chuyển đổi sang list of dicts."""
        results = []
        for i in range(len(self)):
            results.append({
                "box": self.boxes[i].tolist(),
                "score": float(self.scores[i]),
                "class_id": int(self.class_ids[i]),
                "class_name": self.class_names[i],
            })
        return results


class ObjectDetector:
    """
    YOLO26 Object Detector wrapper.

    Phát hiện vật thể nguy hiểm (dao, kéo, nĩa, phích nước, ổ điện)
    và trẻ em trong khung hình camera.

    Args:
        model_path: Đường dẫn tới file weights (.pt).
        device: Device cho inference ('cuda:0', 'cpu').
        conf_threshold: Ngưỡng confidence tối thiểu.
        iou_threshold: Ngưỡng IoU cho NMS.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        device: str | None = None,
        conf_threshold: float | None = None,
        iou_threshold: float | None = None,
    ):
        settings = get_settings()
        self.model_path = Path(model_path) if model_path else settings.yolo_model_path
        self.device = device or settings.inference_device
        self.conf_threshold = conf_threshold or settings.inference_conf_threshold
        self.iou_threshold = iou_threshold or settings.inference_iou_threshold
        self.classes = CHILDSUN_CLASSES

        self._model = None
        self._is_loaded = False

    def load(self) -> None:
        """Load YOLO26 model vào memory."""
        try:
            from ultralytics import YOLO

            if self.model_path.exists():
                self._model = YOLO(str(self.model_path))
                logger.info(f"Loaded YOLO model from: {self.model_path}")
            else:
                # Load pretrained YOLO26n nếu chưa có weights custom
                logger.warning(
                    f"Custom weights not found: {self.model_path}. "
                    "Loading pretrained YOLO26n..."
                )
                self._model = YOLO("yolo26n.pt")

            self._model.to(self.device)
            self._is_loaded = True
            logger.info(f"ObjectDetector ready | device={self.device}")

        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def predict(self, frame: np.ndarray, verbose: bool = False) -> DetectionResult:
        """
        Phát hiện vật thể trong một frame.

        Args:
            frame: np.ndarray (H, W, 3) BGR image.
            verbose: In chi tiết inference.

        Returns:
            DetectionResult chứa boxes, scores, class_ids.
        """
        if not self._is_loaded:
            self.load()

        results = self._model.predict(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=verbose,
            device=self.device,
        )

        # Parse results
        result = results[0]
        boxes = result.boxes

        if len(boxes) == 0:
            return DetectionResult(
                boxes=np.zeros((0, 4)),
                scores=np.zeros(0),
                class_ids=np.zeros(0, dtype=int),
                class_names=[],
            )

        return DetectionResult(
            boxes=boxes.xyxy.cpu().numpy(),
            scores=boxes.conf.cpu().numpy(),
            class_ids=boxes.cls.cpu().numpy().astype(int),
            class_names=[
                self._model.names.get(int(c), f"class_{int(c)}")
                for c in boxes.cls.cpu().numpy()
            ],
        )

    def train(
        self,
        data_yaml: str | Path,
        epochs: int = 100,
        batch_size: int = 16,
        img_size: int = 640,
        name: str = "childsun_yolo26",
        **kwargs: Any,
    ) -> dict:
        """
        Huấn luyện YOLO26 trên dataset ChildSUn.

        Args:
            data_yaml: Đường dẫn tới file data.yaml.
            epochs: Số epoch huấn luyện.
            batch_size: Batch size.
            img_size: Kích thước ảnh.
            name: Tên experiment.

        Returns:
            Dict chứa training metrics.
        """
        if not self._is_loaded:
            self.load()

        logger.info(
            f"Starting training | epochs={epochs} | batch={batch_size} | "
            f"img_size={img_size}"
        )

        results = self._model.train(
            data=str(data_yaml),
            epochs=epochs,
            batch=batch_size,
            imgsz=img_size,
            name=name,
            device=self.device,
            patience=20,  # Early stopping
            save=True,
            save_period=10,
            plots=True,
            **kwargs,
        )

        logger.info(f"Training completed: {name}")
        return results

    def validate(self, data_yaml: str | Path, **kwargs: Any) -> dict:
        """Đánh giá mô hình trên validation set."""
        if not self._is_loaded:
            self.load()

        results = self._model.val(
            data=str(data_yaml),
            device=self.device,
            **kwargs,
        )
        return results

    def export(
        self,
        format: str = "onnx",
        output_dir: str | Path | None = None,
        **kwargs: Any,
    ) -> Path:
        """
        Export mô hình sang format khác cho edge deployment.

        Args:
            format: Format xuất ('onnx', 'tensorrt', 'openvino', 'engine').
            output_dir: Thư mục lưu model đã export.

        Returns:
            Path tới file model đã export.
        """
        if not self._is_loaded:
            self.load()

        logger.info(f"Exporting model to {format}...")
        export_path = self._model.export(format=format, **kwargs)
        logger.info(f"Model exported to: {export_path}")

        return Path(export_path)

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
