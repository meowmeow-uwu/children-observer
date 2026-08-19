"""
Fall Detection Dataset Loader & Data Normalization Module.

Đảm nhận:
1. Quét và tiền xử lý dữ liệu Pose từ module_ai_core/datasets/{train, valid, test}.
2. Lọc triệt để các nhãn hỏng/lỗi: Chỉ chấp nhận dòng nhãn chứa đúng 56 tokens
   (1 class_id + 4 bbox coords + 17 keypoints * 3 = 51 kpts). Tự động loại bỏ các dòng nhãn 5 tokens (Detection thuần).
3. Chuẩn hóa và kiểm tra phạm vi tọa độ điểm khớp (x, y) trong [0.0, 1.0] và trạng thái visibility v thuộc {0, 1, 2}.
4. Tự động loại bỏ các file `labels.cache` cũ để Ultralytics cập nhật dataset sạch.
5. Cập nhật file `module_ai_core/datasets/data.yaml` với đường dẫn tuyệt đối (absolute path) và kpt_shape: [17, 3].
6. Ghi log chi tiết hệ thống bằng logger từ loguru.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import yaml
from loguru import logger

from configs.settings import get_settings
from module_ai_core.datasets.augmentation import get_train_transforms, get_val_transforms

# Cấu hình chuẩn cho YOLOv11-Pose (17 COCO Keypoints)
FALL_CLASSES = ["person"]
NUM_KEYPOINTS = 17
KEYPOINT_DIM = 3  # (x, y, visibility)
POSE_TOKENS_PER_LINE = 1 + 4 + (NUM_KEYPOINTS * KEYPOINT_DIM)  # 56 tokens
DETECTION_ONLY_TOKENS = 5  # 5 tokens (Class + BBox)

# Index lật đối xứng keypoints khi Horizontal Flip (Trái <-> Phải)
COCO_FLIP_IDX = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


def update_data_yaml(
    dataset_dir: str | Path | None = None,
    yaml_path: str | Path | None = None,
) -> Path:
    """
    Cập nhật và chuẩn hóa file data.yaml với đường dẫn tuyệt đối (Absolute Path).

    Args:
        dataset_dir: Thư mục gốc chứa dataset (mặc định: module_ai_core/datasets).
        yaml_path: Đường dẫn tới file data.yaml (mặc định: module_ai_core/datasets/data.yaml).

    Returns:
        Path tuyệt đối tới file data.yaml vừa cập nhật.
    """
    project_root = Path(__file__).resolve().parents[2]
    if dataset_dir is None:
        dataset_dir = project_root / "module_ai_core" / "datasets"
    else:
        dataset_dir = Path(dataset_dir).resolve()

    if yaml_path is None:
        yaml_path = dataset_dir / "data.yaml"
    else:
        yaml_path = Path(yaml_path).resolve()

    train_img_dir = dataset_dir / "train" / "images"
    valid_img_dir = dataset_dir / "valid" / "images"
    test_img_dir = dataset_dir / "test" / "images"

    data_config = {
        "path": str(dataset_dir.resolve()),
        "train": str(train_img_dir.resolve()),
        "val": str(valid_img_dir.resolve()),
        "test": str(test_img_dir.resolve()),
        "kpt_shape": [NUM_KEYPOINTS, KEYPOINT_DIM],
        "flip_idx": COCO_FLIP_IDX,
        "nc": len(FALL_CLASSES),
        "names": {0: FALL_CLASSES[0]},
        "roboflow": {
            "license": "CC BY 4.0",
            "project": "falling-pose-estimation",
            "url": "https://universe.roboflow.com/humna-pose-data/falling-pose-estimation/dataset/4",
            "version": 4,
            "workspace": "humna-pose-data",
        },
    }

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"✅ Đã chuẩn hóa thành công file data.yaml tại: {yaml_path}")
    logger.info(f"   ├─ Train Path : {train_img_dir}")
    logger.info(f"   ├─ Valid Path : {valid_img_dir}")
    logger.info(f"   ├─ Test Path  : {test_img_dir}")
    logger.info(f"   ├─ kpt_shape  : [{NUM_KEYPOINTS}, {KEYPOINT_DIM}]")
    logger.info(f"   └─ Classes    : {FALL_CLASSES}")

    return yaml_path


class FallDataset:
    """
    Dataset Loader & Normalizer chuyên biệt cho YOLOv11-Pose Fall Detection.

    Thực hiện:
    - Quét và nạp dữ liệu từ split ('train', 'valid', 'test').
    - Lọc bỏ nhãn hỏng, lọc triệt để các dòng nhãn 5-token (Object Detection thuần).
    - Chuẩn hóa và clamp tọa độ điểm khớp về [0.0, 1.0], visibility v in {0, 1, 2}.
    - Ghi đè file nhãn sạch chỉ chứa nhãn 56-token chuẩn Pose.
    - Xóa các file cache nhãn (.cache) để ép Ultralytics load lại nhãn sạch.
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        split: Literal["train", "valid", "test"] = "train",
        img_size: int = 640,
        apply_augmentation: bool = True,
        clean_on_init: bool = True,
    ):
        settings = get_settings()
        project_root = Path(__file__).resolve().parents[2]

        if root_dir:
            self.root_dir = Path(root_dir).resolve()
        elif hasattr(settings, "dataset_fall_path") and settings.dataset_fall_path:
            self.root_dir = Path(settings.dataset_fall_path).resolve()
        else:
            self.root_dir = (project_root / "module_ai_core" / "datasets").resolve()

        self.split = split
        self.img_size = img_size
        self.apply_augmentation = apply_augmentation
        self.classes = FALL_CLASSES

        self.images_dir = self.root_dir / split / "images"
        self.labels_dir = self.root_dir / split / "labels"

        # Khởi tạo Augmentation Pipeline
        if apply_augmentation and split == "train":
            self.transform = get_train_transforms(img_size=img_size)
        else:
            self.transform = get_val_transforms(img_size=img_size)

        self._valid_samples: list[dict] = []
        self._filtered_det_lines = 0
        self._corrupted_images = 0
        self._total_pose_objects = 0

        if clean_on_init:
            self._validate_and_clean()

    def _validate_and_clean(self) -> None:
        """Thực hiện quét, làm sạch và chuẩn hóa toàn bộ ảnh và nhãn Pose trong split."""
        if not self.root_dir.exists():
            logger.warning(f"❌ Không tìm thấy thư mục dataset gốc: {self.root_dir}")
            return

        if not self.images_dir.exists():
            logger.warning(f"⚠️ Không tìm thấy thư mục ảnh: {self.images_dir}")
            return

        # 1. Xóa file cache nhãn cũ (nếu có)
        cache_file = self.root_dir / split_cache_name(self.split)
        if cache_file.exists():
            cache_file.unlink(missing_ok=True)
            logger.info(f"🧹 Đã xóa file cache nhãn cũ: {cache_file.name}")

        labels_cache = self.labels_dir.parent / "labels.cache"
        if labels_cache.exists():
            labels_cache.unlink(missing_ok=True)

        valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        image_files = sorted([f for f in self.images_dir.iterdir() if f.suffix.lower() in valid_exts])

        logger.info(f"⏳ Đang quét và kiểm tra dữ liệu [{self.split.upper()}] ({len(image_files)} ảnh)...")

        for img_path in image_files:
            # Kiểm tra tính toàn vẹn của ảnh
            if not img_path.exists() or img_path.stat().st_size == 0:
                logger.warning(f"⚠️ File ảnh 0-byte/không tồn tại: {img_path.name}")
                self._corrupted_images += 1
                continue

            img = cv2.imread(str(img_path))
            if img is None:
                logger.warning(f"⚠️ Ảnh bị hỏng không thể đọc bằng OpenCV: {img_path.name}")
                self._corrupted_images += 1
                continue

            h, w = img.shape[:2]
            label_path = self.labels_dir / f"{img_path.stem}.txt"
            clean_pose_lines = []

            if label_path.exists() and label_path.stat().st_size > 0:
                with open(label_path, "r", encoding="utf-8") as f:
                    raw_lines = f.readlines()

                rewrite_needed = False
                for line_idx, line in enumerate(raw_lines):
                    parts = line.strip().split()
                    if not parts:
                        continue

                    # Nếu là nhãn Detection thuần (5 tokens), bỏ qua
                    if len(parts) == DETECTION_ONLY_TOKENS:
                        self._filtered_det_lines += 1
                        rewrite_needed = True
                        continue

                    # Kiểm tra đủ 56 tokens cho Pose
                    if len(parts) == POSE_TOKENS_PER_LINE:
                        try:
                            class_id = int(float(parts[0]))
                            bbox = [float(x) for x in parts[1:5]]
                            kpts_raw = [float(x) for x in parts[5:]]

                            # Clamp bbox coordinates in [0.0, 1.0]
                            bbox = [max(0.0, min(1.0, b)) for b in bbox]

                            # Chuẩn hóa keypoints: (x, y) in [0.0, 1.0], v in {0, 1, 2}
                            kpts_normalized = []
                            for i in range(NUM_KEYPOINTS):
                                kx = kpts_raw[i * 3]
                                ky = kpts_raw[i * 3 + 1]
                                kv = kpts_raw[i * 3 + 2]

                                # Clamp coordinates
                                kx = max(0.0, min(1.0, kx))
                                ky = max(0.0, min(1.0, ky))

                                # Visibility state
                                kv_int = int(round(kv))
                                if kv_int not in (0, 1, 2):
                                    kv_int = 0 if kv <= 0 else (2 if kv >= 2 else 1)

                                kpts_normalized.extend([kx, ky, float(kv_int)])

                            # Tạo lại dòng nhãn chuẩn 56 tokens
                            clean_line_str = f"{class_id} " + " ".join(f"{v:.6f}" for v in bbox + kpts_normalized)
                            clean_pose_lines.append(clean_line_str)
                            self._total_pose_objects += 1

                        except ValueError as err:
                            logger.warning(f"⚠️ Lỗi định dạng float tại {label_path.name}:{line_idx+1} - {err}")
                            rewrite_needed = True
                    else:
                        logger.warning(
                            f"⚠️ Bỏ qua dòng nhãn sai token ({len(parts)} tokens, kỳ vọng {POSE_TOKENS_PER_LINE}) "
                            f"tại {label_path.name}:{line_idx+1}"
                        )
                        rewrite_needed = True

                # Nếu phát hiện dòng nhãn 5 tokens hoặc lỗi, ghi đè lại file nhãn sạch
                if rewrite_needed or len(clean_pose_lines) != len(raw_lines):
                    with open(label_path, "w", encoding="utf-8") as f:
                        if clean_pose_lines:
                            f.write("\n".join(clean_pose_lines) + "\n")
                        else:
                            f.write("")  # File nhãn rỗng nếu không có đối tượng Pose nào

            # Lọc triệt để: Nếu ảnh không chứa đối tượng Pose nào, di chuyển sang thư mục phụ để tránh pha loãng dataset (khiến model đoán nhầm 90% ảnh là background rỗng)
            if not clean_pose_lines:
                unused_bg_dir = self.root_dir / self.split / "backgrounds_unused"
                unused_bg_dir.mkdir(parents=True, exist_ok=True)
                
                # Di chuyển ảnh và nhãn rỗng sang unused_bg_dir
                shutil.move(str(img_path), str(unused_bg_dir / img_path.name))
                if label_path.exists():
                    label_path.unlink(missing_ok=True)
                continue

            self._valid_samples.append({
                "image_path": img_path,
                "label_path": label_path if label_path.exists() else None,
                "num_pose_objects": len(clean_pose_lines),
                "height": h,
                "width": w,
            })

        logger.info(
            f"✅ Tập [{self.split.upper()}]: Đã giữ lại {len(self._valid_samples)} ảnh có nhãn Pose chuẩn | "
            f"Tổng {self._total_pose_objects} đối tượng Pose | "
            f"Đã lọc & cách ly các nhãn Detection 5-token / ảnh rỗng | "
            f"Ảnh lỗi: {self._corrupted_images}"
        )

    def __len__(self) -> int:
        return len(self._valid_samples)

    def __getitem__(self, idx: int) -> dict:
        sample = self._valid_samples[idx]
        img_path = sample["image_path"]
        image = cv2.imread(str(img_path))

        if image is None:
            raise FileNotFoundError(f"Không thể đọc ảnh: {img_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        return {
            "image": image,
            "image_path": img_path,
            "image_id": img_path.stem,
            "height": sample["height"],
            "width": sample["width"],
            "num_pose_objects": sample["num_pose_objects"],
        }

    def get_stats(self) -> dict:
        return {
            "split": self.split,
            "root_dir": str(self.root_dir),
            "valid_images": len(self._valid_samples),
            "corrupted_images": self._corrupted_images,
            "filtered_det_only_lines": self._filtered_det_lines,
            "total_pose_objects": self._total_pose_objects,
            "kpt_shape": [NUM_KEYPOINTS, KEYPOINT_DIM],
        }


def split_cache_name(split: str) -> str:
    """Tạo tên file cache tương ứng với split."""
    return f"{split}.cache" if split in ("train", "valid", "test") else "labels.cache"


def preprocess_fall_dataset(clean_corrupted: bool = True) -> dict:
    """
    Tiền xử lý toàn bộ dataset Fall Detection (train, valid, test) và cập nhật data.yaml.

    Returns:
        Dict tổng hợp thống kê cả 3 tập dữ liệu.
    """
    logger.info("🚀 BẮT ĐẦU TIỀN XỬ LÝ VÀ CHUẨN HÓA DỮ LIỆU FALL DETECTION (YOLOv11-POSE)")

    # 1. Cập nhật data.yaml
    yaml_path = update_data_yaml()

    # 2. Quét và làm sạch 3 tập dữ liệu
    overall_stats = {}
    for split in ["train", "valid", "test"]:
        dataset_loader = FallDataset(split=split, apply_augmentation=(split == "train"), clean_on_init=True)
        stats = dataset_loader.get_stats()
        overall_stats[split] = stats

    logger.info("🎉 TẤT CẢ DỮ LIỆU POSE ĐÃ ĐƯỢC CHUẨN HÓA SẠCH VÀ SẴN SÀNG HUẤN LUYỆN!")
    return overall_stats


if __name__ == "__main__":
    preprocess_fall_dataset(clean_corrupted=True)
