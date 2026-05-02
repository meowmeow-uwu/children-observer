"""
Training script cho Task AI #1: ROI & Object Detection.

Phụ trách: P3
Model: YOLO26 Nano
Dataset: ChildSUn

Usage:
    python module_ai_core/roi_detection/train.py
    python module_ai_core/roi_detection/train.py --epochs 200 --batch 16
"""

import argparse
import json
from pathlib import Path

from loguru import logger

from configs.settings import get_settings
from module_ai_core.models.object_detector import ObjectDetector


def main():
    parser = argparse.ArgumentParser(description="Train ROI Object Detection")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--img-size", type=int, default=640)
    parser.add_argument("--data-yaml", type=str, default="./data/childsun/data.yaml")
    args = parser.parse_args()

    settings = get_settings()
    output_dir = Path("weights/roi_detection")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 50)
    logger.info("Task AI #1: ROI Object Detection Training")
    logger.info(f"Device: {settings.inference_device}")
    logger.info(f"Epochs: {args.epochs} | Batch: {args.batch}")
    logger.info("=" * 50)

    # Train
    detector = ObjectDetector(device=settings.inference_device)
    results = detector.train(
        data_yaml=args.data_yaml,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.img_size,
        output_dir=str(output_dir),
    )

    # Cập nhật Model Registry
    registry_path = Path("weights/registry.json")
    registry = {}
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())

    registry["roi_detection"] = {
        "status": "ready",
        "path": str(output_dir / "best.pt"),
        "format": "pytorch",
        "metrics": {
            "mAP50": getattr(results, "maps", [0])[0] if results else 0,
        },
    }

    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    logger.info(f"✅ Model saved & registry updated: {registry_path}")


if __name__ == "__main__":
    main()
