"""
Detector ONNX — letterbox chuẩn Ultralytics, class names từ metadata model.

Khắc phục lỗi hình học cũ: trước đây blobFromImage resize thẳng 16:9 → 640×640
nhưng map box ngược lại giả định đã letterbox, làm box lệch khỏi vị trí thật.
Hàm letterbox/unletterbox dưới đây khớp 1:1 với Ultralytics.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort
from loguru import logger

MODEL_NAMES_FALLBACK = ["adult", "child", "knife", "outlet", "scissors"]


def letterbox(
    im: np.ndarray,
    new_shape: tuple[int, int] = (640, 640),
    color: tuple[int, int, int] = (114, 114, 114),
    scaleup: bool = True,
) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize + pad giữ nguyên tỷ lệ, giống Ultralytics.

    Returns: (ảnh đã letterbox, ratio scale, (pad_x, pad_y)).
    """
    shape = im.shape[:2]  # (h, w)
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:
        r = min(r, 1.0)

    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))  # (w, h)
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # (w, h) padding
    dw, dh = dw / 2, dh / 2  # chia đều hai bên

    if shape[::-1] != new_unpad:  # resize
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)

    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return im, r, (dw, dh)


def unletterbox_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    ratio: float,
    pad: tuple[float, float],
    orig_w: int,
    orig_h: int,
) -> tuple[float, float, float, float]:
    """Map box từ tọa độ letterbox (pixel 640) về tọa độ chuẩn hóa 0-1 trên frame gốc."""
    dw, dh = pad
    x1_orig = (x1 - dw) / ratio / orig_w
    y1_orig = (y1 - dh) / ratio / orig_h
    x2_orig = (x2 - dw) / ratio / orig_w
    y2_orig = (y2 - dh) / ratio / orig_h
    return (
        float(max(0.0, min(1.0, x1_orig))),
        float(max(0.0, min(1.0, y1_orig))),
        float(max(0.0, min(1.0, x2_orig))),
        float(max(0.0, min(1.0, y2_orig))),
    )


def to_json_safe(value: Any) -> Any:
    """Chuyển numpy scalars/arrays về Python primitives để JSON serialize được.

    Đây là root cause của lỗi cũ:
    TypeError: Object of type float32 is not JSON serializable.
    """
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(v) for v in value]
    return value


def load_class_names(session: ort.InferenceSession) -> list[str]:
    """Đọc class names từ metadata của ONNX model (nguồn chân lý)."""
    names: str | None = None
    try:
        meta = session.get_modelmeta().custom_metadata_map
        names = meta.get("names")
    except Exception:
        meta = None

    if names:
        # Format 1: JSON hợp lệ {"0": "adult", ...}
        try:
            parsed = json.loads(names)
            if isinstance(parsed, dict):
                ordered = [parsed[str(i)] for i in range(len(parsed))]
                if all(isinstance(n, str) for n in ordered):
                    return ordered
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        # Format 2: Python dict literal "{0: 'adult', 1: 'child', ...}"
        try:
            import re

            items = re.findall(r"(\d+)\s*:\s*['\"]([^'\"]+)['\"]", names)
            if items:
                ordered = [name for _, name in sorted(items, key=lambda kv: int(kv[0]))]
                if ordered and all(isinstance(n, str) for n in ordered):
                    return ordered
        except Exception:
            pass

    # Fallback: registry labels.json nếu khớp số class
    labels_path = Path("configs/labels.json")
    try:
        data = json.loads(labels_path.read_text(encoding="utf-8"))
        classes = [c["name"] for c in data["object_detection"]["classes"]]
        if len(classes) == len(MODEL_NAMES_FALLBACK):
            return classes
    except Exception:
        pass

    logger.warning(
        f"Class names không đọc được từ metadata — dùng fallback: {MODEL_NAMES_FALLBACK}"
    )
    return list(MODEL_NAMES_FALLBACK)


