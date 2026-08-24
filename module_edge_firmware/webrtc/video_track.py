import asyncio
import time
import uuid

import numpy as np
from aiortc import VideoStreamTrack
from aiortc.mediastreams import VIDEO_CLOCK_RATE, VIDEO_TIME_BASE
from av import VideoFrame


class SharedFrameSource:
    """
    Nơi lưu trữ khung hình mới nhất dùng chung cho nhiều kết nối WebRTC.
    """

    def __init__(self):
        self.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def update_frame(self, frame: np.ndarray):
        self.current_frame = frame


class AIVideoTrack(VideoStreamTrack):
    """
    WebRTC video track đọc frame mới nhất từ FrameStore (pipeline demo).

    Clock:
    - Toàn bộ pacing dùng time.monotonic() (KHÔNG trộn time.time()).
    - PTS = (monotonic - start_time) * VIDEO_CLOCK_RATE — tăng đơn điệu
      trong một PeerConnection, khớp `source_time_ms` của pipeline.
    - Mỗi track (mỗi PeerConnection) có stream_id riêng; stream_origin_ms =
      source_time_ms của frame đầu tiên track giao — frontend map mediaTime
      về clock Edge bằng origin + mediaTime*1000.
    - recv() pacing tối đa 30 FPS; không tạo busy-loop.
    """

    def __init__(self, frame_source=None, start_time: float | None = None, fps: int = 30):
        super().__init__()
        if frame_source is None:
            frame_source = SharedFrameSource()
        self.frame_source = frame_source
        self._start = start_time if start_time is not None else time.monotonic()
        # PTS starts from zero for every PeerConnection. `_start` remains the
        # shared pipeline clock used by FrameStore/source_time_ms.
        self._media_start = time.monotonic()
        self._fps = max(1, int(fps))
        self._frame_interval = 1.0 / self._fps
        self._next_frame_mono = self._media_start
        self.stream_id = f"stream-{uuid.uuid4().hex[:12]}"
        self._stream_origin_ms: float | None = None

    def origin_ms(self) -> float | None:
        """source_time_ms của frame đầu tiên track đã giao (cho stream_sync)."""
        return self._stream_origin_ms

    async def recv(self) -> VideoFrame:
        """
        aiortc gọi liên tục để lấy frame đẩy lên mạng; pacing theo monotonic
        clock với deadline tuyệt đối (không sleep dồn theo FPS thực tế).
        """
        if self.readyState != "live":
            raise asyncio.CancelledError

        now = time.monotonic()
        if now < self._next_frame_mono:
            await asyncio.sleep(self._next_frame_mono - now)
            now = time.monotonic()

        pts = int((now - self._media_start) * VIDEO_CLOCK_RATE)
        self._next_frame_mono = self._media_start + (pts + VIDEO_CLOCK_RATE // self._fps) / VIDEO_CLOCK_RATE

        # Lấy frame mới nhất từ frame store; nếu đang giữa vòng lặp video
        # (snapshot=None) thì chờ frame thật — KHÔNG gửi placeholder làm frame
        # đầu tiên (sẽ khóa resolution của track sai, ví dụ 640x480).
        frame = None
        frame_source_time = None
        if hasattr(self.frame_source, "snapshot"):
            for _ in range(100):  # tối đa ~3s
                snap = self.frame_source.snapshot()
                if snap is not None and snap.is_valid:
                    frame = snap.frame
                    frame_source_time = snap.source_time_ms
                    break
                await asyncio.sleep(0.03)
        elif hasattr(self.frame_source, "current_frame"):
            frame = self.frame_source.current_frame
        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Origin: source_time_ms tương ứng frame đầu tiên giao
        if self._stream_origin_ms is None:
            self._stream_origin_ms = frame_source_time if frame_source_time is not None else (now - self._start) * 1000.0

        img = frame.copy()
        vf = VideoFrame.from_ndarray(img, format="bgr24")
        vf.pts = pts
        vf.time_base = VIDEO_TIME_BASE
        return vf
