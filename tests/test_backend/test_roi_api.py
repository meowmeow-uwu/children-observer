"""
Tests cho REST API: ROI CRUD (replace-whole-list), rules persisted, pause alerts.
"""

import base64
import os
import sys
from pathlib import Path

# Dùng sqlite tạm trước khi import app (database.config đọc env lúc import)
TEST_DB = Path(__file__).parent / "test_roi_api.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
TEST_SNAPSHOTS = Path(__file__).parent / "test_snapshots"
os.environ["ALERT_SNAPSHOT_DIR"] = str(TEST_SNAPSHOTS)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from module_backend_infra.main import app, init_seed_data  # noqa: E402

client = TestClient(app)

CAMERA = "camera_living_room_01"


def _zone(name="Khu vực ổ điện", rules=None):
    return {
        "name": name,
        "type": "rectangle",
        "points": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.4, "y": 0.1},
            {"x": 0.4, "y": 0.5},
            {"x": 0.1, "y": 0.5},
        ],
        "sensitivity": "high",
        "enabled": True,
        "rules": rules
        or {
            "enterZone": True,
            "stayTooLong": False,
            "stayDurationSeconds": 5,
            "approachZone": False,
        },
    }


def test_get_cameras_returns_zones_with_rules():
    res = client.get("/api/cameras")
    assert res.status_code == 200
    cams = res.json()
    assert any(c["camera_id_string"] == CAMERA for c in cams)
    cam = next(c for c in cams if c["camera_id_string"] == CAMERA)
    assert "alerts_paused" in cam
    assert len(cam["roi_zones"]) >= 1
    assert cam["roi_zones"][0]["rules"]["enterZone"] is True


def test_save_roi_replaces_whole_list_and_persists_rules():
    res = client.post(
        f"/api/cameras/{CAMERA}/roi",
        json=[
            _zone("Vùng 1"),
            _zone(
                "Vùng 2",
                rules={
                    "enterZone": False,
                    "stayTooLong": True,
                    "stayDurationSeconds": 12,
                    "approachZone": True,
                },
            ),
        ],
    )
    assert res.status_code == 200
    zones = res.json()
    assert len(zones) == 2
    ids = {z["name"]: z for z in zones}
    assert ids["Vùng 2"]["rules"]["stayTooLong"] is True
    assert ids["Vùng 2"]["rules"]["stayDurationSeconds"] == 12
    assert ids["Vùng 2"]["rules"]["approachZone"] is True
    assert ids["Vùng 2"]["type"] == "rectangle"

    # Replace lại chỉ 1 zone → 2 zone cũ phải biến mất
    res2 = client.post(f"/api/cameras/{CAMERA}/roi", json=[_zone("Chỉ còn vùng này")])
    assert len(res2.json()) == 1
    assert res2.json()[0]["name"] == "Chỉ còn vùng này"


def test_save_roi_unknown_camera_404():
    res = client.post("/api/cameras/nonexistent_99/roi", json=[_zone()])
    assert res.status_code == 404


def test_get_camera_roi_roundtrip_rules():
    client.post(f"/api/cameras/{CAMERA}/roi", json=[_zone("Roundtrip")])
    res = client.get(f"/api/cameras/{CAMERA}/roi")
    assert res.status_code == 200
    zone = res.json()[0]
    assert zone["rules"]["enterZone"] is True
    assert zone["name"] == "Roundtrip"
    assert len(zone["points"]) == 4


def test_saved_roi_survives_backend_reinitialization():
    """ROI người dùng lưu không bị seed startup ghi đè ở lần chạy sau."""
    payload = _zone("ROI mới nhất của người dùng")
    payload["points"] = [
        {"x": 0.31, "y": 0.41},
        {"x": 0.67, "y": 0.41},
        {"x": 0.67, "y": 0.88},
        {"x": 0.31, "y": 0.88},
    ]
    saved = client.post(f"/api/cameras/{CAMERA}/roi", json=[payload])
    assert saved.status_code == 200

    # Mô phỏng backend startup lại: seed chỉ được phép chạy khi DB thật sự rỗng.
    init_seed_data()

    loaded = client.get(f"/api/cameras/{CAMERA}/roi")
    assert loaded.status_code == 200
    assert loaded.json()[0]["name"] == "ROI mới nhất của người dùng"
    assert loaded.json()[0]["points"] == payload["points"]


