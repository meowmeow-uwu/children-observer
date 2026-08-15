"""
ByteTrack adapter — bọc ultralytics BYTETracker cho detections ONNX thuần.

- Chỉ đưa class child vào tracker (use case ROI).
- Output chuẩn hóa về Python primitives, box normalized 0-1, kèm class_id/class_name.
- `confirmed`: track đã được quan sát đủ số detection frame (hoặc score cao) —
  ROI alert chỉ dùng track confirmed; frontend có thể hiển thị provisional khác style.
- reset() khi video loop để track ID không bị tái sử dụng sai.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from loguru import logger
from ultralytics.trackers import BYTETracker

# Số detection frame liên tiếp cần để track được coi là confirmed
CONFIRM_FRAMES = 3
# Score cao → confirmed ngay lập tức
CONFIRM_SCORE = 0.5
# Hold/predict box khi track tạm mất dấu (dev.md §4: tối đa 350ms) —
# dùng Kalman state của BYTETracker, không phải box giả
HOLD_LOST_SECONDS = 0.35


class DetectionContainer:
    """Đối tượng detections tối thiểu đáp ứng hợp đồng BYTETracker.update().

    Cần: .xywh, .conf, .cls + __getitem__ theo boolean mask + __len__.
    """

    def __init__(self, xywh: np.ndarray, conf: np.ndarray, cls: np.ndarray):
        self.xywh = xywh
        self.conf = conf
        self.cls = cls

    @classmethod
    def from_xyxy(cls, xyxy: np.ndarray, conf: np.ndarray, cls_ids: np.ndarray) -> "DetectionContainer":
        if len(xyxy) == 0:
            return cls(np.empty((0, 4)), np.empty((0,)), np.empty((0,)))
        w = xyxy[:, 2] - xyxy[:, 0]
        h = xyxy[:, 3] - xyxy[:, 1]
        cx = xyxy[:, 0] + w / 2
        cy = xyxy[:, 1] + h / 2
        return cls(np.stack([cx, cy, w, h], axis=1), conf, cls_ids)

    def __getitem__(self, mask):
        return DetectionContainer(self.xywh[mask], self.conf[mask], self.cls[mask])

    def __len__(self) -> int:
        return len(self.conf)


class ByteTrackAdapter:
    """Wrapper ByteTrack: detections JSON-safe → tracks JSON-safe (child-only)."""

    def __init__(
        self,
        track_thresh: float = 0.35,
        track_buffer: int = 120,
        match_thresh: float = 0.8,
        frame_rate: int = 30,
        classes_to_track: tuple[str, ...] = ("child",),
        high_thresh: float | None = None,
        low_thresh: float | None = None,
        new_thresh: float | None = None,
        confirm_frames: int = CONFIRM_FRAMES,
        confirm_score: float = CONFIRM_SCORE,
    ):
        """Hiệu chỉnh theo test_video.mp4: child detection thưa và confidence thấp.
        `frame_rate` phải bằng detection FPS thật của pipeline (ByteTrack buffer
        quy đổi theo frame, không theo giây)."""
        self._frame_rate = max(1, int(frame_rate))
        self._classes_to_track = set(classes_to_track)
        self._confirm_frames = max(1, int(confirm_frames))
        self._confirm_score = confirm_score
        args = SimpleNamespace(
            track_thresh=track_thresh,
            track_high_thresh=high_thresh if high_thresh is not None else 0.15,
            track_low_thresh=low_thresh if low_thresh is not None else 0.05,
            new_track_thresh=new_thresh if new_thresh is not None else 0.1,
            track_buffer=track_buffer,
            match_thresh=match_thresh,
            min_box_area=10,
            fuse_score=True,
        )
        self._tracker = BYTETracker(args=args, frame_rate=self._frame_rate)
        # (track_id → số frame liên tiếp được tracker giữ)
        self._confirm_count: dict[int, int] = {}
        logger.info(
            f"ByteTrack initialized: thresh={track_thresh} buffer={track_buffer} "
            f"match={match_thresh} classes={classes_to_track} frame_rate={self._frame_rate}"
        )

    def update(self, detections: list[dict]) -> list[dict]:
        """detections: [{box: [x1,y1,x2,y2] 0-1, class_id, class, score}] → tracks JSON-safe."""
        # Lọc class cần track
        scale = 1920.0  # scale nhất quán để tracker làm việc ở pixel space
        rows = [
            d
            for d in detections
            if d.get("class") in self._classes_to_track and d.get("score", 0) >= 0.05
        ]
        if not rows:
            container = DetectionContainer(np.empty((0, 4)), np.empty((0,)), np.empty((0,)))
        else:
            xyxy = np.array(
                [
                    [
                        d["box"][0] * scale,
                        d["box"][1] * scale,
                        d["box"][2] * scale,
                        d["box"][3] * scale,
                    ]
                    for d in rows
                ],
                dtype=np.float32,
            )
            conf = np.array([d["score"] for d in rows], dtype=np.float32)
            cls = np.array([d.get("class_id", 1) for d in rows], dtype=np.float32)
            container = DetectionContainer.from_xyxy(xyxy, conf, cls)

        try:
            out = self._tracker.update(container, None)
        except Exception as exc:
            logger.warning(f"ByteTrack update error: {exc}")
            return []

        tracks: list[dict] = []
        seen_ids: set[int] = set()
        if isinstance(out, np.ndarray) and out.ndim == 2 and len(out):
            for row in out:
                # row: [x1, y1, x2, y2, track_id, score, cls, _]
                tid = int(row[4])
                seen_ids.add(tid)
                self._confirm_count[tid] = self._confirm_count.get(tid, 0) + 1
                score = float(row[5])
                confirmed = self._confirm_count[tid] >= self._confirm_frames or score >= self._confirm_score
                tracks.append(
                    {
                        "track_id": tid,
                        "class_id": 1,
                        "class_name": "child",
                        "confidence": round(score, 3),
                        "box": [
                            round(float(row[0]) / scale, 4),
                            round(float(row[1]) / scale, 4),
                            round(float(row[2]) / scale, 4),
                            round(float(row[3]) / scale, 4),
                        ],
                        "confirmed": confirmed,
                        "predicted": False,
                    }
                )

        # ---- Hold/predict: track vừa mất dấu (<= HOLD_LOST_SECONDS) tiếp tục
        # phát box theo Kalman state — che khoảng inference ngắn (dev.md: max
        # 350ms), không giữ ghost box lâu. Chỉ phát track đã được quan sát ≥1 lần;
        # `confirmed` chỉ True nếu track từng đạt ngưỡng confirm (alert vẫn strict).
        hold_frames = max(1, int(HOLD_LOST_SECONDS * self._frame_rate))
        current_frame = self._tracker.frame_id
        for st in self._tracker.lost_stracks:
            tid = int(st.track_id)
            if tid in seen_ids:
                continue
            if current_frame - st.end_frame > hold_frames:
                continue
            seen_count = self._confirm_count.get(tid, 0)
            if seen_count < 1:
                continue
            try:
                x1, y1, x2, y2 = st.xyxy
            except Exception:
                continue
            tracks.append(
                {
                    "track_id": tid,
                    "class_id": 1,
                    "class_name": "child",
                    "confidence": round(float(getattr(st, "score", 0.0)) if getattr(st, "score", 0.0) else 0.0, 3),
                    "box": [
                        round(float(x1) / scale, 4),
                        round(float(y1) / scale, 4),
                        round(float(x2) / scale, 4),
                        round(float(y2) / scale, 4),
                    ],
                    "confirmed": seen_count >= self._confirm_frames or bool(getattr(st, "score", 0.0)) >= self._confirm_score,
                    "predicted": True,
                }
            )

        # Dọn counter của track đã biến mất
        stale = [tid for tid in self._confirm_count if tid not in seen_ids and tid not in {int(s.track_id) for s in self._tracker.lost_stracks}]
        for tid in stale:
            del self._confirm_count[tid]

        return tracks

    def reset(self) -> None:
        """Reset tracker khi video loop sang vòng mới."""
        try:
            self._tracker.reset()
        except Exception as exc:
            logger.warning(f"ByteTrack reset error: {exc}")
        self._confirm_count.clear()
