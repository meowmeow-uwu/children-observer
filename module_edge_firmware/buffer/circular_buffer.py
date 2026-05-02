"""
Circular Buffer - Bộ đệm vòng cho video.

Lưu trữ 10-15 giây video gần nhất, trích xuất clip 5-10 giây khi có sự cố.
"""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import NamedTuple

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

        max_frames = self.buffer_seconds * self.fps
        self._buffer: deque[TimedFrame] = deque(maxlen=max_frames)
        self._frame_counter = 0

    def add_frame(self, frame: np.ndarray) -> None:
        """Thêm frame vào buffer."""
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
        """
        Trích xuất video clip từ buffer.

        Args:
            duration: Thời lượng clip (seconds). Default từ settings.
            before_event: Lấy frames trước thời điểm hiện tại.

        Returns:
            Path tới file video clip (.mp4), None nếu buffer trống.
        """
        settings = get_settings()
        duration = duration or settings.alert_clip_duration

        if len(self._buffer) == 0:
            logger.warning("Buffer is empty, cannot extract clip")
            return None

        # Lấy N frames cuối cùng
        num_frames = min(duration * self.fps, len(self._buffer))
        frames = list(self._buffer)[-num_frames:]

        if not frames:
            return None

        # Generate filename
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        clip_path = self.output_dir / f"alert_clip_{timestamp_str}.mp4"

        # Write video
        h, w = frames[0].frame.shape[:2]
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(clip_path), fourcc, self.fps, (w, h))

        for timed_frame in frames:
            writer.write(timed_frame.frame)

        writer.release()
        logger.info(f"Extracted clip: {clip_path} ({len(frames)} frames, {duration}s)")

        return clip_path

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
