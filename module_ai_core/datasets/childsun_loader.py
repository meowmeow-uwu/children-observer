"""
ChildSUn Dataset Loader.

Quản lý tập dữ liệu ChildSUn (~5.350 ảnh) cho việc huấn luyện
phát hiện vật thể nguy hiểm: dao, kéo, nĩa, phích nước, ổ điện.

Hỗ trợ:
- YOLO format (txt annotations)
- COCO format (JSON annotations)
- Tự động chia train/val/test
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from loguru import logger

from configs.settings import get_settings


# Nhãn vật thể nguy hiểm trong ChildSUn dataset
CHILDSUN_CLASSES = [
    "child",           # Trẻ em
    "knife",           # Dao
    "scissors",        # Kéo
    "fork",            # Nĩa
    "thermos",         # Phích nước
    "power_outlet",    # Ổ điện
    "lighter",         # Bật lửa
    "medicine",        # Thuốc
    "small_object",    # Vật nhỏ nguy hiểm khác
]


class ChildSUnDataset:
    """
    Dataset loader cho ChildSUn - tập dữ liệu vật thể nguy hiểm với trẻ em.

    Hỗ trợ cả YOLO format và COCO format, tự động chuyển đổi.

    Args:
        root_dir: Đường dẫn gốc tới thư mục dataset.
        split: Phân chia dữ liệu ('train', 'val', 'test').
        img_size: Kích thước ảnh đầu ra.
        format: Định dạng annotation ('yolo' hoặc 'coco').
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        split: Literal["train", "val", "test"] = "train",
        img_size: int = 640,
        format: Literal["yolo", "coco"] = "yolo",
    ):
        settings = get_settings()
        self.root_dir = Path(root_dir) if root_dir else settings.dataset_childsun_path
        self.split = split
        self.img_size = img_size
        self.format = format

        self.images_dir = self.root_dir / split / "images"
        self.labels_dir = self.root_dir / split / "labels"
        self.classes = CHILDSUN_CLASSES

        self._image_files: list[Path] = []
        self._validate_structure()

    def _validate_structure(self) -> None:
        """Kiểm tra cấu trúc thư mục dataset hợp lệ."""
        if not self.root_dir.exists():
            logger.warning(f"Dataset directory not found: {self.root_dir}")
            logger.info("Run 'python scripts/download_dataset.py' to download ChildSUn dataset")
            return

        if not self.images_dir.exists():
            logger.warning(f"Images directory not found: {self.images_dir}")
            return

        # Collect image files
        extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        self._image_files = sorted(
            f for f in self.images_dir.iterdir()
            if f.suffix.lower() in extensions
        )
        logger.info(
            f"ChildSUn [{self.split}]: Found {len(self._image_files)} images "
            f"in {self.images_dir}"
        )

    def __len__(self) -> int:
        return len(self._image_files)

    def __getitem__(self, idx: int) -> dict:
        """
        Load một sample từ dataset.

        Returns:
            dict với keys: 'image' (np.ndarray), 'labels' (np.ndarray),
            'image_path' (Path), 'image_id' (str)
        """
        img_path = self._image_files[idx]
        image = cv2.imread(str(img_path))

        if image is None:
            raise FileNotFoundError(f"Cannot read image: {img_path}")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        labels = self._load_labels(img_path)

        return {
            "image": image,
            "labels": labels,
            "image_path": img_path,
            "image_id": img_path.stem,
        }

    def _load_labels(self, img_path: Path) -> np.ndarray:
        """
        Load annotation tương ứng với ảnh.

        Returns:
            np.ndarray shape (N, 5) với columns [class_id, x_center, y_center, w, h]
            (YOLO format, normalized).
        """
        if self.format == "yolo":
            return self._load_yolo_labels(img_path)
        elif self.format == "coco":
            return self._load_coco_labels(img_path)
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _load_yolo_labels(self, img_path: Path) -> np.ndarray:
        """Load YOLO format labels (.txt file)."""
        label_path = self.labels_dir / f"{img_path.stem}.txt"

        if not label_path.exists():
            return np.zeros((0, 5), dtype=np.float32)

        labels = []
        with open(label_path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    bbox = [float(x) for x in parts[1:5]]
                    labels.append([class_id, *bbox])

        if not labels:
            return np.zeros((0, 5), dtype=np.float32)

        return np.array(labels, dtype=np.float32)

    def _load_coco_labels(self, img_path: Path) -> np.ndarray:
        """Load COCO format labels and convert to YOLO format."""
        coco_path = self.root_dir / self.split / "annotations.json"

        if not coco_path.exists():
            logger.warning(f"COCO annotations not found: {coco_path}")
            return np.zeros((0, 5), dtype=np.float32)

        with open(coco_path) as f:
            coco_data = json.load(f)

        # Find image entry
        img_entry = None
        for img in coco_data.get("images", []):
            if img["file_name"] == img_path.name:
                img_entry = img
                break

        if img_entry is None:
            return np.zeros((0, 5), dtype=np.float32)

        img_w, img_h = img_entry["width"], img_entry["height"]
        img_id = img_entry["id"]

        # Get annotations for this image
        labels = []
        for ann in coco_data.get("annotations", []):
            if ann["image_id"] == img_id:
                x, y, w, h = ann["bbox"]  # COCO format: x_min, y_min, w, h
                # Convert to YOLO format: x_center, y_center, w, h (normalized)
                x_center = (x + w / 2) / img_w
                y_center = (y + h / 2) / img_h
                w_norm = w / img_w
                h_norm = h / img_h
                class_id = ann["category_id"]
                labels.append([class_id, x_center, y_center, w_norm, h_norm])

        if not labels:
            return np.zeros((0, 5), dtype=np.float32)

        return np.array(labels, dtype=np.float32)

    def get_class_name(self, class_id: int) -> str:
        """Lấy tên class từ class ID."""
        if 0 <= class_id < len(self.classes):
            return self.classes[class_id]
        return f"unknown_{class_id}"

    def get_stats(self) -> dict:
        """Thống kê dataset: số ảnh, phân bố class."""
        stats = {
            "total_images": len(self),
            "split": self.split,
            "root_dir": str(self.root_dir),
            "class_distribution": {name: 0 for name in self.classes},
        }

        for idx in range(len(self)):
            try:
                sample = self[idx]
                labels = sample["labels"]
                for label in labels:
                    class_id = int(label[0])
                    class_name = self.get_class_name(class_id)
                    if class_name in stats["class_distribution"]:
                        stats["class_distribution"][class_name] += 1
            except Exception as e:
                logger.warning(f"Error processing image {idx}: {e}")

        return stats

    def prepare_yolo_dataset(self, output_dir: str | Path) -> Path:
        """
        Chuẩn bị dataset theo format YOLO Ultralytics.

        Tạo file data.yaml cần thiết cho training.

        Returns:
            Path tới file data.yaml
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        for split in ["train", "val", "test"]:
            (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
            (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

            src_images = self.root_dir / split / "images"
            src_labels = self.root_dir / split / "labels"

            if src_images.exists():
                for f in src_images.iterdir():
                    shutil.copy2(f, output_dir / split / "images" / f.name)

            if src_labels.exists():
                for f in src_labels.iterdir():
                    shutil.copy2(f, output_dir / split / "labels" / f.name)

        # Create data.yaml
        import yaml

        data_yaml = {
            "path": str(output_dir.resolve()),
            "train": "train/images",
            "val": "val/images",
            "test": "test/images",
            "nc": len(self.classes),
            "names": self.classes,
        }

        yaml_path = output_dir / "data.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"YOLO dataset prepared at: {output_dir}")
        return yaml_path
