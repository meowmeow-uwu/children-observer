"""
Active Learning Service.

Thu thập phản hồi "Báo động sai" từ phụ huynh để cải thiện mô hình.
Luồng: Parent feedback → Label correction → Retrain trigger
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class FeedbackEntry:
    """Một feedback từ phụ huynh."""
    alert_id: str
    timestamp: float
    is_false_alarm: bool
    correct_label: str | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "is_false_alarm": self.is_false_alarm,
            "correct_label": self.correct_label,
            "notes": self.notes,
        }


class ActiveLearningService:
    """
    Thu thập và quản lý feedback cho active learning.

    Khi tích lũy đủ feedback mới, trigger retrain pipeline.
    """

    def __init__(
        self,
        feedback_dir: str | Path = "./data/feedback",
        retrain_threshold: int = 50,
    ):
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.retrain_threshold = retrain_threshold

        self._pending_feedback: list[FeedbackEntry] = []
        self._total_feedback = 0
        self._false_alarm_count = 0

    def submit_feedback(self, alert_id: str, is_false_alarm: bool,
                        correct_label: str | None = None, notes: str = "") -> None:
        """Nhận feedback từ phụ huynh (HITL)."""
        entry = FeedbackEntry(
            alert_id=alert_id,
            timestamp=time.time(),
            is_false_alarm=is_false_alarm,
            correct_label=correct_label,
            notes=notes,
        )

        self._pending_feedback.append(entry)
        self._total_feedback += 1

        if is_false_alarm:
            self._false_alarm_count += 1

        logger.info(
            f"Feedback received: alert={alert_id} | "
            f"false_alarm={is_false_alarm} | "
            f"pending={len(self._pending_feedback)}/{self.retrain_threshold}"
        )

        # Persist feedback
        self._save_feedback(entry)

        # Check retrain trigger
        if len(self._pending_feedback) >= self.retrain_threshold:
            self._trigger_retrain()

    def _save_feedback(self, entry: FeedbackEntry) -> None:
        """Lưu feedback vào file."""
        date_str = time.strftime("%Y%m%d")
        feedback_file = self.feedback_dir / f"feedback_{date_str}.jsonl"

        with open(feedback_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def _trigger_retrain(self) -> None:
        """Trigger retrain pipeline khi đủ feedback."""
        logger.info(
            f"🔄 Retrain triggered! {len(self._pending_feedback)} new feedback entries. "
            f"False alarm rate: {self._false_alarm_count}/{self._total_feedback}"
        )
        # TODO: Integrate with Trainer.train_object_detector()
        self._pending_feedback.clear()

    def get_stats(self) -> dict:
        return {
            "total_feedback": self._total_feedback,
            "false_alarms": self._false_alarm_count,
            "false_alarm_rate": self._false_alarm_count / max(self._total_feedback, 1),
            "pending_retrain": len(self._pending_feedback),
        }
