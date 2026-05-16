"""
ROI Drawing Tool - Công cụ vẽ vùng nguy hiểm bằng tay.

Cho phép phụ huynh vẽ polygon (vùng nguy hiểm) trực tiếp lên frame
camera bằng chuột, sau đó lưu thành configs/roi_zones.json để
ROIChecker tự động load.

Cách dùng:
    python scripts/draw_roi.py
    python scripts/draw_roi.py --source ./data/sample.mp4
    python scripts/draw_roi.py --source rtsp://admin:pass@192.168.1.100/stream

Điều khiển:
    - Click chuột trái: Thêm điểm vào polygon hiện tại
    - ENTER / SPACE: Hoàn thành polygon hiện tại, bắt đầu vùng mới
    - Z / Backspace: Xóa điểm cuối (undo)
    - C: Xóa toàn bộ polygon đang vẽ
    - D: Xóa zone cuối cùng đã lưu
    - S: Lưu tất cả zones và thoát
    - ESC / Q: Thoát không lưu
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

# ---- Màu sắc cho từng zone (BGR) ----
ZONE_COLORS = [
    (0, 0, 255),    # Đỏ
    (0, 165, 255),  # Cam
    (0, 255, 255),  # Vàng
    (255, 0, 128),  # Tím
    (128, 0, 255),  # Tím nhạt
]

ZONE_LABELS = [
    "bếp_lửa",
    "ổ_điện",
    "cầu_thang",
    "hồ_bơi",
    "vùng_nguy_hiểm",
]


class ROIDrawer:
    """
    Interactive ROI polygon drawing tool.

    Cho phép vẽ nhiều vùng polygon (zone) trên frame camera.
    Mỗi zone có label và màu sắc riêng.
    """

    def __init__(self, source: str | int, output_path: str | Path, frame_interval: int = 30):
        """
        Args:
            source: RTSP URL, đường dẫn video/ảnh, hoặc index camera (0, 1...).
            output_path: Đường dẫn file JSON lưu zones.
            frame_interval: Lấy frame thứ N để vẽ (dùng frame tĩnh ổn định hơn).
        """
        self.source = source
        self.output_path = Path(output_path)
        self.frame_interval = frame_interval

        self._completed_zones: list[dict] = []   # Zones đã hoàn thành
        self._current_points: list[tuple] = []   # Điểm đang vẽ
        self._base_frame: np.ndarray | None = None
        self._display_frame: np.ndarray | None = None
        self._mouse_pos: tuple = (0, 0)
        self._zone_id_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> list[dict] | None:
        """
        Bắt đầu tool vẽ ROI.

        Returns:
            List of zone dicts nếu lưu thành công, None nếu thoát.
        """
        self._base_frame = self._capture_frame()
        if self._base_frame is None:
            print("❌ Không thể mở nguồn video:", self.source)
            return None

        h, w = self._base_frame.shape[:2]
        print(f"\n{'='*60}")
        print(f"  ROI Drawing Tool  |  Frame: {w}x{h}")
        print(f"{'='*60}")
        print("  Click: Thêm điểm | ENTER/SPACE: Xong zone")
        print("  Z: Undo điểm | C: Xóa zone | D: Xóa zone cuối")
        print("  S: Lưu & thoát | ESC/Q: Thoát không lưu")
        print(f"{'='*60}\n")

        cv2.namedWindow("ROI Drawing Tool", cv2.WINDOW_RESIZABLE)
        cv2.setMouseCallback("ROI Drawing Tool", self._mouse_callback)

        while True:
            self._render()
            key = cv2.waitKey(20) & 0xFF

            if key == ord("s"):                     # Lưu và thoát
                result = self._save()
                cv2.destroyAllWindows()
                return result

            elif key in (27, ord("q")):             # ESC / Q — thoát không lưu
                print("Thoát không lưu.")
                cv2.destroyAllWindows()
                return None

            elif key in (13, 32):                   # ENTER / SPACE — hoàn thành zone
                self._finish_zone()

            elif key in (ord("z"), 8):              # Z / Backspace — undo điểm
                if self._current_points:
                    self._current_points.pop()
                    print(f"  Undo — còn {len(self._current_points)} điểm")

            elif key == ord("c"):                   # C — xóa polygon đang vẽ
                self._current_points.clear()
                print("  Đã xóa polygon đang vẽ.")

            elif key == ord("d"):                   # D — xóa zone cuối
                if self._completed_zones:
                    removed = self._completed_zones.pop()
                    print(f"  Đã xóa zone: {removed['label']}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _capture_frame(self) -> np.ndarray | None:
        """Đọc một frame đại diện từ nguồn video."""
        try:
            source = int(self.source)   # Webcam index
        except (ValueError, TypeError):
            source = self.source

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            return None

        frame = None
        for i in range(self.frame_interval + 1):
            ret, f = cap.read()
            if ret:
                frame = f

        cap.release()
        return frame

    def _mouse_callback(self, event, x, y, flags, param):
        """Xử lý sự kiện chuột."""
        self._mouse_pos = (x, y)

        if event == cv2.EVENT_LBUTTONDOWN:
            self._current_points.append((x, y))
            idx = len(self._current_points)
            print(f"  Điểm {idx}: ({x}, {y})")

    def _finish_zone(self):
        """Hoàn thành polygon hiện tại và thêm vào danh sách zones."""
        if len(self._current_points) < 3:
            print("  ⚠️  Cần ít nhất 3 điểm để tạo vùng!")
            return

        color_idx = self._zone_id_counter % len(ZONE_COLORS)
        label_idx = self._zone_id_counter % len(ZONE_LABELS)

        zone = {
            "zone_id": f"zone_{self._zone_id_counter:02d}",
            "label": ZONE_LABELS[label_idx],
            "vertices": [list(p) for p in self._current_points],
            "color": ZONE_COLORS[color_idx],  # chỉ dùng trong tool, không lưu JSON
        }

        self._completed_zones.append(zone)
        self._zone_id_counter += 1

        print(
            f"  ✅ Zone '{zone['label']}' đã lưu "
            f"({len(self._current_points)} điểm) "
            f"→ Tổng: {len(self._completed_zones)} zones"
        )

        self._current_points = []

    def _render(self):
        """Vẽ frame với tất cả zones và polygon đang vẽ."""
        frame = self._base_frame.copy()

        # 1. Vẽ các zones đã hoàn thành
        for zone in self._completed_zones:
            pts = np.array(zone["vertices"], dtype=np.int32)
            color = zone.get("color", (0, 0, 255))

            # Vùng tô màu bán trong suốt
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

            # Viền polygon
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

            # Vẽ các điểm góc
            for p in zone["vertices"]:
                cv2.circle(frame, tuple(int(v) for v in p), 5, color, -1)

            # Label ở tâm
            cx = int(sum(p[0] for p in zone["vertices"]) / len(zone["vertices"]))
            cy = int(sum(p[1] for p in zone["vertices"]) / len(zone["vertices"]))
            cv2.putText(
                frame, zone["zone_id"] + ": " + zone["label"],
                (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2, cv2.LINE_AA,
            )

        # 2. Vẽ polygon đang vẽ
        if self._current_points:
            active_color = ZONE_COLORS[self._zone_id_counter % len(ZONE_COLORS)]

            # Các cạnh đã có
            for i in range(len(self._current_points) - 1):
                cv2.line(frame, self._current_points[i], self._current_points[i + 1],
                         active_color, 2)

            # Đường dẫn đến chuột
            cv2.line(frame, self._current_points[-1], self._mouse_pos,
                     active_color, 1, cv2.LINE_AA)

            # Đường closing (về điểm đầu) nếu >= 3 điểm
            if len(self._current_points) >= 3:
                cv2.line(frame, self._mouse_pos, self._current_points[0],
                         active_color, 1, cv2.LINE_AA)

            # Vẽ các điểm
            for idx, pt in enumerate(self._current_points):
                cv2.circle(frame, pt, 6, active_color, -1)
                cv2.putText(
                    frame, str(idx + 1), (pt[0] + 8, pt[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, active_color, 1,
                )

        # 3. Vẽ HUD (hướng dẫn)
        self._draw_hud(frame)

        cv2.imshow("ROI Drawing Tool", frame)
        self._display_frame = frame

    def _draw_hud(self, frame: np.ndarray):
        """Vẽ thông tin trạng thái lên góc màn hình."""
        h, w = frame.shape[:2]
        lines = [
            f"Zones: {len(self._completed_zones)}  |  "
            f"Dang ve: {len(self._current_points)} diem",
            "ENTER=Xong zone  Z=Undo  C=Xoa  D=Del zone  S=Luu  ESC=Thoat",
        ]

        y = h - 50
        for line in lines:
            # Background đen
            (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (8, y - th - 4), (8 + tw + 4, y + 4), (0, 0, 0), -1)
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (0, 255, 0), 1, cv2.LINE_AA)
            y += th + 14

    def _save(self) -> list[dict] | None:
        """Lưu zones thành file JSON."""
        if not self._completed_zones:
            print("⚠️  Không có zone nào để lưu.")
            return None

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        h, w = self._base_frame.shape[:2]

        # Chỉ lưu những fields cần thiết (bỏ color - chỉ dùng trong UI)
        zones_clean = [
            {
                "zone_id": z["zone_id"],
                "label": z["label"],
                "vertices": [[p[0] / w, p[1] / h] for p in z["vertices"]],
            }
            for z in self._completed_zones
        ]

        data = {"zones": zones_clean}

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Đã lưu {len(zones_clean)} zones → {self.output_path}")
        for z in zones_clean:
            print(f"   • {z['zone_id']} ({z['label']}): {len(z['vertices'])} điểm")

        return zones_clean


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ROI Drawing Tool - Vẽ vùng nguy hiểm bằng tay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Nguồn video: RTSP URL, đường dẫn file, hoặc index webcam (0). "
             "Mặc định: đọc từ .env (RTSP_URL).",
    )
    parser.add_argument(
        "--output",
        default="./configs/roi_zones.json",
        help="Đường dẫn lưu file JSON (default: ./configs/roi_zones.json)",
    )
    parser.add_argument(
        "--frame",
        type=int,
        default=30,
        help="Lấy frame thứ N từ video để vẽ (default: 30)",
    )

    args = parser.parse_args()

    # Lấy RTSP_URL từ .env nếu không truyền --source
    source = args.source
    if source is None:
        try:
            from configs.settings import get_settings
            source = get_settings().rtsp_url
            print(f"Dùng RTSP_URL từ .env: {source}")
        except Exception:
            print("❌ Không tìm thấy --source và không đọc được .env.")
            print("   Dùng: python scripts/draw_roi.py --source ./data/sample.mp4")
            sys.exit(1)

    drawer = ROIDrawer(
        source=source,
        output_path=args.output,
        frame_interval=args.frame,
    )
    result = drawer.run()

    if result:
        print(f"\nĐể sử dụng zones, chạy pipeline:")
        print(f"  python main.py --mode edge")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
