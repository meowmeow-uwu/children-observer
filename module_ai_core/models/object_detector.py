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

import time
import cv2
from pathlib import Path
from typing import Any, TYPE_CHECKING
import numpy as np
from loguru import logger
from configs.settings import get_settings
from module_ai_core.datasets.childsun_loader import CHILDSUN_CLASSES

if TYPE_CHECKING:
    from module_edge_firmware.inference.engine import BaseInferenceEngine
class DetectionResult:
    """Kết quả phát hiện vật thể cho một frame."""

    def __init__(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        class_ids: np.ndarray,
        class_names: list[str],
        inference_time_ms: float = 0.0,
    ):
        """
        Args:
            boxes: np.ndarray shape (N, 4) - [x1, y1, x2, y2] absolute coords
            scores: np.ndarray shape (N,) - confidence scores
            class_ids: np.ndarray shape (N,) - class IDs
            class_names: list[str] - corresponding class names
            inference_time_ms: float - thời gian inference (ms)
        """
        self.boxes = boxes
        self.scores = scores
        self.class_ids = class_ids
        self.class_names = class_names
        self.inference_time_ms = inference_time_ms

    def __len__(self) -> int:
        return len(self.boxes)

    def filter_by_class(self, target_classes: list[str]) -> "DetectionResult":
        """Lọc kết quả theo danh sách class cụ thể."""
        mask = np.array([name in target_classes for name in self.class_names], dtype=bool)
        return DetectionResult(
            boxes=self.boxes[mask],
            scores=self.scores[mask],
            class_ids=self.class_ids[mask],
            class_names=[n for n, m in zip(self.class_names, mask) if m],
            inference_time_ms=self.inference_time_ms,
        )

    def get_dangerous_objects(self) -> "DetectionResult":
        """Lọc chỉ các vật thể nguy hiểm (không bao gồm 'child')."""
        dangerous = ["knife", "socket", "scissors"] 
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
        engine_type: str = "yolo", # "yolo", "onnx", "tensorrt", "openvino"
    ):
        settings = get_settings()
        self.model_path = Path(model_path) if model_path else settings.yolo_model_path
        self.device = device or settings.inference_device
        self.conf_threshold = conf_threshold or settings.inference_conf_threshold
        self.iou_threshold = iou_threshold or settings.inference_iou_threshold
        self.engine_type = engine_type
        self.classes = CHILDSUN_CLASSES

        self._model = None
        self._engine: "BaseInferenceEngine | None" = None
        from module_edge_firmware.ingestion.preprocessor import FramePreprocessor
        self._preprocessor = FramePreprocessor(normalize=True)
        self._is_loaded = False

    def load(self) -> None:
        """Load model vào memory sử dụng engine tương ứng."""
        try:
            if self.engine_type == "yolo":
                from ultralytics import YOLO
                model_str = str(self.model_path)
                # Cho phép Ultralytics tự động tải file (vd: yolo26s.pt) từ mạng
                if not self.model_path.exists() and "yolo" not in model_str.lower():
                    logger.warning(f"Weights not found or invalid: {self.model_path}. Fallback to yolo26n.pt")
                    model_str = "yolo26n.pt"
                    
                self._model = YOLO(model_str)
                logger.info(f"Loaded YOLO .pt model: {model_str}")
                self._model.to(self.device)
            else:
                # Sử dụng optimized engine (TensorRT/OpenVINO/ONNX)
                from module_edge_firmware.inference.engine import create_engine
                self._engine = create_engine(self.engine_type)
                # Tự động tìm file engine phù hợp
                ext_map = {"tensorrt": ".engine", "openvino": ".xml", "onnx": ".onnx"}
                target_ext = ext_map.get(self.engine_type, ".onnx")
                optimized_path = self.model_path.with_suffix(target_ext)

                if not optimized_path.exists() and self.engine_type == "tensorrt":
                    # Tự động build engine từ ONNX nếu chưa có
                    onnx_path = self.model_path.with_suffix(".onnx")
                    if onnx_path.exists():
                        logger.info(f"Building TensorRT engine from ONNX...")
                        self._engine.load(onnx_path)
                    else:
                        raise FileNotFoundError(f"Cần file .onnx để build TensorRT engine: {onnx_path}")
                else:
                    self._engine.load(optimized_path)

                # Warmup
                self._engine.warmup()

            self._is_loaded = True
            logger.info(f"ObjectDetector ready | engine={self.engine_type} | device={self.device}")

        except Exception as e:
            logger.error(f"Failed to load ObjectDetector: {e}")
            raise

    def predict(self, frame: np.ndarray, verbose: bool = False) -> DetectionResult:
        """
        Phát hiện vật thể trong một frame.

        Args:
            frame: np.ndarray (H, W, 3) BGR image.
            verbose: In chi tiết inference.
        """
        if not self._is_loaded:
            self.load()

        start_time = time.perf_counter()

        if self.engine_type == "yolo":
            results = self._model.predict(
                source=frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=verbose,
                device=self.device,
            )
            inference_time_ms = (time.perf_counter() - start_time) * 1000.0

            result = results[0]
            boxes = result.boxes
            if len(boxes) == 0:
                raw_result = self._empty_result(inference_time_ms)
            else:
                raw_result = DetectionResult(
                    boxes=boxes.xyxy.cpu().numpy(),
                    scores=boxes.conf.cpu().numpy(),
                    class_ids=boxes.cls.cpu().numpy().astype(int),
                    class_names=[self._model.names.get(int(c), f"class_{int(c)}") for c in boxes.cls.cpu().numpy()],
                    inference_time_ms=inference_time_ms,
                )
        else:
            # Optimized engine inference
            input_tensor = self._preprocessor.to_tensor(frame)
            outputs = self._engine.predict(input_tensor)
            inference_time_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Sử dụng bộ giải mã NumPy tối ưu để xử lý output từ engine
            raw_result = self._parse_engine_output(outputs, frame.shape, inference_time_ms)

        return self._filter_and_map_labels(raw_result)

    def _filter_and_map_labels(self, result: DetectionResult) -> DetectionResult:
        """Lọc bỏ 'adult' và map các class sang chuẩn labels.json"""
        label_map = {
            1: "child",
            2: "knife",
            3: "socket",  # Map outlet -> socket
            4: "scissors"
        }
        
        valid_indices = []
        mapped_names = []
        
        for i, class_id in enumerate(result.class_ids):
            if class_id in label_map:
                valid_indices.append(i)
                mapped_names.append(label_map[class_id])
                
        if len(valid_indices) == 0:
            return self._empty_result(result.inference_time_ms)
            
        mask = np.array(valid_indices)
        return DetectionResult(
            boxes=result.boxes[mask],
            scores=result.scores[mask],
            class_ids=result.class_ids[mask],
            class_names=mapped_names,
            inference_time_ms=result.inference_time_ms,
        )

    def _empty_result(self, inference_time_ms: float = 0.0) -> DetectionResult:
        return DetectionResult(
            boxes=np.zeros((0, 4)),
            scores=np.zeros(0),
            class_ids=np.zeros(0, dtype=int),
            class_names=[],
            inference_time_ms=inference_time_ms,
        )

    def _parse_engine_output(self, outputs: list[np.ndarray], orig_shape: tuple, inference_time_ms: float) -> DetectionResult:
        """
        Decode output từ YOLOv8/v11 (TensorRT/OpenVINO/ONNX).
        Hỗ trợ cả format cũ (1, 84, 8400) và YOLOv10/NMS format (1, 300, 6).
        """
        output = outputs[0]
        if output.ndim == 3:
            output = output[0]  # (84, 8400) hoặc (300, 6)

        h_orig, w_orig = orig_shape[:2]
        scale_info = self._preprocessor.get_scale_info(orig_shape, 640)
        scale = scale_info["scale"]
        pad_x = scale_info["pad_x"]
        pad_y = scale_info["pad_y"]

        # Kéo dài cấu trúc YOLOv10 / End-to-End ONNX format [num_boxes, 6] -> [x1, y1, x2, y2, score, class_id]
        if output.shape[1] == 6:
            boxes_xyxy = output[:, :4]
            scores = output[:, 4]
            class_ids = output[:, 5].astype(int)
            
            mask = scores > self.conf_threshold
            boxes_xyxy = boxes_xyxy[mask]
            scores = scores[mask]
            class_ids = class_ids[mask]
            
            if len(boxes_xyxy) == 0:
                return self._empty_result(inference_time_ms)
                
            boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - pad_x) / scale
            boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - pad_y) / scale
            
            # Khử nhiễu các hộp chồng lấn nhau (NMS)
            indices = cv2.dnn.NMSBoxes(
                bboxes=boxes_xyxy.tolist(),
                scores=scores.tolist(),
                score_threshold=self.conf_threshold,
                nms_threshold=self.iou_threshold
            )
            
            if len(indices) == 0:
                return self._empty_result(inference_time_ms)
                
            if isinstance(indices, np.ndarray):
                indices = indices.flatten()
            else:
                indices = [i[0] if isinstance(i, (list, np.ndarray)) else i for i in indices]
            
        else:
            # Format cũ của YOLOv8: (84, 8400)
            if output.shape[0] < output.shape[1]:
                output = output.T

            # 1. Lọc theo confidence score
            scores = np.max(output[:, 4:], axis=1)
            mask = scores > self.conf_threshold
            output = output[mask]
            scores = scores[mask]
            
            if len(output) == 0:
                return self._empty_result(inference_time_ms)

            # 2. Extract boxes and classes
            boxes = output[:, :4]  # [cx, cy, w, h]
            class_ids = np.argmax(output[:, 4:], axis=1)

            # 3. Convert [cx, cy, w, h] -> [x1, y1, x2, y2]
            x1 = boxes[:, 0] - boxes[:, 2] / 2
            y1 = boxes[:, 1] - boxes[:, 3] / 2
            x2 = boxes[:, 0] + boxes[:, 2] / 2
            y2 = boxes[:, 1] + boxes[:, 3] / 2
            
            boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

            boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - pad_x) / scale
            boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - pad_y) / scale

            # 5. Non-Maximum Suppression (NMS)
            indices = cv2.dnn.NMSBoxes(
                bboxes=boxes_xyxy.tolist(),
                scores=scores.tolist(),
                score_threshold=self.conf_threshold,
                nms_threshold=self.iou_threshold
            )

            if len(indices) == 0:
                return self._empty_result(inference_time_ms)
            
            if isinstance(indices, np.ndarray):
                indices = indices.flatten()
            else:
                indices = [i[0] if isinstance(i, (list, np.ndarray)) else i for i in indices]

        return DetectionResult(
            boxes=boxes_xyxy[indices],
            scores=scores[indices],
            class_ids=class_ids[indices],
            class_names=[self.classes[i] if i < len(self.classes) else f"class_{i}" for i in class_ids[indices]],
            inference_time_ms=inference_time_ms,
        )

    def train(
        self,
        data_yaml: str | Path,
        epochs: int = 100,
        batch_size: int = 16,
        img_size: int = 640,
        name: str = "childsun_yolo26",
        output_dir: str | Path | None = None,
        workers: int = 8,
        cache: bool | str = False,
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
            output_dir: Thư mục lưu kết quả training.
            workers: Số CPU threads để load dữ liệu song song.
            cache: Cache ảnh vào RAM ('ram') hoặc disk ('disk') để tăng tốc.

        Returns:
            Dict chứa training metrics.
        """
        if not self._is_loaded:
            self.load()

        logger.info(
            f"Starting training | epochs={epochs} | batch={batch_size} | "
            f"img_size={img_size} | workers={workers} | cache={cache}"
        )

        train_args = dict(
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
            workers=workers,
            cache=cache,
            **kwargs,
        )
        if output_dir:
            train_args["project"] = str(output_dir)

        results = self._model.train(**train_args)

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
