"""
VideoStream abstraction for reading frames from Webcam, Video file, or RTSP stream.
"""

from __future__ import annotations

import re
import time
from typing import Generator, Iterator, Tuple
import cv2
import numpy as np
from loguru import logger


def redact_rtsp_url(url: str) -> str:
    """
    Redact password and username credentials from RTSP URLs for secure logging.

    Example:
        rtsp://user:secret123@192.168.1.100:554/stream -> rtsp://***:***@192.168.1.100:554/stream
    """
    if isinstance(url, str) and url.lower().startswith("rtsp://"):
        return re.sub(r"rtsp://([^:]+):([^@]+)@", "rtsp://***:***@", url, flags=re.IGNORECASE)
    return str(url)


class VideoStream:
    """
    OpenCV VideoCapture wrapper supporting iterator and context manager protocol.
    Works with webcam index, video file path, or RTSP stream URL.
    """

    def __init__(self, source: str | int | None = 0):
        """
        Args:
            source: 0 (or integer) for webcam, path string for file, or rtsp:// URL.
        """
        self.source = source if source is not None else 0
        self.cap: cv2.VideoCapture | None = None
        self.fps: float = 30.0
        self._start_time: float = 0.0

    def open(self) -> cv2.VideoCapture:
        """Open video stream source."""
        if self.cap is not None and self.cap.isOpened():
            return self.cap

        safe_source_name = redact_rtsp_url(str(self.source))
        logger.info(f"Opening video stream source: {safe_source_name}")

        # If string contains only digits, convert to integer webcam index
        source_arg = self.source
        if isinstance(source_arg, str) and source_arg.isdigit():
            source_arg = int(source_arg)

        self.cap = cv2.VideoCapture(source_arg)

        if not self.cap.isOpened():
            logger.error(f"Failed to open video source: {safe_source_name}")
            raise RuntimeError(f"Cannot open video source: {safe_source_name}")

        fps_val = self.cap.get(cv2.CAP_PROP_FPS)
        if fps_val and fps_val > 0:
            self.fps = fps_val

        self._start_time = time.time()
        logger.info(f"Video stream opened successfully. FPS: {self.fps:.2f}")
        return self.cap

    def __enter__(self) -> VideoStream:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def release(self) -> None:
        """Release underlying OpenCV VideoCapture resource safely."""
        if self.cap is not None:
            safe_source_name = redact_rtsp_url(str(self.source))
            logger.info(f"Releasing video stream: {safe_source_name}")
            self.cap.release()
            self.cap = None

    def __iter__(self) -> Iterator[Tuple[np.ndarray, float]]:
        """
        Yield frames and relative timestamps (in seconds).
        Yields:
            Tuple of (frame_np, timestamp_sec)
        """
        if self.cap is None or not self.cap.isOpened():
            self.open()

        frame_index = 0
        while self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.info("Video stream ended or frame read failed.")
                break

            timestamp_sec = frame_index / self.fps
            frame_index += 1
            yield frame, timestamp_sec