def test_alerts_pause_toggle():
    res = client.post(f"/api/cameras/{CAMERA}/alerts-paused", json={"paused": True})
    assert res.status_code == 200
    assert res.json()["alerts_paused"] is True

    res = client.get(f"/api/cameras/{CAMERA}")
    assert res.json()["alerts_paused"] is True

    res = client.post(f"/api/cameras/{CAMERA}/alerts-paused", json={"paused": False})
    assert res.json()["alerts_paused"] is False


def test_roi_validation_rejects_invalid_payloads():
    """T05: type/sensitivity/name/points được validate; polygon >=3, rectangle ==4."""
    CAMERA = "camera_living_room_01"

    # type sai
    bad_type = _zone("Sai type")
    bad_type["type"] = "circle"
    res = client.post(f"/api/cameras/{CAMERA}/roi", json=[bad_type])
    assert res.status_code == 422

    # sensitivity sai
    bad_sens = _zone("Sai sensitivity")
    bad_sens["sensitivity"] = "extreme"
    res = client.post(f"/api/cameras/{CAMERA}/roi", json=[bad_sens])
    assert res.status_code == 422

    # name rỗng
    bad_name = _zone("   ")
    res = client.post(f"/api/cameras/{CAMERA}/roi", json=[bad_name])
    assert res.status_code == 422

    # tọa độ ngoài [0,1]
    bad_pt = _zone("Điểm ngoài biên")
    bad_pt["points"] = [{"x": 1.5, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.5}, {"x": 0.1, "y": 0.5}]
    res = client.post(f"/api/cameras/{CAMERA}/roi", json=[bad_pt])
    assert res.status_code == 422

    # polygon chỉ 2 điểm
    bad_poly = _zone("Polygon thiếu điểm")
    bad_poly["type"] = "polygon"
    bad_poly["points"] = [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}]
    res = client.post(f"/api/cameras/{CAMERA}/roi", json=[bad_poly])
    assert res.status_code == 422

    # rectangle không đủ 4 điểm
    bad_rect = _zone("Rectangle thiếu góc")
    bad_rect["points"] = [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.5}]
    res = client.post(f"/api/cameras/{CAMERA}/roi", json=[bad_rect])
    assert res.status_code == 422


def test_alerts_crud():
    res = client.post(
        "/api/alerts",
        json={
            "camera_id": CAMERA,
            "camera_name": "Phòng khách",
            "title": "Trẻ vào vùng nguy hiểm",
            "severity": "danger",
            "roi_name": "Vùng 1",
            "snapshot_base64": base64.b64encode(b"\xff\xd8real-frame-jpeg").decode("ascii"),
        },
    )
    assert res.status_code == 200
    alert_id = res.json()["id"]
    snapshot_url = res.json()["snapshot_url"]
    assert snapshot_url.startswith("/snapshots/alert-")
    assert client.get(snapshot_url).content == b"\xff\xd8real-frame-jpeg"

    res = client.patch(f"/api/alerts/{alert_id}", json={"status": "resolved"})
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"

    res = client.get(f"/api/alerts?camera_id={CAMERA}")
    assert any(a["id"] == alert_id for a in res.json())

    res = client.delete("/api/alerts")
    assert res.status_code == 200
    assert res.json()["deleted"] >= 1
    assert res.json()["deleted_snapshots"] >= 1
    assert client.get("/api/alerts").json() == []
    assert client.get(snapshot_url).status_code == 404


def teardown_module():
    client.close()
    if TEST_DB.exists():
        try:
            TEST_DB.unlink()
        except PermissionError:
            pass
    if TEST_SNAPSHOTS.exists():
        for path in TEST_SNAPSHOTS.iterdir():
            path.unlink(missing_ok=True)
        TEST_SNAPSHOTS.rmdir()
