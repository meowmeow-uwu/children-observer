"""
Training script cho Task AI #2: Violence Detection.

Phụ trách: P4
Model: ST-GCN (Behavior Classifier)
Dataset: Violence skeleton sequences

Usage:
    python module_ai_core/violence_detection/train.py
    python module_ai_core/violence_detection/train.py --epochs 200 --lr 0.001
"""

import argparse
import json
from pathlib import Path

import torch
from loguru import logger

from configs.settings import get_settings
from module_ai_core.models.behavior_classifier import BehaviorClassifier


def main():
    parser = argparse.ArgumentParser(description="Train Violence Detection (ST-GCN)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--data-dir", type=str, default="./data/violence")
    args = parser.parse_args()

    settings = get_settings()
    output_dir = Path("weights/violence_detection")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 50)
    logger.info("Task AI #2: Violence Detection Training (ST-GCN)")
    logger.info(f"Device: {settings.inference_device}")
    logger.info(f"Epochs: {args.epochs} | LR: {args.lr}")
    logger.info("=" * 50)

    # Load dataset
    from module_ai_core.datasets.violence_loader import ViolenceDataset

    train_ds = ViolenceDataset(root_dir=args.data_dir, split="train")
    val_ds = ViolenceDataset(root_dir=args.data_dir, split="val")

    if len(train_ds) == 0:
        logger.error("Không tìm thấy dữ liệu! Hãy chuẩn bị dataset trước.")
        logger.info(f"Đặt dữ liệu vào: {args.data_dir}/train/skeletons/")
        return

    logger.info(f"Train: {len(train_ds)} samples | Val: {len(val_ds)} samples")

    # Build model
    classifier = BehaviorClassifier(device=settings.inference_device)

    # TODO: Implement training loop
    # Pseudocode:
    #   train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    #   optimizer = torch.optim.SGD(classifier.model.parameters(), lr=args.lr)
    #   for epoch in range(args.epochs):
    #       for batch in train_loader:
    #           ...
    #       evaluate(val_ds)
    #       save best model

    logger.warning("⚠️ Training loop chưa triển khai. Hãy implement trong file này!")

    # Save placeholder & update registry
    model_path = output_dir / "stgcn_best.pt"
    # torch.save(classifier.model.state_dict(), model_path)

    registry_path = Path("weights/registry.json")
    registry = {}
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())

    registry["violence_detection"] = {
        "status": "training",  # Đổi thành "ready" khi train xong
        "path": str(model_path),
        "format": "pytorch",
        "metrics": {"accuracy": 0.0},
    }

    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    logger.info(f"Registry updated: {registry_path}")


if __name__ == "__main__":
    main()
