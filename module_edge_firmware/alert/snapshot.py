"""
Snapshot Generator.

Tạo ảnh snapshot khi có cảnh báo:
- Ảnh toàn cảnh (full frame)
- Ảnh crop phóng đại vùng sự kiện
"""

from __future__ import annotations

from pathlib import Path
import time

import cv2
import numpy as np
from loguru import logger


class SnapshotGenerator:
    """Tạo snapshot toàn cảnh + crop phóng đại."""

    def __init__(self, output_dir: str | Path = "./snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture(
        self,
        frame: np.ndarray,
        event_box: np.ndarray | None = None,
        padding: float = 0.3,
    ) -> dict[str, Path]:
        """
        Chụp snapshot toàn cảnh và crop sự kiện.

        Args:
            frame: BGR image.
            event_box: [x1, y1, x2, y2] vùng xảy ra sự kiện.
            padding: Padding ratio khi crop.

        Returns:
            Dict: {"full": Path, "crop": Path}
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results = {}

        # Full snapshot
        full_path = self.output_dir / f"full_{timestamp}.jpg"
        cv2.imwrite(str(full_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        results["full"] = full_path

        # Crop snapshot
        if event_box is not None:
            crop_path = self.output_dir / f"crop_{timestamp}.jpg"
            crop = self._crop_with_padding(frame, event_box, padding)
            cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            results["crop"] = crop_path

        logger.info(f"Snapshots captured: {list(results.keys())}")
        return results

    def _crop_with_padding(
        self, frame: np.ndarray, box: np.ndarray, padding: float
    ) -> np.ndarray:
        """Crop ảnh với padding xung quanh bounding box."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = box[:4].astype(int)

        bw, bh = x2 - x1, y2 - y1
        pad_x = int(bw * padding)
        pad_y = int(bh * padding)

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        return frame[y1:y2, x1:x2].copy()