class OnnxDetector:
    """YOLO ONNX (end2end [1,300,6] hoặc [84,8400]) với letterbox chuẩn."""

    def __init__(
        self,
        model_path: str | Path,
        conf_threshold: float = 0.1,
        iou_threshold: float = 0.45,
        input_size: int = 640,
    ):
        self.model_path = Path(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self._session: ort.InferenceSession | None = None
        self._input_name = ""
        self.class_names: list[str] = []

    def load(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {self.model_path}")

        providers = ["CPUExecutionProvider"]
        active = [p for p in providers if p in ort.get_available_providers()]
        sess_opts = ort.SessionOptions()
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # ORT mặc định dùng gần như toàn bộ logical CPU, dễ oversubscribe với
        # decode/WebRTC/ByteTrack và làm p95 tăng vọt. 8 thread đã benchmark
        # tốt nhất trên máy demo 16 logical CPU; vẫn cho phép override.
        default_threads = min(8, max(1, (os.cpu_count() or 2) // 2))
        intra_threads = max(
            1, int(os.getenv("EDGE_ONNX_INTRA_THREADS", str(default_threads)))
        )
        sess_opts.intra_op_num_threads = intra_threads
        sess_opts.inter_op_num_threads = 1
        sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self._session = ort.InferenceSession(
            str(self.model_path), sess_options=sess_opts, providers=active
        )
        self._input_name = self._session.get_inputs()[0].name
        self.class_names = load_class_names(self._session)
        logger.info(
            f"ONNX loaded: {self.model_path.name} | input={self._input_name} | "
            f"classes={self.class_names} | conf={self.conf_threshold} | "
            f"provider={self._session.get_providers()[0]} | threads={intra_threads}"
        )

        dummy = np.random.rand(1, 3, self.input_size, self.input_size).astype(np.float32)
        for _ in range(3):
            self._session.run(None, {self._input_name: dummy})
        logger.info("ONNX warmup complete")

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def detect(self, frame: np.ndarray) -> list[dict]:
        """Chạy inference trên 1 frame BGR. Output: list[dict] JSON-safe."""
        if self._session is None:
            return []

        h_orig, w_orig = frame.shape[:2]
        img, ratio, pad = letterbox(frame, (self.input_size, self.input_size))
        blob = img.transpose(2, 0, 1)[None].astype(np.float32) / 255.0

        outputs = self._session.run(None, {self._input_name: blob})
        output = outputs[0]
        if output.ndim == 3:
            output = output[0]

        detections: list[dict] = []

        # YOLO end2end: (N, 6) → [x1, y1, x2, y2, score, class_id]
        if output.ndim == 2 and output.shape[1] == 6:
            for row in output:
                x1, y1, x2, y2, score, cls_id = row
                if float(score) < self.conf_threshold:
                    continue
                cls_id = int(cls_id)
                if cls_id >= len(self.class_names):
                    continue
                b = unletterbox_box(
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2),
                    ratio,
                    pad,
                    w_orig,
                    h_orig,
                )
                detections.append(
                    {
                        "box": b,
                        "class_id": cls_id,
                        "class": self.class_names[cls_id],
                        "score": round(float(score), 3),
                    }
                )
        else:
            # Standard YOLO: (84, 8400)
            if output.shape[0] < output.shape[1]:
                output = output.T
            scores = np.max(output[:, 4:], axis=1)
            mask = scores > self.conf_threshold
            output_filtered = output[mask]
            scores_filtered = scores[mask]
            if len(output_filtered) > 0:
                boxes_xywh = output_filtered[:, :4]
                class_ids = np.argmax(output_filtered[:, 4:], axis=1)
                x1 = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2
                y1 = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2
                x2 = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2
                y2 = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2
                boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)
                indices = cv2.dnn.NMSBoxes(
                    bboxes=boxes_xyxy.tolist(),
                    scores=scores_filtered.tolist(),
                    score_threshold=self.conf_threshold,
                    nms_threshold=self.iou_threshold,
                )
                if isinstance(indices, np.ndarray):
                    indices = indices.flatten()
                for idx in indices:
                    cls_id = int(class_ids[idx])
                    if cls_id >= len(self.class_names):
                        continue
                    b = unletterbox_box(
                        float(boxes_xyxy[idx][0]),
                        float(boxes_xyxy[idx][1]),
                        float(boxes_xyxy[idx][2]),
                        float(boxes_xyxy[idx][3]),
                        ratio,
                        pad,
                        w_orig,
                        h_orig,
                    )
                    detections.append(
                        {
                            "box": b,
                            "class_id": cls_id,
                            "class": self.class_names[cls_id],
                            "score": round(float(scores_filtered[idx]), 3),
                        }
                    )

        return detections
