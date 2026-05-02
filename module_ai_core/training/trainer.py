"""
Training Pipeline Orchestrator.

Quản lý toàn bộ quá trình huấn luyện cho các mô hình AI:
- YOLO26 Object Detection trên ChildSUn
- YOLO26-Pose
- ST-GCN Behavior Classification
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from loguru import logger

from configs.settings import get_settings
from module_ai_core.models.object_detector import ObjectDetector
from module_ai_core.models.behavior_classifier import BehaviorClassifier, STGCN

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


class Trainer:
    """
    Unified training orchestrator cho tất cả mô hình.

    Hỗ trợ:
    - Train YOLO26 object detection
    - Train ST-GCN behavior classification
    - Resume training, early stopping, checkpoint management
    """

    def __init__(self, output_dir: str | Path | None = None):
        settings = get_settings()
        self.output_dir = Path(output_dir) if output_dir else Path("./runs/train")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = settings.inference_device

    def train_object_detector(
        self,
        data_yaml: str | Path,
        epochs: int = 100,
        batch_size: int = 16,
        img_size: int = 640,
        model_variant: str = "yolo26n.pt",
        resume: bool = False,
        **kwargs: Any,
    ) -> dict:
        """Huấn luyện YOLO26 trên dataset ChildSUn."""
        logger.info(f"=== Training Object Detector ===")
        logger.info(f"Data: {data_yaml} | Epochs: {epochs} | Batch: {batch_size}")

        detector = ObjectDetector(model_path=Path(model_variant))
        detector.load()

        results = detector.train(
            data_yaml=data_yaml,
            epochs=epochs,
            batch_size=batch_size,
            img_size=img_size,
            name="childsun_detector",
            resume=resume,
            **kwargs,
        )

        logger.info("Object detector training completed!")
        return results

    def train_behavior_classifier(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader | None = None,
        epochs: int = 50,
        lr: float = 0.001,
        patience: int = 10,
    ) -> dict:
        """Huấn luyện ST-GCN behavior classifier."""
        logger.info(f"=== Training Behavior Classifier ===")
        logger.info(f"Epochs: {epochs} | LR: {lr} | Patience: {patience}")

        model = STGCN(num_classes=9)
        model.to(self.device)

        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )
        criterion = nn.CrossEntropyLoss()

        best_val_loss = float("inf")
        patience_counter = 0
        history = {"train_loss": [], "val_loss": [], "val_acc": []}

        for epoch in range(epochs):
            # Training
            model.train()
            train_loss = 0.0
            for batch in train_loader:
                x = batch["skeleton"].float().permute(0, 3, 1, 2).to(self.device)
                y = batch["label"].long().to(self.device)

                optimizer.zero_grad()
                logits = model(x)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            avg_train_loss = train_loss / max(len(train_loader), 1)
            history["train_loss"].append(avg_train_loss)

            # Validation
            if val_loader:
                val_loss, val_acc = self._validate_behavior(model, val_loader, criterion)
                history["val_loss"].append(val_loss)
                history["val_acc"].append(val_acc)
                scheduler.step(val_loss)

                logger.info(
                    f"Epoch {epoch+1}/{epochs} | "
                    f"Train Loss: {avg_train_loss:.4f} | "
                    f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2%}"
                )

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    save_path = self.output_dir / "best_behavior.pt"
                    torch.save(model.state_dict(), save_path)
                    logger.info(f"Best model saved: {save_path}")
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info(f"Early stopping at epoch {epoch+1}")
                        break

        return history

    def _validate_behavior(self, model, val_loader, criterion):
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch in val_loader:
                x = batch["skeleton"].float().permute(0, 3, 1, 2).to(self.device)
                y = batch["label"].long().to(self.device)
                logits = model(x)
                val_loss += criterion(logits, y).item()
                preds = logits.argmax(dim=-1)
                correct += (preds == y).sum().item()
                total += y.size(0)

        return val_loss / max(len(val_loader), 1), correct / max(total, 1)
