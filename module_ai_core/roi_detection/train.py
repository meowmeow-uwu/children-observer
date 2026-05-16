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
    parser.add_argument("--workers", type=int, default=8, help="Số CPU threads load dữ liệu")
    parser.add_argument("--cache", type=str, default="", help="Cache ảnh: 'ram' hoặc 'disk'")
    args = parser.parse_args()

    settings = get_settings()
    output_dir = Path("weights/roi_detection")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 50)
    logger.info("Task AI #1: ROI Object Detection Training")
    logger.info(f"Device: {settings.inference_device}")
    logger.info(f"Epochs: {args.epochs} | Batch: {args.batch}")
    logger.info(f"Workers: {args.workers} | Cache: {args.cache or 'off'}")
    logger.info("=" * 50)

    # Train
    detector = ObjectDetector(device=settings.inference_device)
    results = detector.train(
        data_yaml=args.data_yaml,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.img_size,
        output_dir=str(output_dir),
        workers=args.workers,
        cache=args.cache if args.cache else False,
    )

    # Cập nhật Model Registry & So sánh model
    registry_path = Path("weights/registry.json")
    registry = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text())
        except json.JSONDecodeError:
            pass

    # Lấy điểm mAP50 cũ (mặc định 0.0 nếu chưa có)
    old_metrics = registry.get("roi_detection", {}).get("metrics", {})
    old_map50 = old_metrics.get("mAP50", 0.0)

    # Lấy điểm mAP50 mới từ Ultralytics results
    new_map50 = results.box.map50 if results and hasattr(results, "box") else 0.0

    logger.info("=" * 50)
    logger.info(f"📊 Kết quả Training: mAP50 Mới = {new_map50:.4f} | mAP50 Cũ = {old_map50:.4f}")

    if new_map50 > old_map50:
        logger.info("🎉 Đã tìm thấy model tốt hơn! Tiến hành lưu và cập nhật registry...")
        
        # YOLO lưu model ở thư mục riêng (e.g., runs/detect/train3/weights/best.pt)
        # Ta cần copy nó ra thư mục weights/roi_detection chuẩn của dự án
        import shutil
        try:
            # Truy cập thuộc tính save_dir của Ultralytics trainer
            save_dir = getattr(detector._model.trainer, "save_dir", None)
            if save_dir:
                new_best_pt = Path(save_dir) / "weights" / "best.pt"
                target_pt = output_dir / "best.pt"
                
                if new_best_pt.exists():
                    shutil.copy2(new_best_pt, target_pt)
                    logger.info(f"Đã copy model từ {new_best_pt} -> {target_pt}")

                    # Tự động export sang ONNX
                    try:
                        logger.info("Đang tiến hành export sang định dạng ONNX...")
                        from ultralytics import YOLO
                        export_model = YOLO(target_pt)
                        export_model.export(format="onnx")
                        logger.info(f"✅ Tự động Export ONNX thành công: {target_pt.with_suffix('.onnx')}")
                    except Exception as export_e:
                        logger.error(f"❌ Lỗi trong quá trình export ONNX: {export_e}")

                else:
                    logger.warning(f"Không tìm thấy file {new_best_pt} để copy!")
        except Exception as e:
            logger.warning(f"Không thể copy file model tự động: {e}")

        # Cập nhật registry
        registry["roi_detection"] = {
            "status": "ready",
            "path": str(output_dir / "best.pt").replace("\\", "/"),
            "format": "pytorch",
            "metrics": {
                "mAP50": new_map50,
            },
        }

        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
        logger.info(f"✅ Đã cập nhật Model Registry tại {registry_path}")
    else:
        logger.info(f"⚠️ Model mới ({new_map50:.4f}) KHÔNG tốt hơn model cũ ({old_map50:.4f}).")
        logger.info("Giữ nguyên model cũ. Bỏ qua cập nhật Registry!")

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
