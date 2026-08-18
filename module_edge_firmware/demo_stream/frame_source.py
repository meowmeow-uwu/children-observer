"""
FrameSource cho luồng demo: giải mã video MỘT LẦN, chạy đúng clock video.

- Đọc frame theo FPS thật của file (30 FPS) bằng đồng hồ monotonic duy nhất.
- Mỗi frame được gắn:
    - source_pts_ms: clock video trong vòng loop hiện tại (0 .. duration), reset mỗi loop.
    - source_time_ms: clock monotonic của pipeline (tăng liên tục, không reset).
    - loop_id: vòng lặp video (tăng khi EOF, tín hiệu reset tracker).
- Vòng lặp video mới → loop_id++ (reset tracker/state).
- Không tích backlog: chỉ giữ frame mới nhất (latest-frame).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from module_edge_firmware.rtsp_utils import redact_rtsp_url


@dataclass
class FrameSnapshot:
    frame: np.ndarray
    frame_index: int       # frame index trong vòng loop (0..total-1)
    source_pts_ms: float   # clock video trong loop hiện tại (reset mỗi loop)
    source_time_ms: float  # clock monotonic pipeline (tăng liên tục)
    loop_id: int

    @property
    def is_valid(self) -> bool:
        return self.frame is not None


class FrameStore:
    """Lưu frame mới nhất (maxsize=1 semantics) kèm metadata đồng bộ."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: FrameSnapshot | None = None
        self._loop_id = 0
        self._video_fps = 30.0
        self._video_duration_ms = 0.0
        self._total_frames = 0

    def publish(self, frame: np.ndarray, frame_index: int, source_time_ms: float) -> None:
        with self._lock:
            pts_ms = frame_index / self._video_fps * 1000.0 if self._video_fps > 0 else 0.0
            self._snapshot = FrameSnapshot(
                frame=frame,
                frame_index=frame_index,
                source_pts_ms=pts_ms,
                source_time_ms=source_time_ms,
                loop_id=self._loop_id,
            )

    def next_loop(self) -> None:
        with self._lock:
            self._loop_id += 1
            self._snapshot = None

    def clear(self) -> None:
        """Bỏ frame cũ khi không còn viewer; viewer mới không nhận ảnh stale."""
        with self._lock:
            self._snapshot = None

    def snapshot(self) -> FrameSnapshot | None:
        with self._lock:
            return self._snapshot

    def set_meta(self, fps: float, duration_ms: float, total_frames: int) -> None:
        with self._lock:
            self._video_fps = fps
            self._video_duration_ms = duration_ms
            self._total_frames = total_frames

    @property
    def video_fps(self) -> float:
        with self._lock:
            return self._video_fps

    @property
    def video_duration_ms(self) -> float:
        with self._lock:
            return self._video_duration_ms

    @property
    def total_frames(self) -> int:
        with self._lock:
            return self._total_frames

    @property
    def loop_id(self) -> int:
        with self._lock:
            return self._loop_id


