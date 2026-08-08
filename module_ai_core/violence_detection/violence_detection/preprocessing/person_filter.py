"""
Person Filter module to detect human presence before running violence classification.
"""

from __future__ import annotations

import cv2
import numpy as np
from loguru import logger


class PersonFilter:
    """
    Filter layer that detects human presence in video frames.

    Supported backends:
    - 'yolo': Uses Ultralytics YOLO (yolov8n.pt) if installed.
    - 'hog': Uses OpenCV built-in HOG People Detector (No extra dependencies).
    - 'auto': Attempts YOLO first, falls back to OpenCV HOG.
    """

    def __init__(
        self,
        min_persons: int = 2,
        conf_threshold: float = 0.35,
        backend: str = "auto",
        yolo_model_name: str = "yolov8n.pt",
    ):
        self.min_persons = min_persons
        self.conf_threshold = conf_threshold
        self.backend_name = backend.lower()

        self._yolo_model = None
        self._hog_detector = None

        self._init_backend(yolo_model_name)

    def _init_backend(self, yolo_model_name: str):
        if self.backend_name in ("auto", "yolo"):
            try:
                from ultralytics import YOLO
                logger.info(f"PersonFilter: Loading YOLO model '{yolo_model_name}'...")
                self._yolo_model = YOLO(yolo_model_name)
                self.active_backend = "yolo"
                logger.info("PersonFilter: Successfully initialized YOLO backend.")
                return
            except Exception as err:
                if self.backend_name == "yolo":
                    logger.error(f"Failed to load YOLO model: {err}")
                    raise RuntimeError(f"YOLO backend requested but failed to load: {err}") from err
                logger.info("PersonFilter: Ultralytics YOLO not available. Falling back to OpenCV HOG People Detector.")

        # OpenCV HOG Fallback
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self._hog_detector = hog
        self.active_backend = "hog"
        logger.info("PersonFilter: Initialized OpenCV HOG People Detector backend.")

    def count_persons_in_frame(self, frame: np.ndarray) -> int:
        """
        Count number of persons detected in a single BGR frame.

        Args:
            frame: OpenCV BGR image numpy array.

        Returns:
            Number of detected human persons.
        """
        if frame is None or frame.size == 0:
            return 0

        if self.active_backend == "yolo" and self._yolo_model is not None:
            results = self._yolo_model(frame, verbose=False, conf=self.conf_threshold)
            count = 0
            if len(results) > 0 and results[0].boxes is not None:
                classes = results[0].boxes.cls.cpu().numpy()
                # COCO class 0 is 'person'
                count = int(np.sum(classes == 0))
            return count

        elif self.active_backend == "hog" and self._hog_detector is not None:
            # Resize image for faster HOG detection
            h, w = frame.shape[:2]
            scale = 400.0 / max(h, w)
            if scale < 1.0:
                resized = cv2.resize(frame, (int(w * scale), int(h * scale)))
            else:
                resized = frame

            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            boxes, _ = self._hog_detector.detectMultiScale(
                gray, winStride=(8, 8), padding=(4, 4), scale=1.05
            )
            return len(boxes)

        return 0

    def has_required_persons(self, frames: list[np.ndarray]) -> tuple[bool, int]:
        """
        Check if clip frames contain at least min_persons.
        Inspects representative frames (middle, start, end) from the clip.

        Args:
            frames: Sequence of OpenCV BGR frames.

        Returns:
            Tuple of (has_sufficient_persons: bool, max_persons_found: int).
        """
        if not frames:
            return False, 0

        # Sample 3 representative frames across the clip (start, middle, end)
        sample_indices = [0, len(frames) // 2, len(frames) - 1]
        max_persons = 0

        for idx in sample_indices:
            count = self.count_persons_in_frame(frames[idx])
            max_persons = max(max_persons, count)
            if max_persons >= self.min_persons:
                return True, max_persons

        return max_persons >= self.min_persons, max_persons
