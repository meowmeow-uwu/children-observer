"""
Training script cho Task AI #3: Fall Detection (Pose Estimation).

Phụ trách: P5
Model: YOLO26-Pose (Ultralytics)

Usage:
    python module_ai_core/fall_detection/train.py
    python module_ai_core/fall_detection/train.py --pretrained
    python module_ai_core/fall_detection/train.py --epochs 50 --data ./data/pose/data.yaml
"""

import argparse
import json
from pathlib import Path

from loguru import logger

from configs.settings import get_settings
from module_ai_core.models.pose_estimator import PoseEstimator


def main():
    parser = argparse.ArgumentParser(description="Train/Prepare Fall Detection (Pose)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--data", type=str, default="./data/pose/data.yaml")
    parser.add_argument(
        "--pretrained", action="store_true",
        help="Sử dụng pretrained model từ Ultralytics (không cần train)",
    )
    args = parser.parse_args()

    settings = get_settings()
    output_dir = Path("weights/fall_detection")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 50)
    logger.info("Task AI #3: Fall Detection (Pose Estimation)")
    logger.info(f"Device: {settings.inference_device}")
    logger.info("=" * 50)

    if args.pretrained:
        # Sử dụng pretrained — download và lưu vào weights/
        logger.info("Sử dụng pretrained YOLO-Pose model...")
        estimator = PoseEstimator(device=settings.inference_device)
        estimator.load()

        model_path = output_dir / "yolo-pose-best.pt"
        # Export pretrained weights
        if hasattr(estimator._model, "save"):
            estimator._model.save(str(model_path))
        logger.info(f"Pretrained model saved: {model_path}")
    else:
        # Fine-tune trên dữ liệu custom
        logger.info(f"Fine-tuning Pose model | Epochs: {args.epochs}")
        estimator = PoseEstimator(device=settings.inference_device)
        estimator.train(
            data_yaml=args.data,
            epochs=args.epochs,
            batch_size=args.batch,
            output_dir=str(output_dir),
        )
        model_path = output_dir / "yolo-pose-best.pt"

    # Cập nhật Model Registry
    registry_path = Path("weights/registry.json")
    registry = {}
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())

    registry["fall_detection"] = {
        "status": "ready",
        "path": str(model_path),
        "format": "pytorch",
        "note": "pretrained" if args.pretrained else "fine-tuned",
    }

    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    logger.info(f"✅ Registry updated: {registry_path}")


if __name__ == "__main__":
    main()