class DemoVideoSource:
    """Đọc video (file hoặc RTSP) theo đúng clock video trên thread riêng.

    Hỗ trợ đoạn demo: nếu start_seconds/end_seconds được cấu hình, loop chỉ
    chạy trong đoạn [start, end] của chính MP4 (không tạo bản sao video).
    """

    def __init__(
        self,
        video_path: str | Path,
        frame_store: FrameStore | None = None,
        start_time: float | None = None,
        start_seconds: float | None = None,
        end_seconds: float | None = None,
        initial_active: bool = True,
    ):
        self.video_path = Path(video_path)
        self._store = frame_store or FrameStore()
        # Đồng hồ wall-clock (monotonic) dùng chung với AIVideoTrack.
        self._start_time = start_time if start_time is not None else time.monotonic()
        self._start_seconds = start_seconds
        self._end_seconds = end_seconds

        self._running = False
        self._thread: threading.Thread | None = None
        self._restart_requested = False
        self._restart_lock = threading.Lock()
        self._active = threading.Event()
        if initial_active:
            self._active.set()

    @property
    def store(self) -> FrameStore:
        return self._store

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, name="demo-video-source", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def restart(self) -> None:
        """Tua video về ĐẦU đoạn demo (loop mới + reset tracker).

        Gọi khi có viewer WebRTC mới kết nối để video chạy lại từ đầu
        mỗi lần người dùng vào xem — không chiếu tiếp ở đoạn giữa chừng.
        An toàn thread: read loop xử lý cờ ở vòng lặp kế tiếp (<= 1 frame).
        """
        with self._restart_lock:
            self._restart_requested = True
        # Không cho WebRTC track mới lấy frame còn sót của vòng trước trong
        # khoảng ngắn trước khi thread VideoCapture xử lý lệnh seek.
        self._store.clear()

    def restart_and_wait(self, timeout: float = 2.0) -> bool:
        """Tua và chờ frame đầu vòng mới trước khi WebRTC tạo video track.

        Điều kiện ``loop_id`` tăng loại bỏ race trong đó read thread kịp
        publish thêm một frame của vòng cũ sau lệnh ``clear()``.
        """
        previous_loop = self._store.loop_id
        self.set_active(False)
        self.restart()
        self.set_active(True)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snap = self._store.snapshot()
            if (
                self._store.loop_id > previous_loop
                and snap is not None
                and snap.is_valid
                and snap.frame_index <= 2
            ):
                return True
            time.sleep(0.005)
        logger.error("Timed out waiting for demo video session restart")
        return False

    def set_active(self, active: bool) -> None:
        """Bật/tắt decode theo viewer của phiên demo."""
        if active:
            self._active.set()
        else:
            self._active.clear()
            self._store.clear()

    def _consume_restart(self) -> bool:
        with self._restart_lock:
            requested = self._restart_requested
            self._restart_requested = False
        return requested

    def _read_loop(self) -> None:
        if not self.video_path.exists():
            logger.error(f"Demo video not found: {self.video_path}")
            return

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open demo video: {self.video_path}")
            return

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_ms = total_frames / video_fps * 1000.0
        self._store.set_meta(video_fps, duration_ms, total_frames)

        # Đoạn demo: [start, end] theo giây trên chính file video
        start_frame = int((self._start_seconds or 0.0) * video_fps)
        end_frame = int((self._end_seconds or (total_frames / video_fps)) * video_fps)
        end_frame = min(end_frame, total_frames)
        segment_frames = max(1, end_frame - start_frame)
        if self._start_seconds is not None or self._end_seconds is not None:
            segment_start_s = start_frame / video_fps
            segment_end_s = end_frame / video_fps
            logger.info(
                f"Demo segment: frames [{start_frame}, {end_frame}) "
                f"({segment_start_s:.1f}s → {segment_end_s:.1f}s)"
            )

        frame_interval = 1.0 / video_fps
        frame_index = 0

        # Bảo đảm cả chế độ không viewer-gated cũng bắt đầu đúng đầu đoạn,
        # không đọc frame 0 của file trước lần loop/restart đầu tiên.
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        while self._running:
            if not self._active.wait(timeout=0.1):
                continue
            loop_start = time.monotonic()

            # Viewer mới kết nối → tua video về đầu đoạn demo
            if self._consume_restart():
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                frame_index = 0
                self._store.next_loop()
                logger.info(f"Video restarted to segment start (loop #{self._store.loop_id})")
                continue

            # Nhảy tới vị trí đoạn demo mỗi loop
            if frame_index >= segment_frames or frame_index < 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                frame_index = 0
                self._store.next_loop()
                logger.info(f"Demo loop restart (loop #{self._store.loop_id}, tracker reset)")
                continue

            ret, frame = cap.read()
            if not ret:
                # EOF (hoặc file hỏng) — loop an toàn, không decode vô hạn
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                frame_index = 0
                self._store.next_loop()
                continue

            source_time_ms = (time.monotonic() - self._start_time) * 1000.0
            self._store.publish(frame, frame_index, source_time_ms)
            frame_index += 1

            # Chạy đúng clock video
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.0, frame_interval - elapsed)
            time.sleep(sleep_time)

        cap.release()
        logger.info("Demo video source stopped")


class RtspVideoSource:
    """Latest-frame RTSP source for hardware deployments.

    Unlike the demo file source this never loops or seeks.  On a read failure
    it releases the decoder and reconnects with bounded backoff, keeping the
    last valid ROI/model state in the pipeline.
    """

    def __init__(
        self,
        rtsp_url: str,
        frame_store: FrameStore | None = None,
        start_time: float | None = None,
        reconnect_delay: float = 3.0,
        initial_active: bool = True,
    ) -> None:
        self.rtsp_url = rtsp_url
        self._store = frame_store or FrameStore()
        self._start_time = start_time if start_time is not None else time.monotonic()
        self._reconnect_delay = reconnect_delay
        self._running = False
        self._thread: threading.Thread | None = None
        self._active = threading.Event()
        if initial_active:
            self._active.set()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, name="rtsp-video-source", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._active.set()  # unblock wait before joining
        if self._thread:
            self._thread.join(timeout=5)

    def set_active(self, active: bool) -> None:
        if active:
            self._active.set()
        else:
            self._active.clear()
            self._store.clear()

    def restart(self) -> None:
        # A live camera cannot seek; a new viewer simply starts from the next
        # available frame and receives a new stream identity.
        self._store.next_loop()

    def restart_and_wait(self, timeout: float = 2.0) -> bool:
        previous_loop = self._store.loop_id
        self.set_active(True)
        self.restart()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snap = self._store.snapshot()
            if self._store.loop_id > previous_loop and snap is not None and snap.is_valid:
                return True
            time.sleep(0.01)
        logger.error("Timed out waiting for first RTSP frame")
        return False

    def _read_loop(self) -> None:
        frame_index = 0
        while self._running:
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                logger.warning("Cannot open RTSP stream; retrying in {}s", self._reconnect_delay)
                cap.release()
                time.sleep(self._reconnect_delay)
                continue

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            self._store.set_meta(fps, 0.0, 0)
            logger.info("RTSP stream connected: {}", redact_rtsp_url(self.rtsp_url))
            while self._running:
                if not self._active.wait(timeout=0.2):
                    continue
                ok, frame = cap.read()
                if not ok:
                    logger.warning("RTSP frame read failed; reconnecting")
                    break
                source_time_ms = (time.monotonic() - self._start_time) * 1000.0
                self._store.publish(frame, frame_index, source_time_ms)
                frame_index += 1
            cap.release()
            if self._running:
                time.sleep(self._reconnect_delay)
