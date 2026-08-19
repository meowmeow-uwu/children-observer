"""
Data Augmentation Pipeline.

Kỹ thuật augmentation cho tập dữ liệu ChildSUn:
- Nhiễu (Gaussian noise, ISO noise)
- Mờ (Motion blur, Gaussian blur)
- Ánh sáng yếu (RandomBrightnessContrast, RandomGamma)
- Biến đổi hình học (Flip, Rotate, Scale)
- Augmentation chuyên biệt cho cảnh trong nhà
"""

from __future__ import annotations

import albumentations as A
from albumentations.pytorch import ToTensorV2


def get_train_transforms(img_size: int = 640) -> A.Compose:
    """
    Pipeline augmentation cho training.

    Mô phỏng các điều kiện thực tế:
    - Camera trong nhà có ánh sáng yếu
    - Ảnh bị nhiễu do camera giá rẻ
    - Vật thể nhỏ ở nhiều góc độ

    Args:
        img_size: Kích thước ảnh đầu ra.

    Returns:
        Albumentation Compose pipeline.
    """
    return A.Compose(
        [
            # Resize giữ tỷ lệ
            A.LongestMaxSize(max_size=img_size),
            A.PadIfNeeded(
                min_height=img_size,
                min_width=img_size,
                border_mode=0,  # cv2.BORDER_CONSTANT
                fill=114,
            ),

            # Biến đổi hình học
            A.HorizontalFlip(p=0.5),
            A.Rotate(limit=15, p=0.3, border_mode=0),
            A.Affine(
                scale=(0.8, 1.2),
                translate_percent={"x": (-0.1, 0.1), "y": (-0.1, 0.1)},
                p=0.3,
            ),

            # Ánh sáng & màu sắc (mô phỏng camera trong nhà)
            A.OneOf([
                A.RandomBrightnessContrast(
                    brightness_limit=(-0.3, 0.2),
                    contrast_limit=(-0.2, 0.2),
                    p=1.0,
                ),
                A.RandomGamma(gamma_limit=(70, 130), p=1.0),
                A.CLAHE(clip_limit=4.0, p=1.0),
            ], p=0.5),

            # Nhiễu (mô phỏng camera IP giá rẻ)
            A.OneOf([
                A.GaussNoise(std_range=(0.01, 0.05), p=1.0),
                A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
            ], p=0.3),

            # Mờ (mô phỏng chuyển động, lệch focus)
            A.OneOf([
                A.MotionBlur(blur_limit=7, p=1.0),
                A.GaussianBlur(blur_limit=(3, 7), p=1.0),
                A.Defocus(radius=(3, 5), p=1.0),
            ], p=0.2),

            # Hiệu ứng thời tiết/ánh sáng đặc biệt
            A.OneOf([
                A.RandomShadow(p=1.0),
                A.RandomFog(fog_coef_range=(0.1, 0.3), p=1.0),
            ], p=0.1),

            # Color jitter nhẹ
            A.HueSaturationValue(
                hue_shift_limit=10,
                sat_shift_limit=20,
                val_shift_limit=15,
                p=0.3,
            ),

            # Normalize và convert
            A.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
            ToTensorV2(),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            min_visibility=0.3,
        ),
    )


def get_val_transforms(img_size: int = 640) -> A.Compose:
    """
    Pipeline transform cho validation/test (không augmentation).

    Args:
        img_size: Kích thước ảnh đầu ra.

    Returns:
        Albumentation Compose pipeline.
    """
    return A.Compose(
        [
            A.LongestMaxSize(max_size=img_size),
            A.PadIfNeeded(
                min_height=img_size,
                min_width=img_size,
                border_mode=0,
                fill=114,
            ),
            A.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
            ToTensorV2(),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            min_visibility=0.3,
        ),
    )


def get_skeleton_augmentation(sequence_length: int = 30) -> dict:
    """
    Augmentation config cho skeleton sequences (dùng trong behavior classifier).

    Returns:
        Dict chứa các tham số augmentation cho skeleton data.
    """
    return {
        "random_shift": {
            "enabled": True,
            "max_shift": 0.05,  # 5% shift trên mỗi keypoint
        },
        "random_scale": {
            "enabled": True,
            "scale_range": (0.9, 1.1),
        },
        "temporal_crop": {
            "enabled": True,
            "crop_ratio": 0.9,  # Giữ 90% frames
        },
        "joint_dropout": {
            "enabled": True,
            "dropout_rate": 0.05,  # 5% keypoints bị ẩn
        },
        "gaussian_noise": {
            "enabled": True,
            "std": 0.01,
        },
    }
