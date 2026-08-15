"""
ROI State Engine — enter / stayTooLong / approach với hysteresis + cooldown.

- enterZone   : CHỈ fire tại transition outside → inside (sau confirm_in frame).
                Track ở nguyên trong zone KHÔNG fire lại dù hết cooldown.
- stayTooLong : cùng track_id quan sát trong zone đủ giây (có tolerance cho
                detector gap), fire một lần mỗi lần ở trong.
- approachZone: khoảng cách tới biên giảm liên tục với delta tối thiểu, chuỗi
                phẳng hoặc nhiễu nhỏ không fire.
- Hysteresis  : confirm_in frame để "vào", confirm_out frame để "ra".
- Cooldown    : key (camera, zone, track, rule), clock monotonic liên tục,
                sentinel None (không dùng 0).
- Pause       : chặn phát alert; resume chỉ xét transition mới, không bù sự kiện cũ.
- Chỉ track `confirmed` được xét rule (provisional không gây alert).
- ROI presence: điểm chân nằm trong vùng HOẶC ít nhất 15% diện tích box giao
                vùng. Cách lai giữ đúng vùng sàn nhưng vẫn khớp trực giác UI
                khi người dùng vẽ vùng lên thân người/vật thể trong phối cảnh.

Sensitivity ánh xạ UX:
  high  → conf_min 0.15, confirm_in 2, confirm_out 5, approach_margin 0.12
  medium→ conf_min 0.10, confirm_in 3, confirm_out 6, approach_margin 0.09
  low   → conf_min 0.05, confirm_in 5, confirm_out 8, approach_margin 0.06
High dễ bắt hơn và xác nhận nhanh hơn; low chặt hơn.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
import cv2
import numpy as np
from loguru import logger

SENSITIVITY_CONFIG: dict[str, dict[str, float | int]] = {
    "high": {"conf_min": 0.15, "confirm_in": 2, "confirm_out": 5, "approach_margin": 0.12},
    "medium": {"conf_min": 0.10, "confirm_in": 3, "confirm_out": 6, "approach_margin": 0.09},
    "low": {"conf_min": 0.05, "confirm_in": 5, "confirm_out": 8, "approach_margin": 0.06},
}

# Track state hết hạn sau bao lâu không được quan sát (ms) → prune
TRACK_STATE_TTL_MS = 2000.0
# Tolerance cho detector gap khi tính stayTooLong: khoảng cách giữa 2 lần quan
# sát liên tiếp không được vượt quá ngưỡng này (ms) để vẫn tính là "liên tục"
STAY_GAP_TOLERANCE_MS = 500.0
# Delta tối thiểu mỗi bước khi xét approach (tránh chuỗi phẳng/nhiễu)
APPROACH_MIN_DELTA = 0.004
# Điểm đại diện vị trí trên sàn: giữa cạnh dưới box, dịch lên 3% chiều cao.
# Inset nhỏ giúp tránh bật/tắt khi đáy box dao động đúng trên biên ROI.
FOOTPOINT_INSET_RATIO = 0.03
# Ngưỡng phần diện tích bounding box nằm trong ROI. Chống báo khi chỉ sượt mép.
BOX_ZONE_OVERLAP_RATIO = 0.15


@dataclass
class ZoneConfig:
    zone_id: str
    name: str
    points: list[dict]  # [{x, y}] normalized 0-1
    enabled: bool = True
    sensitivity: str = "medium"
    rules: dict = field(default_factory=dict)
    type: str = "polygon"

    @property
    def enter_zone(self) -> bool:
        return bool(self.rules.get("enterZone", True))

    @property
    def stay_too_long(self) -> bool:
        return bool(self.rules.get("stayTooLong", False))

    @property
    def stay_duration_seconds(self) -> float:
        try:
            return max(1.0, float(self.rules.get("stayDurationSeconds", 5)))
        except (TypeError, ValueError):
            return 5.0

    @property
    def approach_zone(self) -> bool:
        return bool(self.rules.get("approachZone", False))

    def polygon(self) -> np.ndarray:
        pts = np.array([[p["x"], p["y"]] for p in self.points], dtype=np.float64)
        return pts.reshape((-1, 1, 2))

    def signature(self) -> str:
        """Dấu vân tay cấu hình — đổi bất kỳ trường nào → state zone phải reset."""
        return repr(sorted(self.points, key=lambda p: (p["x"], p["y"]))) + (
            f"|{self.enabled}|{self.sensitivity}|{self.rules}|{self.type}"
        )

    @property
    def is_valid(self) -> bool:
        return len(self.points) >= 3


@dataclass
class TrackZoneState:
    """Trạng thái của một track_id đối với một zone."""
    zone_id: str
    inside_confirm: int = 0  # số frame liên tiếp đang ở trong
    outside_confirm: int = 0  # số frame liên tiếp đang ở ngoài
    inside: bool = False
    entered_at_ms: float = 0.0
    last_seen_ms: float = 0.0
    last_inside_observed_ms: float = 0.0  # mốc quan sát trong zone (cho stayTooLong)
    observed_inside_ms: float = 0.0  # tổng thời gian quan sát trong zone
    stay_alerted: bool = False
    enter_fired: bool = False
    approach_fired: bool = False
    distances: deque = field(default_factory=lambda: deque(maxlen=8))
    last_breach_ms: float = 0.0


@dataclass
class AlertEvent:
    camera_id: str
    zone_id: str
    zone_name: str
    rule: str  # enterZone | stayTooLong | approachZone
    track_id: int
    confidence: float
    box: list[float]  # normalized 0-1
    at_ms: float
    title: str


class RoiStateEngine:
    def __init__(
        self,
        camera_id: str,
        cooldown_seconds: float = 30.0,
        approach_frames: int = 4,
        default_sensitivity: str = "medium",
    ):
        self.camera_id = camera_id
        self.cooldown_seconds = cooldown_seconds
        self.approach_frames = approach_frames
        self.default_sensitivity = default_sensitivity

        self._lock = threading.Lock()
        self._zones: dict[str, ZoneConfig] = {}
        self._zone_signatures: dict[str, str] = {}
        self._track_state: dict[tuple[int, str], TrackZoneState] = {}
        # (camera, zone, track, rule) → last fire source_time_ms | None
        self._last_fire: dict[tuple[str, str, int, str], float | None] = {}
        self._paused = False

    # ---- Zone management (thread-safe, immutable snapshot cho update) ----
    def set_zones(self, zones: list[dict]) -> None:
        """Thay thế toàn bộ zone list từ backend (poll/relay).

        Zone đổi geometry/rules/sensitivity → reset state của zone đó.
        Zone bị xóa → xóa state. Dùng lock; update() chụp snapshot nên pipeline
        có thể chạy song song với poll.
        """
        next_zones: dict[str, ZoneConfig] = {}
        next_signatures: dict[str, str] = {}
        for z in zones:
            zone_id = str(z.get("id") or z.get("zone_id") or "")
            if not zone_id:
                continue
            cfg = ZoneConfig(
                zone_id=zone_id,
                name=str(z.get("name") or f"Vùng {zone_id}"),
                points=z.get("points") or [],
                enabled=bool(z.get("enabled", True)),
                sensitivity=str(z.get("sensitivity") or self.default_sensitivity),
                rules=z.get("rules") or {},
                type=str(z.get("type") or "polygon"),
            )
            if cfg.is_valid:
                next_zones[zone_id] = cfg
                next_signatures[zone_id] = cfg.signature()

        with self._lock:
            for zone_id, cfg in next_zones.items():
                old_sig = self._zone_signatures.get(zone_id)
                if old_sig is not None and old_sig != next_signatures[zone_id]:
                    self._clear_zone_state(zone_id)
                    logger.info(f"ROI engine: zone {zone_id} cấu hình thay đổi → reset state")
            removed = set(self._zones) - set(next_zones)
            for zone_id in removed:
                self._clear_zone_state(zone_id)
            self._zones = next_zones
            self._zone_signatures = next_signatures
        logger.info(f"ROI engine: {len(self._zones)} zones (removed {len(removed)})")

    def _clear_zone_state(self, zone_id: str) -> None:
        self._track_state = {k: v for k, v in self._track_state.items() if v.zone_id != zone_id}
        self._last_fire = {
            k: v for k, v in self._last_fire.items() if k[1] != zone_id
        }

    def set_paused(self, paused: bool) -> None:
        """Tạm dừng phát sinh cảnh báo (vẫn theo dõi; resume không phát bù)."""
        with self._lock:
            if paused != self._paused:
                self._paused = paused
                logger.info(f"ROI engine: alerts {'paused' if paused else 'resumed'}")

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    @property
    def zone_count(self) -> int:
        with self._lock:
            return len(self._zones)

    # ---- Core update ----
    def update(self, tracks: list[dict], now_ms: float | None = None) -> list[AlertEvent]:
        """Nhận tracks mới nhất, trả về alert events mới (đã qua cooldown).

        `now_ms` là clock monotonic liên tục của pipeline (source_time_ms).
        Đồng thời đánh dấu zone breach trên track (cho overlay màu đỏ).
        """
        if now_ms is None:
            now_ms = time.monotonic() * 1000.0

        with self._lock:
            zones = list(self._zones.values())
            paused = self._paused

        alerts: list[AlertEvent] = []
        if not zones:
            return alerts

        # Marker là kết quả của RIÊNG frame hiện tại; xóa giá trị frame trước
        # để object track tái sử dụng không bị giữ đỏ sau khi đã ra khỏi ROI.
        for track in tracks:
            track.pop("zone_breach", None)
            track.pop("zone_id", None)
            track.pop("zone_name", None)

        # Chỉ track confirmed được xét rule (provisional không gây alert)
        confirmed_tracks = [t for t in tracks if t.get("confirmed")]

        for track in confirmed_tracks:
            track_id = int(track["track_id"])
            box = track["box"]
            foot_x, foot_y = self._roi_anchor(box)

            for zone in zones:
                if not zone.enabled or not zone.is_valid:
                    continue

                key = (track_id, zone.zone_id)

                cfg = SENSITIVITY_CONFIG.get(zone.sensitivity, SENSITIVITY_CONFIG["medium"])
                if track.get("confidence", 0) < cfg["conf_min"]:
                    continue

                state = self._track_state.get(key)
                if state is None:
                    state = TrackZoneState(zone_id=zone.zone_id)
                    self._track_state[key] = state
                state.last_seen_ms = now_ms

                poly = zone.polygon().astype(np.float32)
                foot_inside = cv2.pointPolygonTest(
                    poly, (float(foot_x), float(foot_y)), measureDist=False
                ) >= 0
                overlap_ratio = self._box_zone_overlap_ratio(box, poly)
                inside = foot_inside or overlap_ratio >= BOX_ZONE_OVERLAP_RATIO
                # Approach và enter/stay dùng cùng một điểm đại diện trên sàn.
                dist = self._distance_to_boundary((foot_x, foot_y), zone)

                # ---- Hysteresis: vào/ra vùng ----
                if inside:
                    state.outside_confirm = 0
                    state.inside_confirm += 1
                    # Tolerance: gap quan sát ngắn vẫn tính stayTooLong liên tục
                    if state.last_inside_observed_ms and (
                        now_ms - state.last_inside_observed_ms <= STAY_GAP_TOLERANCE_MS
                    ):
                        state.observed_inside_ms += now_ms - state.last_inside_observed_ms
                    state.last_inside_observed_ms = now_ms
                    if not state.inside and state.inside_confirm >= cfg["confirm_in"]:
                        state.inside = True
                        state.entered_at_ms = now_ms
                        state.enter_fired = False
                        state.stay_alerted = False
                        state.observed_inside_ms = 0.0
                        state.last_inside_observed_ms = now_ms
                else:
                    state.inside_confirm = 0
                    state.last_inside_observed_ms = 0.0
                    if state.inside:
                        state.outside_confirm += 1
                        if state.outside_confirm >= cfg["confirm_out"]:
                            state.inside = False
                            state.stay_alerted = False

                # ---- Rule 1: enterZone — CHỈ tại transition outside → inside ----
                if state.inside and zone.enter_zone and not state.enter_fired:
                    if paused:
                        # Transition xảy ra khi đang pause → đánh dấu đã xử lý
                        # (không replay sau resume; transition mới mới fire).
                        state.enter_fired = True
                    elif self._fire("enterZone", track, zone, now_ms):
                        state.enter_fired = True
                        alerts.append(self._build_alert(track, zone, "enterZone", now_ms))

                # ---- Rule 2: stayTooLong — thời gian QUAN SÁT trong zone ----
                if state.inside and zone.stay_too_long and not state.stay_alerted:
                    elapsed = state.observed_inside_ms / 1000.0
                    if elapsed >= zone.stay_duration_seconds:
                        state.stay_alerted = True
                        if paused:
                            continue  # đánh dấu đã xử lý, không fire
                        if self._fire("stayTooLong", track, zone, now_ms):
                            alerts.append(self._build_alert(track, zone, "stayTooLong", now_ms))

                # ---- Rule 3: approachZone — delta giảm tối thiểu ----
                if zone.approach_zone and not state.inside:
                    if state.approach_fired:
                        # Re-arm sau cooldown khi track rời xa biên
                        last = self._last_fire.get(
                            (self.camera_id, zone.zone_id, track_id, "approachZone")
                        )
                        if last is not None and now_ms - last >= self.cooldown_seconds * 1000.0 and dist > cfg["approach_margin"] * 2:
                            state.approach_fired = False
                            state.distances.clear()
                    else:
                        state.distances.append(dist)
                        if len(state.distances) >= self.approach_frames:
                            seq = list(state.distances)
                            decreasing = all(
                                seq[i] - seq[i + 1] >= APPROACH_MIN_DELTA
                                for i in range(len(seq) - 1)
                            )
                            if decreasing and dist <= cfg["approach_margin"]:
                                state.approach_fired = True
                                if paused:
                                    continue  # đánh dấu đã xử lý, không fire
                                if self._fire("approachZone", track, zone, now_ms):
                                    alerts.append(self._build_alert(track, zone, "approachZone", now_ms))
                elif state.inside:
                    state.distances.clear()

                # ---- Breach marker cho overlay (box đỏ khi thực sự vi phạm) ----
                if state.inside and (zone.enter_zone or zone.stay_too_long):
                    state.last_breach_ms = now_ms
                    track["zone_breach"] = True
                    track["zone_id"] = zone.zone_id
                    track["zone_name"] = zone.name

        # ---- Prune track state hết hạn (kể cả khi update không có track nào) ----
        expired = [
            k
            for k, st in self._track_state.items()
            if now_ms - st.last_seen_ms > TRACK_STATE_TTL_MS
        ]
        for k in expired:
            del self._track_state[k]

        return alerts

    def _fire(self, rule: str, track: dict, zone: ZoneConfig, now_ms: float) -> bool:
        """Cooldown check — key (camera, zone, track, rule), sentinel None.

        now_ms là clock monotonic liên tục (không reset giữa loop)."""
        with self._lock:
            if self._paused:
                return False
            key = (self.camera_id, zone.zone_id, int(track["track_id"]), rule)
            last = self._last_fire.get(key)
            if last is not None and now_ms - last < self.cooldown_seconds * 1000.0:
                return False
            self._last_fire[key] = now_ms
            return True

    def reset_tracks(self) -> None:
        """Xóa toàn bộ state track khi video loop sang vòng mới (track IDs reset)."""
        with self._lock:
            self._track_state.clear()
            self._last_fire.clear()

    def _build_alert(self, track: dict, zone: ZoneConfig, rule: str, now_ms: float) -> AlertEvent:
        labels = {
            "enterZone": "Trẻ đi vào vùng nguy hiểm",
            "stayTooLong": "Trẻ đứng trong vùng nguy hiểm quá lâu",
            "approachZone": "Trẻ tiến lại gần ranh giới vùng nguy hiểm",
        }
        return AlertEvent(
            camera_id=self.camera_id,
            zone_id=zone.zone_id,
            zone_name=zone.name,
            rule=rule,
            track_id=int(track["track_id"]),
            confidence=float(track.get("confidence", 0.0)),
            box=[float(v) for v in track["box"]],
            at_ms=now_ms,
            title=labels.get(rule, rule),
        )

    @staticmethod
    def _roi_anchor(box: list[float]) -> tuple[float, float]:
        """Điểm chân dùng cho ROI: bottom-center, inset 3% chiều cao box."""
        x1, y1, x2, y2 = (float(v) for v in box)
        height = max(0.0, y2 - y1)
        return (x1 + x2) / 2.0, y2 - height * FOOTPOINT_INSET_RATIO

    @staticmethod
    def _box_zone_overlap_ratio(
        box: list[float], polygon: np.ndarray, samples: int = 9
    ) -> float:
        """Ước lượng phần diện tích box nằm trong polygon, hỗ trợ cả ROI lõm.

        Lưới 9×9 đủ ổn định cho rule 12 FPS và rẻ hơn raster mask toàn frame.
        Điểm nằm đúng biên được tính là giao vùng.
        """
        x1, y1, x2, y2 = (float(v) for v in box)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inside_count = 0
        total = samples * samples
        for row in range(samples):
            y = y1 + (row + 0.5) / samples * (y2 - y1)
            for col in range(samples):
                x = x1 + (col + 0.5) / samples * (x2 - x1)
                if cv2.pointPolygonTest(
                    polygon, (float(x), float(y)), measureDist=False
                ) >= 0:
                    inside_count += 1
        return inside_count / total

    @staticmethod
    def _distance_to_boundary(point: tuple[float, float], zone: ZoneConfig) -> float:
        """Khoảng cách từ điểm tới biên đa giác (chuẩn hóa 0-1 space)."""
        poly = zone.polygon().reshape(-1, 2)
        best = math.inf
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            seg_dx, seg_dy = b[0] - a[0], b[1] - a[1]
            length_sq = seg_dx * seg_dx + seg_dy * seg_dy
            if length_sq == 0:
                continue
            t = max(0.0, min(1.0, ((point[0] - a[0]) * seg_dx + (point[1] - a[1]) * seg_dy) / length_sq))
            px, py = a[0] + t * seg_dx, a[1] + t * seg_dy
            best = min(best, math.hypot(point[0] - px, point[1] - py))
        return best
