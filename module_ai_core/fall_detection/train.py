"""
Training script cho Task AI #3: Fall Detection (Pose Estimation).

Phụ trách: P5
Model: YOLO11-Pose (Ultralytics)

Usage:
    python module_ai_core/fall_detection/train.py
    python module_ai_core/fall_detection/train.py --pretrained
    python module_ai_core/fall_detection/train.py --epochs 50 --data ./data/pose/data.yaml
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path

import torch
from loguru import logger

from configs.settings import get_settings
from module_ai_core.models.pose_estimator import PoseEstimator


def download_dataset_roboflow():
    """Tự động tải dữ liệu từ Roboflow vào đúng thư mục module_ai_core/datasets/"""
    try:
        from roboflow import Roboflow
    except ImportError:
        logger.warning("Thư viện 'roboflow' chưa được cài đặt. Bỏ qua tự động tải dataset từ Roboflow.")
        return None

    # 1. Định vị đường dẫn lưu dataset vào folder module_ai_core/datasets/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.abspath(os.path.join(current_dir, "..", "datasets"))
    os.makedirs(dataset_dir, exist_ok=True)

    # Đổi thư mục làm việc hiện tại sang folder datasets để Roboflow tải vào đó
    os.chdir(dataset_dir)

    # 2. Tải dữ liệu Pose từ Roboflow bằng API Key
    logger.info("⏳ Đang kết nối tới Roboflow để tải bộ dữ liệu Pose (falling-pose-estimation)...")
    try:
        rf = Roboflow(api_key="M23OWchANwVdP5BAJGx4") 
        project = rf.workspace("humna-pose-data").project("falling-pose-estimation")
        version = project.version(4)
        dataset = version.download("yolov8")

        # Đường dẫn tuyệt đối đến file data.yaml vừa tải về
        yaml_path = os.path.join(dataset.location, "data.yaml")
        logger.info(f"✅ Tải dữ liệu Pose thành công! File cấu hình tại: {yaml_path}")
    except Exception as e:
        logger.error(f"❌ Lỗi khi tải dữ liệu từ Roboflow: {e}")
        yaml_path = None

    # 3. Quay trở lại thư mục ban đầu để chạy tiếp code dự án
    os.chdir(current_dir)
    return yaml_path


def main():
    parser = argparse.ArgumentParser(description="Train/Prepare Fall Detection (Pose)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument(
        "--data", type=str, default=None,
        help="Path to data.yaml dataset config file.",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Thiet bi huan luyen ('0', 'cuda', 'cpu'). Mac dinh uu tien GPU (0/cuda) neu co.",
    )
    parser.add_argument(
        "--pretrained", action="store_true",
        help="Su dung pretrained model tu Ultralytics (khong can train)",
    )
    args = parser.parse_args()

    # Tự động tải dữ liệu nếu chưa chỉ định --data và không phải --pretrained
    if not args.pretrained and args.data is None:
        roboflow_yaml_path = download_dataset_roboflow()
        args.data = roboflow_yaml_path if roboflow_yaml_path else "./data/pose/data.yaml"
    elif args.data is None:
        args.data = "./data/pose/data.yaml"

    settings = get_settings()
    output_dir = Path("weights/fall_detection")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Độc lập xác định thiết bị GPU/CPU cho việc train/fine-tune
    if args.device is not None:
        device = args.device
    elif torch.cuda.is_available():
        device = "0"  # GPU index 0 cho Ultralytics YOLO
    else:
        device = "cpu"

    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"

    if not cuda_available and str(device) not in ("cpu", "CPU"):
        logger.warning(
            f"⚠️ Yêu cầu device='{device}' nhưng PyTorch hiện tại không hỗ trợ CUDA (torch+cpu). "
            f"Tự động chuyển sang device='cpu'."
        )
        device = "cpu"

    logger.info("=" * 50)
    logger.info("Task AI #3: Fall Detection (Pose Estimation)")
    logger.info(f"Target Device : {device}")
    logger.info(f"CUDA Available: {cuda_available} ({device_name})")
    logger.info(f"Data Config   : {args.data}")
    logger.info("=" * 50)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.pretrained:
        # Sử dụng pretrained — download và lưu vào weights/
        logger.info("Sử dụng pretrained YOLO-Pose model...")
        estimator = PoseEstimator(device=device)
        estimator.load()

        final_model_path = output_dir / f"yolo11n-pose-pretrained-{timestamp}.pt"
        # Export pretrained weights
        if hasattr(estimator._model, "save"):
            estimator._model.save(str(final_model_path))
        logger.info(f"Pretrained model saved: {final_model_path}")
    else:
        # Fine-tune trên dữ liệu custom
        logger.info(f"⚡ Fine-tuning Pose model | Epochs: {args.epochs} | Batch: {args.batch} | Device: {device}")
        estimator = PoseEstimator(device=device)
        estimator.train(
            data_yaml=args.data,
            epochs=args.epochs,
            batch_size=args.batch,
            output_dir=str(output_dir),
            device=device,
        )
        
        # Đường dẫn file gốc sau khi train xong
        raw_best_path = output_dir / "train_results" / "weights" / "best.pt"
        
        # Đổi tên file và di chuyển ra ngoài để kèm timestamp tránh bị ghi đè lần sau
        final_model_path = output_dir / f"yolo11n-pose-finetuned-{timestamp}.pt"
        if raw_best_path.exists():
            raw_best_path.rename(final_model_path)
            logger.info(f"Fine-tuned model moved and renamed to: {final_model_path}")
        else:
            final_model_path = raw_best_path  # Phòng hờ nếu lỗi di chuyển file

    # Cập nhật Model Registry (registry.json)
    registry_path = Path("weights/registry.json")
    registry = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text())
        except Exception:
            registry = {}

    registry["fall_detection"] = {
        "status": "ready",
        "path": str(final_model_path),
        "format": "pytorch",
        "note": "pretrained" if args.pretrained else "fine-tuned",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    logger.info(f"✅ Registry updated: {registry_path}")


if __name__ == "__main__":
    main()


