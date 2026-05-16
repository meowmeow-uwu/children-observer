"""
RTSP Stream Capture.

Thu nhận luồng video RTSP từ camera IP với:
- Thread-safe frame access
- Auto-reconnect khi mất kết nối
- Configurable FPS và resolution
"""

from __future__ import annotations

import threading
import time
from typing import Callable

import cv2
import numpy as np
from loguru import logger

from configs.settings import get_settings


class RTSPCapture:
    """
    Thread-safe RTSP stream capture.

    Chạy capture trên background thread, cung cấp frame mới nhất.
    Tự động reconnect khi mất kết nối camera.
    """

    def __init__(
        self,
        rtsp_url: str | None = None,
        target_fps: int | None = None,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
    ):
        settings = get_settings()
        self.rtsp_url = rtsp_url or settings.rtsp_url
        self.target_fps = target_fps or settings.rtsp_fps
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        self._cap: cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._frame_count = 0
        self._on_frame_callbacks: list[Callable] = []
        self._actual_fps = 0.0
        self._last_fps_time = time.monotonic()
        self._fps_frames = 0

    def start(self) -> None:
        """Bắt đầu capture stream trên background thread."""
        if self._running:
            logger.warning("RTSPCapture is already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(f"RTSP capture started: {self.rtsp_url}")

    def stop(self) -> None:
        """Dừng capture stream."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("RTSP capture stopped")

    def get_frame(self) -> np.ndarray | None:
        """Lấy frame mới nhất (thread-safe)."""
        with self._frame_lock:
            return self._frame.copy() if self._frame is not None else None

    def on_frame(self, callback: Callable[[np.ndarray, int], None]) -> None:
        """Đăng ký callback được gọi mỗi khi có frame mới."""
        self._on_frame_callbacks.append(callback)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def actual_fps(self) -> float:
        """Trả về FPS thực tế đo được từ stream."""
        return self._actual_fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def _capture_loop(self) -> None:
        """Main capture loop chạy trên background thread."""
        reconnect_count = 0
        frame_interval = 1.0 / self.target_fps

        while self._running:
            if not self._connect():
                reconnect_count += 1
                if reconnect_count >= self.max_reconnect_attempts:
                    logger.error("Max reconnect attempts reached. Stopping.")
                    self._running = False
                    break
                logger.warning(
                    f"Reconnecting in {self.reconnect_delay}s "
                    f"({reconnect_count}/{self.max_reconnect_attempts})"
                )
                time.sleep(self.reconnect_delay)
                continue

            reconnect_count = 0
            logger.info("RTSP stream connected successfully")

            while self._running:
                start_time = time.monotonic()

                ret, frame = self._cap.read()
                if not ret:
                    logger.warning("Failed to read frame. Reconnecting...")
                    break

                with self._frame_lock:
                    self._frame = frame

                self._frame_count += 1

                # Fire callbacks
                for cb in self._on_frame_callbacks:
                    try:
                        cb(frame, self._frame_count)
                    except Exception as e:
                        logger.error(f"Frame callback error: {e}")

                # Actual FPS measurement
                self._fps_frames += 1
                now = time.monotonic()
                if now - self._last_fps_time >= 2.0: # Update mỗi 2s
                    self._actual_fps = self._fps_frames / (now - self._last_fps_time)
                    self._fps_frames = 0
                    self._last_fps_time = now

                # FPS control
                elapsed = time.monotonic() - start_time
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            if self._cap:
                self._cap.release()
                self._cap = None

    def _connect(self) -> bool:
        """Kết nối tới RTSP stream."""
        try:
            self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self._cap.isOpened():
                logger.error(f"Cannot open RTSP stream: {self.rtsp_url}")
                return False

            return True
        except Exception as e:
            logger.error(f"RTSP connection error: {e}")
            return False
