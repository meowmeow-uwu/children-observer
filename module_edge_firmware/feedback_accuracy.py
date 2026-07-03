"""
Feedback accuracy tracking for real-world edge alerts.

Mobile sends parent feedback after an alert. The edge device stores the
prediction snapshot locally and forwards false-alarm signals to the existing
active-learning service without owning that team's retraining flow.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from loguru import logger

from configs.settings import get_settings


@dataclass
class FeedbackRecord:
    alert_id: str
    timestamp: float
    is_correct: bool
    correct_label: str | None = None
    notes: str = ""
    prediction: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "is_correct": self.is_correct,
            "correct_label": self.correct_label,
            "notes": self.notes,
            "prediction": self.prediction,
        }


class AccuracyFeedbackTracker:
    """Store alert feedback and expose simple accuracy metrics for MVP validation."""

    def __init__(self, output_dir: str | Path | None = None):
        settings = get_settings()
        self.output_dir = Path(output_dir) if output_dir else settings.feedback_log_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._predictions: dict[str, dict[str, Any]] = {}
        self._total_feedback = 0
        self._correct_feedback = 0
        self._lock = Lock()

    def register_alert(self, alert) -> None:
        """Remember prediction metadata so later mobile feedback has context."""
        payload = alert.to_dict() if hasattr(alert, "to_dict") else dict(alert)
        alert_id = payload.get("alert_id")
        if not alert_id:
            logger.warning("Cannot register alert without alert_id")
            return

        with self._lock:
            self._predictions[alert_id] = payload
        logger.debug(f"Registered alert prediction for feedback: {alert_id}")

    def submit_feedback(
        self,
        alert_id: str,
        is_correct: bool,
        correct_label: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Persist feedback from mobile and update in-memory accuracy metrics."""
        with self._lock:
            prediction = self._predictions.get(alert_id, {})
            record = FeedbackRecord(
                alert_id=alert_id,
                timestamp=time.time(),
                is_correct=is_correct,
                correct_label=correct_label,
                notes=notes,
                prediction=prediction,
            )

            self._append_record(record)
            self._total_feedback += 1
            if is_correct:
                self._correct_feedback += 1

            summary = self.summary()

        self._send_to_active_learning(record)
        logger.info(
            f"Feedback recorded: alert={alert_id} | correct={is_correct} | "
            f"accuracy={summary['accuracy']:.2%}"
        )
        return summary

    def summary(self) -> dict[str, Any]:
        accuracy = self._correct_feedback / max(self._total_feedback, 1)
        return {
            "total_feedback": self._total_feedback,
            "correct_feedback": self._correct_feedback,
            "incorrect_feedback": self._total_feedback - self._correct_feedback,
            "accuracy": accuracy,
        }

    def _append_record(self, record: FeedbackRecord) -> None:
        date_str = time.strftime("%Y%m%d")
        path = self.output_dir / f"edge_feedback_{date_str}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def _send_to_active_learning(self, record: FeedbackRecord) -> None:
        """Bridge feedback to backend active learning when available."""
        try:
            from module_backend_infra.active_learning import ActiveLearningService

            service = ActiveLearningService(feedback_dir=self.output_dir)
            service.submit_feedback(
                alert_id=record.alert_id,
                is_false_alarm=not record.is_correct,
                correct_label=record.correct_label,
                notes=record.notes,
            )
        except Exception as exc:
            logger.debug(f"Active learning feedback bridge skipped: {exc}")
