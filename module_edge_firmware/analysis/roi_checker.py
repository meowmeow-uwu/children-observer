"""
ROI Checker - Kiểm tra xâm nhập vùng nguy hiểm.

Sử dụng cv2.pointPolygonTest để kiểm tra vị trí trẻ/vật thể
so với các vùng nguy hiểm (polygon) do phụ huynh vẽ.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


class ROIZone:
    """Một vùng nguy hiểm được định nghĩa bởi polygon."""

    def __init__(self, zone_id: str, vertices: list[list[float]], label: str = "danger"):
        self.zone_id = zone_id
        self.label = label
        self.norm_vertices = np.array(vertices, dtype=np.float32)
        self.vertices = self.norm_vertices.copy()  # Sẽ được update bởi ROIChecker
        self._contour = self.vertices.reshape((-1, 1, 2)).astype(np.float32)

        # Tối ưu: Tính toán AABB (Axis-Aligned Bounding Box) để lọc nhanh
        self._min_x = float(np.min(self.vertices[:, 0]))
        self._min_y = float(np.min(self.vertices[:, 1]))
        self._max_x = float(np.max(self.vertices[:, 0]))
        self._max_y = float(np.max(self.vertices[:, 1]))

    def update_scale(self, width: int, height: int):
        """Cập nhật tọa độ pixel dựa trên kích thước frame mới."""
        self.vertices[:, 0] = self.norm_vertices[:, 0] * width
        self.vertices[:, 1] = self.norm_vertices[:, 1] * height
        self._contour = self.vertices.reshape((-1, 1, 2)).astype(np.float32)
        
        # Tối ưu: Tính toán AABB (Axis-Aligned Bounding Box) để lọc nhanh
        self._min_x = np.min(self.vertices[:, 0])
        self._min_y = np.min(self.vertices[:, 1])
        self._max_x = np.max(self.vertices[:, 0])
        self._max_y = np.max(self.vertices[:, 1])

    def contains_point(self, point: tuple[float, float]) -> bool:
        """Kiểm tra điểm có nằm trong vùng polygon không (kèm lọc nhanh AABB)."""
        if self._contour is None or len(self._contour) < 3:
            return False

        px, py = float(point[0]), float(point[1])

        # 1. Lọc nhanh bằng AABB (O(1))
        if not (self._min_x <= px <= self._max_x and self._min_y <= py <= self._max_y):
            return False

        # 2. Kiểm tra chính xác bằng Polygon Test (O(N))
        result = cv2.pointPolygonTest(self._contour, (px, py), measureDist=False)
        return result >= 0

    def distance_to_point(self, point: tuple[float, float]) -> float:
        """Tính khoảng cách từ điểm tới biên polygon (âm = bên trong)."""
        if self._contour is None or len(self._contour) < 3:
            return float('inf')
        pt = (float(point[0]), float(point[1]))
        return cv2.pointPolygonTest(self._contour, pt, measureDist=True)

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "label": self.label,
            "vertices": self.norm_vertices.tolist(), # Lưu tọa độ chuẩn hóa
        }


class ROIChecker:
    """
    Quản lý và kiểm tra nhiều vùng ROI.

    Nhận JSON vertices từ Mobile App, lưu cục bộ,
    và kiểm tra xâm nhập real-time.
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else Path("./configs/roi_zones.json")
        self._zones: dict[str, ROIZone] = {}
        self._current_size: tuple[int, int] | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load ROI config từ file JSON."""
        if not self.config_path.exists():
            logger.info("No ROI config found. Running without zone protection.")
            return

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            for zone_data in data.get("zones", []):
                zone = ROIZone(
                    zone_id=zone_data["zone_id"],
                    vertices=zone_data["vertices"],
                    label=zone_data.get("label", "danger"),
                )
                self._zones[zone.zone_id] = zone

            logger.info(f"Loaded {len(self._zones)} ROI zones")
        except Exception as e:
            logger.error(f"Failed to load ROI config: {e}")

    def update_zones(self, zones_json: list[dict]) -> None:
        """
        Cập nhật ROI zones từ Mobile App (JSON vertices).

        Args:
            zones_json: List of zone dicts với keys: zone_id, vertices, label
        """
        self._zones.clear()

        for zone_data in zones_json:
            zone = ROIZone(
                zone_id=zone_data["zone_id"],
                vertices=zone_data["vertices"],
                label=zone_data.get("label", "danger"),
            )
            self._zones[zone.zone_id] = zone

        # Persist to file
        self._save_config()
        logger.info(f"Updated {len(self._zones)} ROI zones")

    def _save_config(self) -> None:
        """Lưu ROI config xuống file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"zones": [z.to_dict() for z in self._zones.values()]}
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def check_intrusion(self, point: tuple[float, float]) -> list[ROIZone]:
        """
        Kiểm tra điểm có xâm nhập vào vùng nguy hiểm nào không.

        Args:
            point: (x, y) tọa độ pixel.

        Returns:
            Danh sách các ROIZone bị xâm nhập.
        """
        intruded = []
        for zone in self._zones.values():
            if zone.contains_point(point):
                intruded.append(zone)
        return intruded

    def check_box_intrusion(self, box: np.ndarray, frame_size: tuple[int, int] | None = None) -> list[ROIZone]:
        """
        Kiểm tra bounding box có overlap với vùng nguy hiểm không.

        Args:
            box: [x1, y1, x2, y2] bounding box.
            frame_size: (w, h) của frame hiện tại để update scale nếu cần.
        """
        if frame_size and frame_size != self._current_size:
            self._update_all_scales(frame_size)

        # Check 4 corners + center
        x1, y1, x2, y2 = box[:4]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

        points = [(cx, cy), (x1, y1), (x2, y1), (x1, y2), (x2, y2)]

        intruded = set()
        for point in points:
            pt = (float(point[0]), float(point[1]))
            for zone in self._zones.values():
                if zone.zone_id in intruded:
                    continue  # Zone đã match, không cần check lại
                if zone.contains_point(pt):
                    intruded.add(zone.zone_id)

        return [self._zones[zid] for zid in intruded]

    def _update_all_scales(self, frame_size: tuple[int, int]):
        """Cập nhật lại toàn bộ zone pixel coords khi resolution thay đổi."""
        w, h = frame_size
        for zone in self._zones.values():
            zone.update_scale(w, h)
        self._current_size = frame_size
        logger.info(f"ROI scaled to match new resolution: {w}x{h}")

    @property
    def has_zones(self) -> bool:
        return len(self._zones) > 0

    @property
    def zone_count(self) -> int:
        return len(self._zones)

    def draw_zones(self, frame: np.ndarray, alpha: float = 0.3) -> np.ndarray:
        """Vẽ các vùng ROI lên frame để hiển thị overlay."""
        overlay = frame.copy()

        for zone in self._zones.values():
            pts = zone.vertices.astype(np.int32)
            # Vẽ vùng filled bán trong suốt
            cv2.fillPoly(overlay, [pts], (0, 0, 255))
            # Vẽ viền
            cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
            # Vẽ label
            cx, cy = pts.mean(axis=0).astype(int)
            cv2.putText(frame, zone.label, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 2)

        # Blend overlay
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame
