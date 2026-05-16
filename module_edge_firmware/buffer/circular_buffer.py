"""
Circular Buffer - Bộ đệm vòng cho video.

Lưu trữ 10-15 giây video gần nhất, trích xuất clip 5-10 giây khi có sự cố.
"""

from __future__ import annotations

import time
import threading
from collections import deque
from pathlib import Path
from typing import NamedTuple
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from loguru import logger

from configs.settings import get_settings


class TimedFrame(NamedTuple):
    frame: np.ndarray
    timestamp: float
    frame_id: int


class CircularBuffer:
    """
    Ring buffer lưu trữ frames gần nhất.

    Khi có sự cố, trích xuất video clip từ buffer.
    """

    MAX_PENDING_CLIPS = 5  # Giới hạn số clip đang ghi đồng thời

    def __init__(
        self,
        buffer_seconds: int | None = None,
        fps: int | None = None,
        output_dir: str | Path = "./clips",
    ):
        settings = get_settings()
        self.buffer_seconds = buffer_seconds or settings.alert_buffer_seconds
        self.fps = fps or settings.rtsp_fps
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.max_frames = self.buffer_seconds * self.fps
        self._buffer: deque[TimedFrame] = deque(maxlen=self.max_frames)
        self._frame_counter = 0
        self._lock = threading.Lock()

        # Sử dụng Semaphore để giới hạn số clip extraction đồng thời
        self._clip_semaphore = threading.Semaphore(self.MAX_PENDING_CLIPS)
        self._executor = ThreadPoolExecutor(max_workers=2)

        logger.info(
            f"CircularBuffer initialized: {self.buffer_seconds}s @ {self.fps}fps "
            f"(max {self.max_frames} frames)"
        )

    def add_frame(self, frame: np.ndarray) -> None:
        """Thêm frame vào buffer (Thread-safe)."""
        with self._lock:
            self._frame_counter += 1
            self._buffer.append(TimedFrame(
                frame=frame,
                timestamp=time.time(),
                frame_id=self._frame_counter,
            ))

    def extract_clip(
        self,
        duration: int | None = None,
        before_event: bool = True,
    ) -> Path | None:
        """Trích xuất video clip từ buffer (Async, có giới hạn đồng thời)."""
        settings = get_settings()
        duration = duration or settings.alert_clip_duration

        if len(self._buffer) == 0:
            logger.warning("Buffer is empty, cannot extract clip")
            return None

        # Kiểm tra giới hạn clip đang xử lý
        if not self._clip_semaphore.acquire(blocking=False):
            logger.warning("⚠️ Too many clips being written. Skipping extraction.")
            return None

        # Lấy bản sao của frames (Thread-safe)
        with self._lock:
            num_frames = min(duration * self.fps, len(self._buffer))
            frames_to_write = list(self._buffer)[-num_frames:]

        if not frames_to_write:
            self._clip_semaphore.release()
            return None

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        clip_path = self.output_dir / f"alert_clip_{timestamp_str}.mp4"

        self._executor.submit(self._write_video_worker, frames_to_write, clip_path, self.fps)
        return clip_path

    def _write_video_worker(self, frames: list[TimedFrame], output_path: Path, fps: int):
        """Worker thread để ghi video clip."""
        try:
            if not frames:
                return
            h, w = frames[0].frame.shape[:2]
            fourcc = cv2.VideoWriter.fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

            for timed_frame in frames:
                writer.write(timed_frame.frame)

            writer.release()
            logger.info(f"✅ Video clip saved async: {output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to write video clip: {e}")
        finally:
            self._clip_semaphore.release()

    def get_memory_usage_mb(self) -> float:
        """Tính toán dung lượng RAM đang dùng bởi buffer (xấp xỉ)."""
        if not self._buffer:
            return 0.0
        sample_frame = self._buffer[0].frame
        frame_size = sample_frame.nbytes
        total_bytes = frame_size * len(self._buffer)
        return total_bytes / (1024 * 1024)

    def shutdown(self):
        """Giải phóng tài nguyên executor."""
        self._executor.shutdown(wait=False)

    def __del__(self):
        self.shutdown()

    @property
    def frame_count(self) -> int:
        return len(self._buffer)

    @property
    def duration_seconds(self) -> float:
        if len(self._buffer) < 2:
            return 0.0
        return self._buffer[-1].timestamp - self._buffer[0].timestamp

    def clear(self) -> None:
        self._buffer.clear()
