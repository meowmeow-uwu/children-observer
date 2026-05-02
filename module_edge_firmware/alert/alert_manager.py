"""
Alert Manager.

Quản lý và gửi cảnh báo kèm snapshot + video clip.
Có debounce để tránh spam cảnh báo liên tục.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
from loguru import logger

from configs.settings import get_settings
from module_edge_firmware.alert.snapshot import SnapshotGenerator
from module_edge_firmware.buffer.circular_buffer import CircularBuffer
from module_edge_firmware.analysis.risk_assessor import RiskAssessment


@dataclass
class Alert:
    """Một cảnh báo hoàn chỉnh."""
    alert_id: str
    timestamp: float
    risk_level: str
    reasons: list[str]
    snapshot_full: Path | None = None
    snapshot_crop: Path | None = None
    video_clip: Path | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "snapshot_full": str(self.snapshot_full) if self.snapshot_full else None,
            "snapshot_crop": str(self.snapshot_crop) if self.snapshot_crop else None,
            "video_clip": str(self.video_clip) if self.video_clip else None,
            "metadata": self.metadata,
        }


class AlertManager:
    """
    Quản lý cảnh báo với debounce.

    Khi phát hiện rủi ro:
    1. Chụp snapshot (toàn cảnh + crop)
    2. Trích xuất video clip từ buffer
    3. Mã hóa E2EE (delegate to module_security)
    4. Gửi tới Mobile App
    """

    def __init__(
        self,
        buffer: CircularBuffer | None = None,
        cooldown_seconds: int | None = None,
    ):
        settings = get_settings()
        self.buffer = buffer or CircularBuffer()
        self.cooldown = cooldown_seconds or settings.alert_cooldown_seconds
        self.snapshot_gen = SnapshotGenerator()

        self._last_alert_time: float = 0
        self._alert_count: int = 0
        self._alert_history: list[Alert] = []
        self._callbacks: list = []

    def on_alert(self, callback) -> None:
        """Đăng ký callback khi có alert mới."""
        self._callbacks.append(callback)

    def process_risk(
        self,
        assessment: RiskAssessment,
        frame: np.ndarray,
        event_box: np.ndarray | None = None,
    ) -> Alert | None:
        """
        Xử lý risk assessment và tạo alert nếu cần.

        Args:
            assessment: Kết quả đánh giá rủi ro.
            frame: Frame hiện tại (BGR).
            event_box: Bounding box của sự kiện.

        Returns:
            Alert nếu gửi cảnh báo, None nếu bị debounce.
        """
        if not assessment.should_alert:
            return None

        # Debounce check
        current_time = time.time()
        if current_time - self._last_alert_time < self.cooldown:
            logger.debug(
                f"Alert debounced. Next alert in "
                f"{self.cooldown - (current_time - self._last_alert_time):.1f}s"
            )
            return None

        self._last_alert_time = current_time
        self._alert_count += 1

        # 1. Chụp snapshot
        snapshots = self.snapshot_gen.capture(frame, event_box)

        # 2. Trích xuất video clip
        clip_path = self.buffer.extract_clip()

        # 3. Tạo alert object
        alert = Alert(
            alert_id=f"alert_{self._alert_count:06d}",
            timestamp=current_time,
            risk_level=assessment.level.value,
            reasons=assessment.reasons,
            snapshot_full=snapshots.get("full"),
            snapshot_crop=snapshots.get("crop"),
            video_clip=clip_path,
            metadata=assessment.to_dict(),
        )

        self._alert_history.append(alert)

        # 4. Fire callbacks (sẽ gửi qua E2EE tới mobile)
        for cb in self._callbacks:
            try:
                cb(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(
            f"🚨 ALERT #{self._alert_count} | {assessment.level.value} | "
            f"{'; '.join(assessment.reasons)}"
        )

        return alert

    @property
    def alert_count(self) -> int:
        return self._alert_count

    def get_history(self, limit: int = 50) -> list[dict]:
        """Lấy lịch sử cảnh báo."""
        return [a.to_dict() for a in self._alert_history[-limit:]]
