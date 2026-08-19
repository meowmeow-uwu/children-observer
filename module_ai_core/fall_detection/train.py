"""
High-Performance Fine-Tuning Script cho Module Fall Detection (YOLOv11-Pose).

Tối ưu hóa các chỉ số đánh giá Pose (mục tiêu Pose Recall > 80%, Pose mAP50-95 > 40%):
1. Nạp base model yolo11n-pose.pt và file cấu hình dataset data.yaml.
2. Tiền xử lý và làm sạch dữ liệu Pose (loại bỏ dòng 5 tokens, kiểm tra keypoints).
3. Cấu hình siêu tham số nâng cao:
   - Loss Gains: pose=18.0, kobj=3.0, box=7.5, cls=0.5.
   - Epochs=150, batch=16, imgsz=640, optimizer="AdamW", lr0=0.001, lrf=0.01.
   - Warmup=4.0, weight_decay=0.0005, patience=25, close_mosaic=20.
   - Augmentation: degrees=10.0, fliplr=0.5, flipud=0.0 (tuyệt đối không lật dọc).
4. Đánh giá tự động trên tập test và trích xuất đầy đủ Box & Pose metrics.
5. Sao chép checkpoint đầu ra tới weights/fall_detection/best.pt.
6. Cập nhật Model Registry tại weights/registry.json.

Usage:
    python module_ai_core/fall_detection/train.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

# Tối ưu hóa phân bổ bộ nhớ CUDA phòng tránh CUBLAS_STATUS_ALLOC_FAILED
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import numpy as np
import torch
from loguru import logger
from ultralytics import YOLO

from configs.settings import get_settings
from module_ai_core.datasets.fall_loader import preprocess_fall_dataset, update_data_yaml


def safe_float(val: Any, default: float = 0.0) -> float:
    """Chuyển đổi các kiểu dữ liệu số/numpy/tensor về float an toàn."""
    if val is None:
        return default
    if hasattr(val, "item"):
        return float(val.item())
    if isinstance(val, (list, tuple, np.ndarray)):
        return float(np.mean(val)) if len(val) > 0 else default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="High-Performance YOLOv11m-Pose Fine-Tuning for Fall Detection")
    parser.add_argument("--epochs", type=int, default=150, help="Số lượng epoch (mặc định: 150)")
    parser.add_argument("--batch", type=int, default=4, help="Kích thước batch (mặc định: 4)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào (mặc định: 640)")
    parser.add_argument("--optimizer", type=str, default="AdamW", help="Optimizer (mặc định: AdamW)")
    parser.add_argument("--lr0", type=float, default=0.001, help="Learning rate ban đầu (mặc định: 0.001)")
    parser.add_argument("--lrf", type=float, default=0.01, help="Learning rate tỷ lệ cuối (mặc định: 0.01)")
    parser.add_argument("--weight_decay", type=float, default=0.0005, help="Weight decay (mặc định: 0.0005)")
    parser.add_argument("--warmup_epochs", type=float, default=3.0, help="Số epoch warmup (mặc định: 3.0)")
    parser.add_argument("--patience", type=int, default=20, help="Patience cho Early Stopping (mặc định: 20)")
    parser.add_argument("--close_mosaic", type=int, default=15, help="Tắt mosaic N epoch cuối (mặc định: 15)")
    parser.add_argument("--degrees", type=float, default=10.0, help="Xoay tối đa (mặc định: 10.0)")
    parser.add_argument("--fliplr", type=float, default=0.5, help="Lật ngang (mặc định: 0.5)")
    parser.add_argument("--pose", type=float, default=18.0, help="Loss weight cho Pose keypoints (mặc định: 18.0)")
    parser.add_argument("--kobj", type=float, default=3.0, help="Loss weight cho Keypoint objectness (mặc định: 3.0)")
    parser.add_argument("--box", type=float, default=7.5, help="Loss weight cho Bounding Box (mặc định: 7.5)")
    parser.add_argument("--cls", type=float, default=0.5, help="Loss weight cho Class (mặc định: 0.5)")
    parser.add_argument("--model", type=str, default="yolo11m-pose.pt", help="Base pose model (mặc định: yolo11m-pose.pt)")
    parser.add_argument("--data", type=str, default=None, help="Đường dẫn file data.yaml")
    parser.add_argument("--device", type=str, default=None, help="Thiết bị tính toán ('0', 'cuda', 'cpu')")
    parser.add_argument("--workers", type=int, default=4, help="Số luồng Dataloader (mặc định: 4)")
    parser.add_argument("--skip-preprocess", action="store_true", help="Bỏ qua bước tiền xử lý dữ liệu")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]

    # 1. Định vị và chuẩn hóa đường dẫn file data.yaml
    if args.data:
        data_yaml_path = Path(args.data).resolve()
    else:
        data_yaml_path = project_root / "module_ai_core" / "datasets" / "data.yaml"

    if not args.skip_preprocess:
        logger.info("🔍 Tiến hành tiền xử lý và lọc sạch dữ liệu Pose trước khi huấn luyện...")
        preprocess_fall_dataset(clean_corrupted=True)
    else:
        update_data_yaml(yaml_path=data_yaml_path)

    # 2. Thiết lập thiết bị phần cứng
    if args.device is not None:
        device = args.device
    elif torch.cuda.is_available():
        device = "0"
    else:
        device = "cpu"

    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    if not cuda_available and str(device) not in ("cpu", "CPU"):
        logger.warning(f"⚠️ Thiết bị '{device}' không khả thi (không có CUDA). Tự động chuyển sang CPU.")
        device = "cpu"

    # 3. Base model checkpoint yolo11m-pose.pt
    model_arg_path = Path(args.model)
    local_in_module = project_root / "module_ai_core" / "fall_detection" / model_arg_path.name
    if model_arg_path.exists():
        model_source = str(model_arg_path.resolve())
    elif local_in_module.exists():
        model_source = str(local_in_module.resolve())
    else:
        model_source = model_arg_path.name

    model_name = Path(model_source).stem

    logger.info("=" * 70)
    logger.info(f"🚀 KÍCH HOẠT HUẤN LUYỆN CAO CẤP MODEL {model_name.upper()} (EXP_POSE_MAX)")
    logger.info(f"   ├─ Base Checkpoint : {model_source}")
    logger.info(f"   ├─ Data Config     : {data_yaml_path}")
    logger.info(f"   ├─ Compute Device  : {device} ({device_name})")
    logger.info(f"   ├─ Schedule        : Epochs={args.epochs}, Batch={args.batch}, ImgSz={args.imgsz}")
    logger.info(f"   ├─ Optimizer       : {args.optimizer} (lr0={args.lr0}, lrf={args.lrf}, decay={args.weight_decay})")
    logger.info(f"   ├─ Loss Gains      : Pose={args.pose}, KObj={args.kobj}, Box={args.box}, Cls={args.cls}")
    logger.info(f"   └─ Augmentations   : flipud=0.0 (fixed), fliplr={args.fliplr}, degrees={args.degrees}, amp=True")
    logger.info("=" * 70)

    model = YOLO(model_source)

    # Cấu hình đầy đủ các tham số tối ưu hóa cho YOLOv11m-Pose
    train_args = {
        "data": str(data_yaml_path),
        "epochs": args.epochs,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "optimizer": args.optimizer,
        "lr0": args.lr0,
        "lrf": args.lrf,
        "weight_decay": args.weight_decay,
        "warmup_epochs": args.warmup_epochs,
        "patience": args.patience,
        "close_mosaic": args.close_mosaic,
        "degrees": args.degrees,
        "fliplr": args.fliplr,
        "flipud": 0.0,  # Tuyệt đối không lật dọc với tư thế ngã
        "pose": args.pose,
        "kobj": args.kobj,
        "box": args.box,
        "cls": args.cls,
        "amp": True,  # Kích hoạt FP16 Automatic Mixed Precision tối ưu Tesla V100 Tensor Cores
        "workers": args.workers,
        "project": "runs/fall_detection",
        "name": "exp_pose_max",
        "save": True,
        "device": device,
        "exist_ok": True,
    }

    # Kích hoạt quá trình huấn luyện
    model.train(**train_args)
    logger.info("✅ Quá trình huấn luyện model.train() đã hoàn tất thành công!")

    # 4. Đánh giá mô hình trên tập TEST sau khi huấn luyện xong
    logger.info("📊 Tiến hành đánh giá tự động trên tập TEST (split='test')...")
    val_results = model.val(
        data=str(data_yaml_path),
        split="test",
        imgsz=args.imgsz,
        device=device,
    )

    # Trích xuất chi tiết Box và Pose metrics
    metrics = {
        "box_precision": 0.0,
        "box_recall": 0.0,
        "box_map50": 0.0,
        "box_map50_95": 0.0,
        "pose_precision": 0.0,
        "pose_recall": 0.0,
        "pose_map50": 0.0,
        "pose_map50_95": 0.0,
    }

    # Trích xuất Box Metrics
    if hasattr(val_results, "box") and val_results.box is not None:
        b = val_results.box
        metrics["box_precision"] = safe_float(getattr(b, "mp", getattr(b, "p", 0.0)))
        metrics["box_recall"] = safe_float(getattr(b, "mr", getattr(b, "r", 0.0)))
        metrics["box_map50"] = safe_float(getattr(b, "map50", 0.0))
        metrics["box_map50_95"] = safe_float(getattr(b, "map", 0.0))

    # Trích xuất Pose Metrics
    if hasattr(val_results, "pose") and val_results.pose is not None:
        p = val_results.pose
        metrics["pose_precision"] = safe_float(getattr(p, "mp", getattr(p, "p", 0.0)))
        metrics["pose_recall"] = safe_float(getattr(p, "mr", getattr(p, "r", 0.0)))
        metrics["pose_map50"] = safe_float(getattr(p, "map50", 0.0))
        metrics["pose_map50_95"] = safe_float(getattr(p, "map", 0.0))

    # Fallback trích xuất từ results_dict nếu có
    if hasattr(val_results, "results_dict") and val_results.results_dict:
        rd = val_results.results_dict
        if metrics["box_precision"] == 0.0:
            metrics["box_precision"] = safe_float(rd.get("metrics/precision(B)", 0.0))
            metrics["box_recall"] = safe_float(rd.get("metrics/recall(B)", 0.0))
            metrics["box_map50"] = safe_float(rd.get("metrics/mAP50(B)", 0.0))
            metrics["box_map50_95"] = safe_float(rd.get("metrics/mAP50-95(B)", 0.0))

        if metrics["pose_precision"] == 0.0:
            metrics["pose_precision"] = safe_float(rd.get("metrics/precision(p)", 0.0))
            metrics["pose_recall"] = safe_float(rd.get("metrics/recall(p)", 0.0))
            metrics["pose_map50"] = safe_float(rd.get("metrics/mAP50(p)", 0.0))
            metrics["pose_map50_95"] = safe_float(rd.get("metrics/mAP50-95(p)", 0.0))

    logger.info("📈 THÔNG SỐ ĐÁNH GIÁ MÔ HÌNH TRÊN TẬP TEST:")
    logger.info("   ├─ [Bounding Box Metrics]")
    logger.info(f"   │  ├─ Box Precision : {metrics['box_precision']:.4f}")
    logger.info(f"   │  ├─ Box Recall    : {metrics['box_recall']:.4f}")
    logger.info(f"   │  ├─ Box mAP50     : {metrics['box_map50']:.4f}")
    logger.info(f"   │  └─ Box mAP50-95  : {metrics['box_map50_95']:.4f}")
    logger.info("   └─ [Pose Keypoint Metrics]")
    logger.info(f"      ├─ Pose Precision: {metrics['pose_precision']:.4f}")
    logger.info(f"      ├─ Pose Recall   : {metrics['pose_recall']:.4f}")
    logger.info(f"      ├─ Pose mAP50    : {metrics['pose_map50']:.4f}")
    logger.info(f"      └─ Pose mAP50-95 : {metrics['pose_map50_95']:.4f}")

    # 5. Sao chép Checkpoints
    runs_best_pt = project_root / "runs" / "fall_detection" / "exp_pose_max" / "weights" / "best.pt"
    runs_last_pt = project_root / "runs" / "fall_detection" / "exp_pose_max" / "weights" / "last.pt"

    dest_best_1 = project_root / "weights" / "fall_detection" / "best.pt"
    dest_best_2 = project_root / "module_ai_core" / "fall_detection" / "weights" / "best.pt"
    dest_last_2 = project_root / "module_ai_core" / "fall_detection" / "weights" / "last.pt"

    dest_best_1.parent.mkdir(parents=True, exist_ok=True)
    dest_best_2.parent.mkdir(parents=True, exist_ok=True)
    dest_last_2.parent.mkdir(parents=True, exist_ok=True)

    if runs_best_pt.exists():
        shutil.copy2(runs_best_pt, dest_best_1)
        shutil.copy2(runs_best_pt, dest_best_2)
        logger.info(f"📁 Đã sao chép best.pt sang:\n   1. {dest_best_1}\n   2. {dest_best_2}")
    else:
        logger.warning(f"⚠️ Không tìm thấy file checkpoint: {runs_best_pt}")

    if runs_last_pt.exists():
        shutil.copy2(runs_last_pt, dest_last_2)
        logger.info(f"📁 Đã sao chép last.pt sang:\n   1. {dest_last_2}")

    # 6. Cập nhật Model Registry tại weights/registry.json
    registry_path = project_root / "weights" / "registry.json"
    registry = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception as err:
            logger.warning(f"⚠️ Không thể đọc registry.json ({err}), khởi tạo mới.")

    registry["fall_detection"] = {
        "task": "fall_detection",
        "model_name": model_name,
        "status": "ready",
        "path": "weights/fall_detection/best.pt",
        "format": "PyTorch (.pt)",
        "metrics": {
            "box_precision": round(metrics["box_precision"], 4),
            "box_recall": round(metrics["box_recall"], 4),
            "box_map50": round(metrics["box_map50"], 4),
            "box_map50_95": round(metrics["box_map50_95"], 4),
            "pose_precision": round(metrics["pose_precision"], 4),
            "pose_recall": round(metrics["pose_recall"], 4),
            "pose_map50": round(metrics["pose_map50"], 4),
            "pose_map50_95": round(metrics["pose_map50_95"], 4),
        },
        "note": f"Fine-tuned {model_name} (exp_pose_max) on falling-pose-estimation v4 dataset for children fall detection",
    }

    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"✅ Đã tự động cập nhật Model Registry tại: {registry_path}")


if __name__ == "__main__":
    main()
