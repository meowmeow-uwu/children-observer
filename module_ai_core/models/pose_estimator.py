"""
YOLO11-Pose Estimator.

Wrapper cho YOLO11-Pose để trích xuất skeleton keypoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from configs.settings import get_settings


class Keypoint:
    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16
    HANDS = [LEFT_WRIST, RIGHT_WRIST]
    MOUTH_REGION = [NOSE]


class PoseResult:
    """Kết quả pose estimation cho một frame."""

    def __init__(self, keypoints: np.ndarray, scores: np.ndarray, boxes: np.ndarray):
        self.keypoints = keypoints  # (N, 17, 3)
        self.scores = scores       # (N,)
        self.boxes = boxes         # (N, 4)

    def __len__(self) -> int:
        return len(self.keypoints)

    def get_person_keypoints(self, idx: int = 0) -> np.ndarray:
        if idx >= len(self):
            return np.zeros((17, 3), dtype=np.float32)
        return self.keypoints[idx]

    def get_hand_positions(self, idx: int = 0) -> tuple[np.ndarray, np.ndarray]:
        kps = self.get_person_keypoints(idx)
        return kps[Keypoint.LEFT_WRIST][:2], kps[Keypoint.RIGHT_WRIST][:2]

    def get_mouth_position(self, idx: int = 0) -> np.ndarray:
        kps = self.get_person_keypoints(idx)
        nose = kps[Keypoint.NOSE][:2]
        l_sh = kps[Keypoint.LEFT_SHOULDER][:2]
        r_sh = kps[Keypoint.RIGHT_SHOULDER][:2]
        shoulder_center = (l_sh + r_sh) / 2
        return nose + (shoulder_center - nose) * 0.2

    def get_body_center(self, idx: int = 0) -> np.ndarray:
        kps = self.get_person_keypoints(idx)
        valid = kps[kps[:, 2] > 0.3]
        if len(valid) == 0:
            return np.zeros(2, dtype=np.float32)
        return valid[:, :2].mean(axis=0)

    def to_skeleton_sequence_frame(self) -> np.ndarray:
        if len(self) == 0:
            return np.zeros((1, 17, 3), dtype=np.float32)
        return self.keypoints.copy()


class PoseEstimator:
    """YOLO11-Pose wrapper cho pose estimation."""

    def __init__(self, model_path=None, device=None, conf_threshold=None):
        settings = get_settings()
        self.model_path = Path(model_path) if model_path else settings.pose_model_path
        self.device = device or settings.inference_device
        self.conf_threshold = conf_threshold or settings.inference_conf_threshold
        self._model = None
        self._is_loaded = False

    def load(self) -> None:
        from ultralytics import YOLO
        if self.model_path and self.model_path.exists():
            self._model = YOLO(str(self.model_path))
        else:
            logger.warning(f"Pose weights not found: {self.model_path}. Using pretrained.")
            self._model = YOLO("yolo11n-pose.pt")
        self._model.to(self.device)
        self._is_loaded = True
        logger.info(f"PoseEstimator ready | device={self.device}")

    def predict(self, frame: np.ndarray, verbose: bool = False) -> PoseResult:
        if not self._is_loaded:
            self.load()
        results = self._model.predict(
            source=frame, conf=self.conf_threshold, verbose=verbose, device=self.device
        )
        result = results[0]
        if result.keypoints is None or len(result.boxes) == 0:
            return PoseResult(np.zeros((0, 17, 3)), np.zeros(0), np.zeros((0, 4)))
        return PoseResult(
            keypoints=result.keypoints.data.cpu().numpy(),
            scores=result.boxes.conf.cpu().numpy(),
            boxes=result.boxes.xyxy.cpu().numpy(),
        )

    def export(self, format: str = "onnx", **kwargs: Any) -> Path:
        if not self._is_loaded:
            self.load()
        path = self._model.export(format=format, **kwargs)
        logger.info(f"Pose model exported to: {path}")
        return Path(path)

    def train(
        self,
        data_yaml: str,
        epochs: int = 30,
        batch_size: int = 8,
        output_dir: str = "weights/fall_detection",
        device: str | int | None = None,
        workers: int = 2,
        **kwargs: Any,
    ) -> None:
        """Huấn luyện (Fine-tuning) mô hình dựa trên nền tảng kiến trúc YOLO11n-pose."""
        from ultralytics import YOLO

        target_device = device if device is not None else self.device
        logger.info(f"Khởi tạo mô hình nền gốc yolo11n-pose.pt để chuẩn bị Fine-tuning trên device={target_device}...")
        # Ép buộc nạp cấu trúc và trọng số khởi tạo của mô hình YOLO11n-pose
        self._model = YOLO("yolo11n-pose.pt")

        logger.info(f"Bắt đầu quá trình huấn luyện: data={data_yaml}, epochs={epochs}, batch={batch_size}, device={target_device}, workers={workers}")
        # Kích hoạt hàm train của Ultralytics với các tham số truyền từ script chính
        results = self._model.train(
            data=data_yaml,
            epochs=epochs,
            batch=batch_size,
            project=output_dir,
            name="train_results",
            device=target_device,
            workers=workers,  # Giới hạn số luồng nạp dữ liệu CPU để hạ nhiệt độ máy
            exist_ok=True,  # Ghi đè vào cùng thư mục để dễ quản lý file kết quả đầu ra
            **kwargs,
        )

        # Sau khi huấn luyện xong, tự động cập nhật lại trạng thái nạp mô hình bằng file best.pt vừa học được
        best_model_path = Path(output_dir) / "train_results" / "weights" / "best.pt"
        if best_model_path.exists():
            self._model = YOLO(str(best_model_path))
            self.model_path = best_model_path
            self._is_loaded = True
            logger.info(f"Huấn luyện thành công! Mô hình tốt nhất lưu tại: {best_model_path}")
        else:
            logger.error("Không tìm thấy file trọng số sau khi kết thúc huấn luyện.")

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded