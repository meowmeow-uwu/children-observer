"""
Offline Pose Data Augmentation & Expansion Module.

Tăng cường dữ liệu offline cho tập Fall Detection (YOLOv11-Pose):
- Tập TRAIN : Mở rộng từ 384 ảnh gốc -> 5,000 ảnh.
- Tập VALID : Mở rộng từ 109 ảnh gốc -> 600 ảnh (bối cảnh/người độc lập 100%).
- Tập TEST  : Mở rộng từ 56 ảnh gốc -> 600 ảnh (bối cảnh/người độc lập 100%).

Đảm bảo TUYỆT ĐỐI nguyên tắc Zero Data Leakage:
1. Tập Val & Test giữ nguyên tính độc lập từ các video/bối cảnh mới hoàn toàn so với Train.
2. Quá trình Augment chỉ thực hiện NỘI BỘ trong từng tập split (Train -> Train, Val -> Val, Test -> Test).
3. Đảo ngược vị trí keypoints COCO (Trai <-> Phai) khi thực hiện Horizontal Flip.
4. Biến đổi đồng bộ cả Bounding Box và 17 điểm khớp Keypoints (x, y, v).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import albumentations as A
import cv2
import numpy as np
from loguru import logger

# Cấu hình chuẩn COCO 17 Keypoints
NUM_KEYPOINTS = 17
KEYPOINT_DIM = 3
POSE_TOKENS_PER_LINE = 56

# Swap Index cho Horizontal Flip: (0: nose, 1: L_eye, 2: R_eye, ...)
COCO_FLIP_IDX = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]


def create_pose_augmentor(img_size: int = 640) -> A.Compose:
    """Tạo pipeline Albumentations biến đổi đồng bộ Ảnh, Bounding Box và Pose Keypoints."""
    return A.Compose(
        [
            # Biến đổi hình học
            A.HorizontalFlip(p=0.5),
            A.Affine(
                scale=(0.88, 1.12),
                translate_percent={"x": (-0.05, 0.05), "y": (-0.05, 0.05)},
                rotate=(-12, 12),
                shear=(-5, 5),
                p=0.6,
                border_mode=cv2.BORDER_CONSTANT,
            ),
            # Ánh sáng & màu sắc (mô phỏng camera ánh sáng yếu / trong nhà)
            A.OneOf(
                [
                    A.RandomBrightnessContrast(brightness_limit=(-0.25, 0.25), contrast_limit=(-0.2, 0.2), p=1.0),
                    A.RandomGamma(gamma_limit=(75, 125), p=1.0),
                    A.CLAHE(clip_limit=3.0, p=1.0),
                ],
                p=0.6,
            ),
            # HSV / Hue
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=25, val_shift_limit=20, p=0.4),
            # Nhiễu & Mờ camera
            A.OneOf(
                [
                    A.GaussNoise(std_range=(0.01, 0.04), p=1.0),
                    A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                    A.MotionBlur(blur_limit=(3, 5), p=1.0),
                ],
                p=0.35,
            ),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"], min_visibility=0.3),
        keypoint_params=A.KeypointParams(format="xy", remove_invisible=False),
    )


def augment_split(
    split_dir: Path,
    split_name: str,
    target_count: int,
    augmentor: A.Compose,
) -> int:
    """
    Tăng cường dữ liệu nội bộ trong 1 split (train/valid/test).
    Giữ nguyên tính độc lập 100% không rò rỉ dữ liệu giữa các tập.
    """
    img_dir = split_dir / "images"
    lbl_dir = split_dir / "labels"

    if not img_dir.exists() or not lbl_dir.exists():
        logger.warning(f"⚠️ Thư mục split {split_name} không tồn tại: {img_dir}")
        return 0

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    orig_img_files = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in valid_exts])
    
    # Lọc lấy các ảnh thực sự có nhãn Pose
    source_samples = []
    for img_path in orig_img_files:
        lbl_path = lbl_dir / f"{img_path.stem}.txt"
        if lbl_path.exists() and lbl_path.stat().st_size > 0:
            source_samples.append((img_path, lbl_path))

    num_sources = len(source_samples)
    if num_sources == 0:
        logger.warning(f"⚠️ Tập [{split_name.upper()}] không có ảnh gốc nào chứa nhãn Pose!")
        return 0

    logger.info(
        f"🚀 Bắt đầu nhân bản tập [{split_name.upper()}]: Từ {num_sources} ảnh gốc -> Mụctiêu {target_count} ảnh "
        f"(100% Độc lập Zero-Leakage)"
    )

    # Đọc và cache toàn bộ dữ liệu gốc vào RAM
    cached_data = []
    for img_path, lbl_path in source_samples:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        pose_objects = []
        with open(lbl_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == POSE_TOKENS_PER_LINE:
                    cls_id = int(float(parts[0]))
                    bbox = [float(x) for x in parts[1:5]]
                    kpts_raw = [float(x) for x in parts[5:]]
                    pose_objects.append({
                        "cls_id": cls_id,
                        "bbox": bbox,
                        "kpts": kpts_raw,
                    })

        if pose_objects:
            cached_data.append({
                "img_path": img_path,
                "lbl_path": lbl_path,
                "img": img,
                "height": h,
                "width": w,
                "objects": pose_objects,
            })

    num_cached = len(cached_data)
    if num_cached == 0:
        logger.warning(f"⚠️ Tập [{split_name.upper()}]: Không đọc được dữ liệu Pose nào.")
        return 0

    # Tính số ảnh cần sinh thêm
    generated_count = num_cached
    idx = 0

    while generated_count < target_count:
        # Lấy mẫu gốc xoay vòng
        sample = cached_data[idx % num_cached]
        idx += 1

        img = sample["img"].copy()
        h, w = sample["height"], sample["width"]
        objects = sample["objects"]

        # Chuẩn bị bboxes và keypoints cho Albumentations
        bboxes = []
        class_labels = []
        keypoints_xy = []
        visibility_list = []

        for obj in objects:
            bboxes.append(obj["bbox"])
            class_labels.append(obj["cls_id"])
            kpts_raw = obj["kpts"]
            for i in range(NUM_KEYPOINTS):
                kx_norm = kpts_raw[i * 3]
                ky_norm = kpts_raw[i * 3 + 1]
                kv = kpts_raw[i * 3 + 2]
                
                kx_px = kx_norm * w
                ky_px = ky_norm * h
                keypoints_xy.append((kx_px, ky_px))
                visibility_list.append(kv)

        # Áp dụng Augmentation
        try:
            transformed = augmentor(
                image=img,
                bboxes=bboxes,
                class_labels=class_labels,
                keypoints=keypoints_xy,
            )
        except Exception:
            continue

        aug_img = transformed["image"]
        aug_bboxes = transformed["bboxes"]
        aug_labels = transformed["class_labels"]
        aug_kpts_xy = transformed["keypoints"]

        if not aug_bboxes or len(aug_bboxes) != len(bboxes):
            # Nếu bbox bị trượt ra ngoài khung hình, thử lại
            continue

        aug_h, aug_w = aug_img.shape[:2]

        # Kiểm tra xem có bị Horizontal Flip không
        # Nếu tổng tọa độ x bị đảo chiều tương quan
        is_flipped = False
        if len(keypoints_xy) > 0 and len(aug_kpts_xy) == len(keypoints_xy):
            # So sánh điểm mũi (index 0) hoặc điểm khớp chính
            orig_x0 = keypoints_xy[0][0] / w
            aug_x0 = aug_kpts_xy[0][0] / aug_w
            # Nếu vị trí lật ngược khoảng cách đến tâm
            if abs((1.0 - orig_x0) - aug_x0) < abs(orig_x0 - aug_x0) - 0.1:
                is_flipped = True

        # Tái cấu trúc dòng nhãn YOLOv11-Pose
        clean_lines = []
        kpt_idx_counter = 0

        for obj_idx, obj in enumerate(objects):
            if obj_idx >= len(aug_bboxes):
                break
            
            b = aug_bboxes[obj_idx]
            cls_id = aug_labels[obj_idx]

            # Re-format bbox normalized [cx, cy, w, h] in [0.0, 1.0]
            b_norm = [max(0.0, min(1.0, float(x))) for x in b]

            obj_kpts = []
            for i in range(NUM_KEYPOINTS):
                target_i = COCO_FLIP_IDX[i] if is_flipped else i
                curr_kpt_idx = obj_idx * NUM_KEYPOINTS + target_i
                
                if curr_kpt_idx < len(aug_kpts_xy):
                    kx_px, ky_px = aug_kpts_xy[curr_kpt_idx]
                    kv = visibility_list[curr_kpt_idx]
                    
                    kx_norm = max(0.0, min(1.0, kx_px / aug_w))
                    ky_norm = max(0.0, min(1.0, ky_px / aug_h))
                    kv_val = float(int(round(kv)))
                    obj_kpts.extend([kx_norm, ky_norm, kv_val])
                else:
                    obj_kpts.extend([0.0, 0.0, 0.0])

            line_str = f"{cls_id} " + " ".join(f"{v:.6f}" for v in b_norm + obj_kpts)
            clean_lines.append(line_str)

        if not clean_lines:
            continue

        # Lưu ảnh và nhãn mới tăng cường
        new_name = f"aug_{generated_count:05d}_{sample['img_path'].stem}"
        new_img_path = img_dir / f"{new_name}.jpg"
        new_lbl_path = lbl_dir / f"{new_name}.txt"

        cv2.imwrite(str(new_img_path), aug_img)
        with open(new_lbl_path, "w", encoding="utf-8") as f:
            f.write("\n".join(clean_lines) + "\n")

        generated_count += 1

    logger.info(f"✅ Hoàn tất nhân bản tập [{split_name.upper()}]: Hiện tại đạt {generated_count} ảnh Pose chuẩn.")
    return generated_count


def expand_dataset(
    dataset_dir: str | Path | None = None,
    target_train: int = 5000,
    target_val: int = 600,
    target_test: int = 600,
) -> None:
    """Mở rộng toàn bộ dataset theo tỉ lệ mong muốn với Zero Data Leakage."""
    project_root = Path(__file__).resolve().parents[2]
    if dataset_dir is None:
        dataset_dir = project_root / "module_ai_core" / "datasets"
    else:
        dataset_dir = Path(dataset_dir).resolve()

    augmentor = create_pose_augmentor(img_size=640)

    logger.info("=" * 70)
    logger.info("🎯 BẮT ĐẦU TĂNG CƯỜNG DỮ LIỆU OFFLINE CHO POSE FALL DETECTION")
    logger.info(f"   ├─ Tập TRAIN Mụctiêu : {target_train} ảnh")
    logger.info(f"   ├─ Tập VALID Mụctiêu : {target_val} ảnh (Độc lập 100%)")
    logger.info(f"   ├─ Tập TEST  Mụctiêu : {target_test} ảnh (Độc lập 100%)")
    logger.info("   └─ Nguyên tắc        : Zero Data Leakage (Không trùng lặp bối cảnh/người)")
    logger.info("=" * 70)

    # 1. Augment TRAIN
    augment_split(dataset_dir / "train", "train", target_train, augmentor)

    # 2. Augment VALID
    augment_split(dataset_dir / "valid", "valid", target_val, augmentor)

    # 3. Augment TEST
    augment_split(dataset_dir / "test", "test", target_test, augmentor)

    logger.info("🎉 TẤT CẢ CÁC TẬP TRAIN / VALID / TEST ĐÃ ĐƯỢC MỞ RỘNG THÀNH CÔNG!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expand Fall Detection Pose Dataset with Zero Data Leakage")
    parser.add_argument("--train", type=int, default=5000, help="Số lượng ảnh mục tiêu tập Train (mặc định: 5000)")
    parser.add_argument("--val", type=int, default=600, help="Số lượng ảnh mục tiêu tập Valid (mặc định: 600)")
    parser.add_argument("--test", type=int, default=600, help="Số lượng ảnh mục tiêu tập Test (mặc định: 600)")
    args = parser.parse_args()

    expand_dataset(target_train=args.train, target_val=args.val, target_test=args.test)
