"""
Violence Behavior Dataset Loader.

Quản lý tập dữ liệu hành vi bạo lực cho việc huấn luyện mô hình
phân loại hành vi: tát, đá, đẩy, xô, kéo tóc...

Dataset bao gồm:
- Video clips đã được gán nhãn hành vi
- Skeleton sequences (keypoints theo thời gian)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from loguru import logger

from configs.settings import get_settings

# Nhãn hành vi bạo lực
VIOLENCE_CLASSES = [
    "normal",          # Hành vi bình thường
    "slap",            # Tát
    "kick",            # Đá
    "push",            # Đẩy
    "pull_hair",       # Kéo tóc
    "shake",           # Lắc/xóc
    "hit_object",      # Đánh bằng vật
    "fall_injury",     # Té ngã chấn thương
    "fall_play",       # Té ngã chơi đùa (không nguy hiểm)
]

# Số keypoints trong skeleton (COCO format: 17 keypoints)
NUM_KEYPOINTS = 17
SKELETON_DIM = 3  # x, y, confidence


class ViolenceDataset:
    """
    Dataset loader cho dữ liệu hành vi bạo lực.

    Hỗ trợ 2 kiểu dữ liệu:
    - Video clips: Trích xuất frames và skeleton sequences
    - Pre-extracted skeletons: File JSON chứa keypoints theo thời gian

    Args:
        root_dir: Đường dẫn gốc tới thư mục dataset.
        split: Phân chia dữ liệu ('train', 'val', 'test').
        sequence_length: Số frames trong mỗi sequence.
        data_type: Loại dữ liệu ('video' hoặc 'skeleton').
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        split: Literal["train", "val", "test"] = "train",
        sequence_length: int = 30,
        data_type: Literal["video", "skeleton"] = "skeleton",
    ):
        settings = get_settings()
        self.root_dir = Path(root_dir) if root_dir else settings.dataset_violence_path
        self.split = split
        self.sequence_length = sequence_length
        self.data_type = data_type
        self.classes = VIOLENCE_CLASSES

        self._samples: list[dict] = []
        self._load_annotations()

    def _load_annotations(self) -> None:
        """Load danh sách samples từ file annotation."""
        ann_file = self.root_dir / self.split / "annotations.json"

        if not ann_file.exists():
            logger.warning(f"Violence annotations not found: {ann_file}")
            logger.info("Run 'python scripts/download_dataset.py' to download violence dataset")
            return

        with open(ann_file) as f:
            annotations = json.load(f)

        self._samples = annotations.get("samples", [])
        logger.info(
            f"Violence [{self.split}]: Loaded {len(self._samples)} samples "
            f"({self.data_type} mode)"
        )

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> dict:
        """
        Load một sample.

        Returns:
            dict với keys:
            - 'skeleton': np.ndarray shape (T, num_keypoints, 3) - skeleton sequence
            - 'label': int - class ID
            - 'label_name': str - tên class
            - 'metadata': dict - thông tin bổ sung
        """
        sample_info = self._samples[idx]

        if self.data_type == "skeleton":
            skeleton = self._load_skeleton(sample_info)
        else:
            skeleton = self._extract_skeleton_from_video(sample_info)

        label = sample_info.get("label", 0)

        return {
            "skeleton": skeleton,
            "label": label,
            "label_name": self.get_class_name(label),
            "metadata": {
                "sample_id": sample_info.get("id", idx),
                "source": sample_info.get("source", "unknown"),
                "duration": sample_info.get("duration", 0),
            },
        }

    def _load_skeleton(self, sample_info: dict) -> np.ndarray:
        """
        Load pre-extracted skeleton sequence từ file JSON.

        Returns:
            np.ndarray shape (sequence_length, NUM_KEYPOINTS, SKELETON_DIM)
        """
        skeleton_file = self.root_dir / self.split / "skeletons" / sample_info["skeleton_file"]

        if not skeleton_file.exists():
            logger.warning(f"Skeleton file not found: {skeleton_file}")
            return np.zeros(
                (self.sequence_length, NUM_KEYPOINTS, SKELETON_DIM), dtype=np.float32
            )

        with open(skeleton_file) as f:
            skeleton_data = json.load(f)

        frames = skeleton_data.get("frames", [])
        skeleton_seq = []

        for frame in frames:
            keypoints = frame.get("keypoints", [])
            if len(keypoints) == NUM_KEYPOINTS * SKELETON_DIM:
                kps = np.array(keypoints, dtype=np.float32).reshape(NUM_KEYPOINTS, SKELETON_DIM)
            else:
                kps = np.zeros((NUM_KEYPOINTS, SKELETON_DIM), dtype=np.float32)
            skeleton_seq.append(kps)

        skeleton_seq = np.array(skeleton_seq, dtype=np.float32)

        # Pad or truncate to fixed sequence length
        skeleton_seq = self._normalize_sequence(skeleton_seq)

        return skeleton_seq

    def _extract_skeleton_from_video(self, sample_info: dict) -> np.ndarray:
        """
        Trích xuất skeleton từ video clip sử dụng pose estimator.

        Returns:
            np.ndarray shape (sequence_length, NUM_KEYPOINTS, SKELETON_DIM)
        """
        video_path = self.root_dir / self.split / "videos" / sample_info["video_file"]

        if not video_path.exists():
            logger.warning(f"Video file not found: {video_path}")
            return np.zeros(
                (self.sequence_length, NUM_KEYPOINTS, SKELETON_DIM), dtype=np.float32
            )

        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Sample frames uniformly
        if total_frames <= 0:
            cap.release()
            return np.zeros(
                (self.sequence_length, NUM_KEYPOINTS, SKELETON_DIM), dtype=np.float32
            )

        frame_indices = np.linspace(0, total_frames - 1, self.sequence_length, dtype=int)
        frames = []

        for fi in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
            else:
                frames.append(np.zeros((480, 640, 3), dtype=np.uint8))

        cap.release()

        # Placeholder: skeleton extraction sẽ dùng PoseEstimator
        # Trả về zeros cho bây giờ - sẽ integrate với module inference
        skeleton_seq = np.zeros(
            (self.sequence_length, NUM_KEYPOINTS, SKELETON_DIM), dtype=np.float32
        )

        return skeleton_seq

    def _normalize_sequence(self, skeleton_seq: np.ndarray) -> np.ndarray:
        """Pad hoặc truncate sequence về đúng sequence_length."""
        current_len = skeleton_seq.shape[0]

        if current_len == self.sequence_length:
            return skeleton_seq
        elif current_len > self.sequence_length:
            # Uniform sampling
            indices = np.linspace(0, current_len - 1, self.sequence_length, dtype=int)
            return skeleton_seq[indices]
        else:
            # Pad with last frame
            padding = np.repeat(
                skeleton_seq[-1:], self.sequence_length - current_len, axis=0
            )
            return np.concatenate([skeleton_seq, padding], axis=0)

    def get_class_name(self, class_id: int) -> str:
        """Lấy tên class từ class ID."""
        if 0 <= class_id < len(self.classes):
            return self.classes[class_id]
        return f"unknown_{class_id}"

    def get_stats(self) -> dict:
        """Thống kê dataset."""
        stats = {
            "total_samples": len(self),
            "split": self.split,
            "sequence_length": self.sequence_length,
            "class_distribution": {name: 0 for name in self.classes},
        }

        for sample in self._samples:
            label = sample.get("label", 0)
            class_name = self.get_class_name(label)
            if class_name in stats["class_distribution"]:
                stats["class_distribution"][class_name] += 1

        return stats
