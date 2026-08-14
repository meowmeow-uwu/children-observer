"""
Tests cho ROI State Engine — enter/stay/approach transitions, hysteresis,
cooldown (sentinel None), pause/resume, prune, sensitivity, confirmed-only.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from module_edge_firmware.demo_stream.roi_engine import RoiStateEngine  # noqa: E402

CAMERA = "camera_living_room_01"

# Zone hình vuông lớn [0.2-0.8]
ZONE = {
    "id": 1,
    "name": "Khu vực nguy hiểm",
    "type": "rectangle",
    "points": [{"x": 0.2, "y": 0.2}, {"x": 0.8, "y": 0.2}, {"x": 0.8, "y": 0.8}, {"x": 0.2, "y": 0.8}],
    "sensitivity": "high",
    "enabled": True,
    "rules": {"enterZone": True, "stayTooLong": False, "stayDurationSeconds": 5, "approachZone": False},
}

TRACK_OUTSIDE = {"track_id": 7, "class": "child", "class_name": "child", "confirmed": True, "confidence": 0.6, "box": [0.05, 0.5, 0.15, 0.6]}
TRACK_INSIDE = {"track_id": 7, "class": "child", "class_name": "child", "confirmed": True, "confidence": 0.6, "box": [0.4, 0.3, 0.6, 0.6]}
TRACK_INSIDE_UNCONFIRMED = {"track_id": 8, "class": "child", "class_name": "child", "confirmed": False, "confidence": 0.6, "box": [0.4, 0.3, 0.6, 0.6]}
TRACK_INSIDE_LOW_CONF = {"track_id": 9, "class": "child", "class_name": "child", "confirmed": True, "confidence": 0.02, "box": [0.4, 0.3, 0.6, 0.6]}


def _engine(sensitivity="high", rules=None, **kwargs) -> RoiStateEngine:
    """Zone dùng sensitivity để quyết định confirm_in/out (high=2, low=5...)."""
    zone = dict(ZONE)
    zone["sensitivity"] = sensitivity
    if rules is not None:
        zone["rules"] = rules
    engine = RoiStateEngine(camera_id=CAMERA, **kwargs)
    engine.set_zones([zone])
    return engine


def test_enter_zone_fires_once_at_transition():
    """sensitivity high → confirm_in=2. Fire đúng một lần tại transition,
    không fire lại khi vẫn ở trong dù hết cooldown."""
    engine = _engine(cooldown_seconds=30)
    now = 1_000_000.0

    # Frame 1: ngoài — chưa có gì
    assert engine.update([TRACK_OUTSIDE], now_ms=now) == []
    # Frame 2: vào — cần 2 frame confirm
    now += 100
    assert engine.update([TRACK_INSIDE], now_ms=now) == []
    # Frame 3: vẫn trong — fire lần đầu
    now += 100
    alerts = engine.update([TRACK_INSIDE], now_ms=now)
    assert len(alerts) == 1
    assert alerts[0].rule == "enterZone"
    assert alerts[0].zone_id == "1"
    assert alerts[0].track_id == 7

    # Ở nguyên trong zone vượt cooldown → KHÔNG fire lại (transition-only)
    now += 100_000
    assert engine.update([TRACK_INSIDE], now_ms=now) == []

    # Rời vùng rồi quay lại → transition mới → fire lần nữa
    now += 100
    engine.update([TRACK_OUTSIDE], now_ms=now)
    for _ in range(6):  # confirm_out=5 (high)
        now += 100
        engine.update([TRACK_OUTSIDE], now_ms=now)
    now += 100
    assert engine.update([TRACK_INSIDE], now_ms=now) == []
    now += 100
    alerts2 = engine.update([TRACK_INSIDE], now_ms=now)
    assert len(alerts2) == 1
    assert alerts2[0].rule == "enterZone"


def test_unconfirmed_tracks_never_trigger_rules():
    """Provisional (confirmed=False) không bao giờ gây alert."""
    engine = _engine()
    now = 1_000_000.0
    for _ in range(5):
        now += 100
        assert engine.update([TRACK_INSIDE_UNCONFIRMED], now_ms=now) == []


def test_hysteresis_prevents_flicker():
    """Vào-rồi-ra ngay trong cửa sổ confirm không fire alert."""
    engine = _engine()  # high: confirm_in=2
    now = 1_000_000.0

    assert engine.update([TRACK_OUTSIDE], now_ms=now) == []
    now += 100
    assert engine.update([TRACK_INSIDE], now_ms=now) == []
    now += 100
    assert engine.update([TRACK_OUTSIDE], now_ms=now) == []  # ra trước khi confirm đủ
    now += 100
    assert engine.update([TRACK_INSIDE], now_ms=now) == []  # quay lại — đếm lại từ đầu
    # Chưa từng fire alert nào
    assert engine._last_fire == {}


def test_roi_significant_box_overlap_triggers_when_feet_are_outside():
    """Vùng vẽ trên thân trẻ vẫn báo nếu box giao đáng kể với ROI."""
    engine = _engine()  # zone y=[0.2, 0.8], high confirm_in=2
    now = 1_000_000.0
    center_inside_feet_outside = {
        **TRACK_INSIDE,
        "box": [0.4, 0.4, 0.6, 0.95],  # center y=.675 inside; footpoint y≈.934 outside
    }
    center_inside_feet_outside.pop("zone_breach", None)
    center_inside_feet_outside.pop("zone_id", None)
    center_inside_feet_outside.pop("zone_name", None)

    alerts = []
    for _ in range(2):
        now += 100
        alerts += engine.update([center_inside_feet_outside], now_ms=now)
    assert [alert.rule for alert in alerts] == ["enterZone"]
    assert center_inside_feet_outside.get("zone_breach") is True


def test_roi_tiny_box_edge_graze_does_not_trigger():
    """Box chỉ sượt một phần rất nhỏ của ROI không được báo nhầm."""
    engine = _engine()
    track = {
        **TRACK_OUTSIDE,
        "box": [0.05, 0.1, 0.205, 0.3],
    }
    now = 1_000_000.0
    for _ in range(3):
        now += 100
        assert engine.update([track], now_ms=now) == []
    assert track.get("zone_breach") is not True


def test_roi_footpoint_enters_floor_zone_before_box_center():
    """Điểm chân vào vùng sàn phải báo dù tâm cơ thể vẫn còn ở ngoài."""
    floor_zone = {
        **ZONE,
        "points": [
            {"x": 0.2, "y": 0.55},
            {"x": 0.8, "y": 0.55},
            {"x": 0.8, "y": 0.8},
            {"x": 0.2, "y": 0.8},
        ],
    }
    engine = RoiStateEngine(camera_id=CAMERA)
    engine.set_zones([floor_zone])
    now = 1_000_000.0
    feet_inside_center_outside = {
        **TRACK_INSIDE,
        "box": [0.4, 0.0, 0.6, 0.7],  # center y=.35 outside; footpoint y=.679 inside
    }
    feet_inside_center_outside.pop("zone_breach", None)
    feet_inside_center_outside.pop("zone_id", None)
    feet_inside_center_outside.pop("zone_name", None)

    fired = []
    for _ in range(2):
        now += 100
        fired += engine.update([feet_inside_center_outside], now_ms=now)

    assert [alert.rule for alert in fired] == ["enterZone"]
    assert feet_inside_center_outside.get("zone_breach") is True


def test_stay_too_long_fires_once_and_resets_on_leave():
    rules = {"enterZone": True, "stayTooLong": True, "stayDurationSeconds": 5, "approachZone": False}
    engine = _engine(rules=rules)  # high: confirm_in=2
    now = 1_000_000.0

    alerts = []
    for i in range(61):
        now += 100  # 100ms/step
        alerts += engine.update([TRACK_INSIDE], now_ms=now)

    rules_fired = [a.rule for a in alerts]
    assert "enterZone" in rules_fired
    assert "stayTooLong" in rules_fired
    assert rules_fired.count("stayTooLong") == 1

    # Rời vùng → reset; sau cooldown (30s) quay lại ở đủ lâu → fire lần nữa
    for _ in range(6):
        now += 100
        engine.update([TRACK_OUTSIDE], now_ms=now)
    now += 40_000  # vượt cooldown (cooldown key: camera, zone, track, rule)
    alerts2 = []
    for i in range(61):
        now += 100
        alerts2 += engine.update([TRACK_INSIDE], now_ms=now)
    assert "stayTooLong" in [a.rule for a in alerts2]


def test_approach_zone_requires_min_decreasing_delta():
    rules = {"enterZone": False, "stayTooLong": False, "stayDurationSeconds": 5, "approachZone": True}
    engine = _engine(rules=rules, approach_frames=4)
    now = 1_000_000.0

    # Tiến dần từ xa về gần biên (biên trái x=0.2): x2 tăng dần về 0.19
    fired = []
    for x2 in (0.02, 0.08, 0.12, 0.16, 0.19):
        now += 100
        track = {"track_id": 9, "class": "child", "class_name": "child", "confirmed": True, "confidence": 0.6, "box": [0.0, 0.4, x2, 0.7]}
        fired += engine.update([track], now_ms=now)

    assert any(a.rule == "approachZone" for a in fired)


def test_approach_flat_sequence_does_not_fire():
    """Chuỗi phẳng (delta < APPROACH_MIN_DELTA) không fire."""
    rules = {"enterZone": False, "stayTooLong": False, "stayDurationSeconds": 5, "approachZone": True}
    engine = _engine(rules=rules, approach_frames=4)
    now = 1_000_000.0

    fired = []
    for _ in range(6):
        now += 100
        track = {"track_id": 10, "class": "child", "class_name": "child", "confirmed": True, "confidence": 0.6, "box": [0.0, 0.4, 0.18, 0.7]}
        fired += engine.update([track], now_ms=now)  # x2 cố định — phẳng

    assert fired == []


def test_low_confidence_respects_sensitivity():
    """Sensitivity high: conf_min=0.15 → track conf 0.02 không bao giờ fire."""
    engine = _engine()
    now = 1_000_000.0
    assert engine.update([TRACK_INSIDE_LOW_CONF], now_ms=now) == []


def test_pause_suppresses_and_resume_no_replay():
    """Pause chặn alert; resume chỉ xét transition mới, không phát bù sự kiện cũ."""
    engine = _engine()
    engine.set_paused(True)
    now = 1_000_000.0
    for _ in range(3):
        now += 100
        assert engine.update([TRACK_INSIDE], now_ms=now) == []
    assert engine.is_paused

    engine.set_paused(False)
    # Vẫn ở trong — KHÔNG có transition mới → không fire bù
    for _ in range(3):
        now += 100
        assert engine.update([TRACK_INSIDE], now_ms=now) == []

    # Ra rồi vào lại → transition mới → fire
    for _ in range(6):
        now += 100
        engine.update([TRACK_OUTSIDE], now_ms=now)
    now += 100
    engine.update([TRACK_INSIDE], now_ms=now)
    now += 100
    assert len(engine.update([TRACK_INSIDE], now_ms=now)) == 1


def test_cooldown_per_track_and_zone():
    """Hai track khác nhau vào cùng zone → mỗi track 1 alert."""
    engine = _engine(cooldown_seconds=30)
    now = 1_000_000.0

    fired = []
    for _ in range(2):
        now += 100
        fired += engine.update([TRACK_INSIDE], now_ms=now)
    assert len(fired) == 1

    track2 = {**TRACK_INSIDE, "track_id": 99}
    fired2 = []
    for _ in range(2):
        now += 100
        fired2 += engine.update([track2], now_ms=now)
    assert len(fired2) == 1
    assert fired2[0].track_id == 99


def test_cooldown_first_fire_at_zero_clock():
    """Hồi quy: clock bắt đầu từ 0 (source_time_ms) — lần fire đầu không bị chặn;
    sentinel None, không dùng 0."""
    engine = _engine(cooldown_seconds=30)
    now = 0.0
    fired = []
    for _ in range(2):
        now += 100
        fired += engine.update([TRACK_INSIDE], now_ms=now)
    assert len(fired) == 1

    for _ in range(2):
        now += 100
        fired += engine.update([TRACK_INSIDE], now_ms=now)
    assert len(fired) == 1


def test_track_prune_after_ttl():
    """Track biến mất → state bị prune sau TRACK_STATE_TTL_MS."""
    engine = _engine()
    now = 1_000_000.0
    engine.update([TRACK_INSIDE], now_ms=now)
    assert len(engine._track_state) == 1

    # Không còn track nào — nhưng update() cần được gọi để prune
    engine.update([], now_ms=now + 3000.0)
    assert len(engine._track_state) == 0


def test_zone_config_change_resets_state():
    """Đổi geometry/rules/sensitivity của zone → reset state zone đó."""
    engine = _engine()
    now = 1_000_000.0
    engine.update([TRACK_INSIDE], now_ms=now)
    assert len(engine._track_state) == 1

    zone2 = dict(ZONE)
    zone2["rules"] = {"enterZone": False, "stayTooLong": False, "stayDurationSeconds": 5, "approachZone": True}
    engine.set_zones([zone2])
    assert len(engine._track_state) == 0
    assert len(engine._last_fire) == 0


def test_breach_marker_on_tracks():
    engine = _engine()
    now = 1_000_000.0
    track = {**TRACK_INSIDE}
    engine.update([track], now_ms=now)
    # Marker breach chỉ xuất hiện sau khi track thực sự inside (sau confirm_in)
    for _ in range(3):
        now += 100
        engine.update([track], now_ms=now)
    assert track.get("zone_breach") is True
    assert track.get("zone_name") == "Khu vực nguy hiểm"


def test_disabled_zone_ignored():
    zone = dict(ZONE)
    zone["enabled"] = False
    engine = RoiStateEngine(camera_id=CAMERA)
    engine.set_zones([zone])
    now = 1_000_000.0
    assert engine.update([TRACK_INSIDE], now_ms=now) == []


def test_zone_removal_cleans_state():
    engine = _engine()
    now = 1_000_000.0
    engine.update([TRACK_INSIDE], now_ms=now)
    engine.set_zones([])
    assert engine.zone_count == 0
    assert all(v.zone_id != "1" for v in engine._track_state.values())
