"""
Model Evaluator.

Đánh giá hiệu suất mô hình với các metrics: mAP, Precision, Recall, F1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger


class Evaluator:
    """Đánh giá mô hình trên tập validation/test."""

    def __init__(self, output_dir: str | Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path("./runs/eval")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_detector(self, detector, data_yaml: str | Path) -> dict:
        """Đánh giá YOLO detector - trả về mAP, precision, recall."""
        logger.info(f"Evaluating detector on: {data_yaml}")
        results = detector.validate(data_yaml=data_yaml)
        logger.info(f"Evaluation completed")
        return results

    def evaluate_behavior(self, predictions: list[int], ground_truths: list[int],
                          class_names: list[str]) -> dict:
        """Tính metrics cho behavior classifier."""
        preds = np.array(predictions)
        gts = np.array(ground_truths)

        accuracy = (preds == gts).mean()

        # Per-class metrics
        per_class = {}
        for i, name in enumerate(class_names):
            tp = ((preds == i) & (gts == i)).sum()
            fp = ((preds == i) & (gts != i)).sum()
            fn = ((preds != i) & (gts == i)).sum()
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-6)
            per_class[name] = {
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
            }

        metrics = {"accuracy": float(accuracy), "per_class": per_class}
        logger.info(f"Behavior evaluation: accuracy={accuracy:.2%}")
        return metrics
