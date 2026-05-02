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
            Processed frame (target_size, target_size, 3)
        """
        if frame is None:
            raise ValueError("Frame is None")

        # Letterbox resize (giữ tỷ lệ)
        processed = self.letterbox(frame, self.target_size)

        return processed

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
