"""
Privacy Masking - Làm mờ mặt người lạ tại biên.

Tự động phát hiện và blur mặt người không thuộc gia đình
trước khi lưu trữ hoặc truyền video.
"""

from __future__ import annotations

import cv2
import numpy as np
from loguru import logger

from configs.settings import get_settings


class PrivacyMasker:
    """
    Face blurring cho người lạ.

    Sử dụng OpenCV DNN face detector hoặc MediaPipe.
    """

    def __init__(self, blur_strength: int = 51, min_confidence: float | None = None):
        settings = get_settings()
        self.blur_strength = blur_strength
        self.min_confidence = min_confidence or settings.privacy_face_detection_conf
        self._face_detector = None
        self._is_enabled = settings.privacy_blur_strangers

    def load(self) -> None:
        """Load face detector."""
        # Sử dụng OpenCV Haar Cascade (built-in, không cần download)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_detector = cv2.CascadeClassifier(cascade_path)
        logger.info("Privacy masker loaded (Haar Cascade)")

    def apply(self, frame: np.ndarray, known_boxes: list | None = None) -> np.ndarray:
        """
        Blur mặt người lạ trong frame.

        Args:
            frame: BGR image.
            known_boxes: List of [x1,y1,x2,y2] boxes cho người đã biết (không blur).

        Returns:
            Frame đã blur mặt người lạ.
        """
        if not self._is_enabled:
            return frame

        if self._face_detector is None:
            self.load()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        result = frame.copy()

        for (x, y, w, h) in faces:
            face_center = (x + w // 2, y + h // 2)

            # Skip nếu là người đã biết
            if known_boxes and self._is_known_person(face_center, known_boxes):
                continue

            # Blur face
            face_region = result[y:y+h, x:x+w]
            blurred = cv2.GaussianBlur(face_region, (self.blur_strength, self.blur_strength), 0)
            result[y:y+h, x:x+w] = blurred

        return result

    def _is_known_person(self, face_center: tuple, known_boxes: list) -> bool:
        """Kiểm tra mặt có thuộc người đã biết không."""
        cx, cy = face_center
        for box in known_boxes:
            x1, y1, x2, y2 = box[:4]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return True
        return False
