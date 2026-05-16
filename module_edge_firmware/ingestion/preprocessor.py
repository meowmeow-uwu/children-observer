"""
Frame Preprocessor.

Tiền xử lý khung hình trước khi đưa vào AI inference:
- Resize về kích thước mô hình
- Normalize pixel values
- Color space conversion
"""

from __future__ import annotations

import cv2
import numpy as np
from loguru import logger


class FramePreprocessor:
    """Tiền xử lý frame cho AI inference."""

    def __init__(self, target_size: int = 640, normalize: bool = True):
        self.target_size = target_size
        self.normalize = normalize

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Tiền xử lý frame: resize + normalize.

        Args:
            frame: BGR image (H, W, 3)

        Returns:
            Processed frame (target_size, target_size, 3) dtype=float32 nếu normalize,
            hoặc uint8 nếu không normalize.
        """
        if frame is None:
            raise ValueError("Frame is None")

        # Letterbox resize (giữ tỷ lệ, padding xám)
        processed = self.letterbox(frame, self.target_size)

        # Normalize pixel values về [0.0, 1.0]
        if self.normalize:
            processed = processed.astype(np.float32) / 255.0

        return processed

    def to_tensor(self, frame: np.ndarray) -> np.ndarray:
        """
        Chuyển frame về NCHW tensor format cực nhanh bằng cv2.dnn.blobFromImage.

        Hàm này thực hiện đồng thời:
        - Resize về target_size
        - Normalize pixel (1/255.0)
        - Swap Channels (BGR -> RGB nếu cần)
        - HWC -> NCHW conversion

        Returns:
            np.ndarray shape (1, 3, target_size, target_size) dtype=float32
        """
        if frame is None:
            raise ValueError("Frame is None")

        # Sử dụng OpenCV DNN blob function (tối ưu C++ SIMD)
        # scalefactor = 1/255, size = (target_size, target_size), mean = (0,0,0), swapRB = True
        blob = cv2.dnn.blobFromImage(
            frame, 
            scalefactor=1.0/255.0 if self.normalize else 1.0,
            size=(self.target_size, self.target_size),
            mean=(0, 0, 0),
            swapRB=True, # YOLO thường yêu cầu RGB
            crop=False
        )
        return blob

    def batch_process(self, frames: list[np.ndarray]) -> np.ndarray:
        """
        Xử lý batch nhiều frame cùng lúc.

        Args:
            frames: List of BGR images.

        Returns:
            np.ndarray shape (N, 3, target_size, target_size) dtype=float32
        """
        tensors = [self.to_tensor(f) for f in frames]
        return np.concatenate(tensors, axis=0)

    def letterbox(
        self,
        frame: np.ndarray,
        target_size: int,
        color: tuple = (114, 114, 114),
    ) -> np.ndarray:
        """Resize ảnh giữ tỷ lệ, padding phần thừa."""
        h, w = frame.shape[:2]
        scale = min(target_size / h, target_size / w)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Padding
        canvas = np.full((target_size, target_size, 3), color, dtype=np.uint8)
        dx = (target_size - new_w) // 2
        dy = (target_size - new_h) // 2
        canvas[dy:dy + new_h, dx:dx + new_w] = resized

        return canvas

    def get_scale_info(self, original_shape: tuple, target_size: int) -> dict:
        """Tính thông tin scale để map tọa độ ngược lại ảnh gốc."""
        h, w = original_shape[:2]
        scale = min(target_size / h, target_size / w)
        new_w, new_h = int(w * scale), int(h * scale)
        dx = (target_size - new_w) // 2
        dy = (target_size - new_h) // 2

        return {
            "scale": scale,
            "pad_x": dx,
            "pad_y": dy,
            "original_shape": (h, w),
        }
