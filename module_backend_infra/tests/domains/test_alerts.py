# tests/domains/test_alerts.py
from unittest.mock import patch
from datetime import datetime, timedelta

@patch("domains.alerts.alert_service.send_telegram_alert")
@patch("domains.alerts.alert_service.manager.broadcast")
def test_create_alert_triggers_webhook_and_ws(mock_broadcast, mock_telegram, client, db_session):
    # 1. Tạo Dummy Device & Camera trong DB in-memory để thỏa mãn Khóa ngoại (Foreign Key)
    from domains.devices.device_models import Device
    from domains.cameras.camera_models import Camera
    from domains.auth.auth_models import User
    
    
    user = User(email="alertuser@gmail.com", password_hash="hash", telegram_chat_id=123456789)
    db_session.add(user)
    db_session.commit()
    
    device = Device(user_id=user.id, mac_address="MAC123", device_secret_key="key")
    db_session.add(device)
    db_session.commit()
    
    cam = Camera(device_id=device.id, camera_id_string="cam_alert_01", name="Cam1", rtsp_url="rtsp://..")
    db_session.add(cam)
    db_session.commit()
    
    # 2. SỬA DÒNG NÀY: Payload gửi lên phải dùng camera_id_string để khớp với luồng xử lý
    alert_payload = {
        "camera_id": "cam_alert_01", 
        "title": "Trẻ ngã cầu thang",
        "severity": "danger",
        "snapshot_url": "snapshot_123.jpg",
        "roi_name": "Cầu thang"
    }
    
    # Vì hàm route create_alert sử dụng async, TestClient của FastAPI vẫn xử lý được
    response = client.post("/api/alerts/", json=alert_payload)
    
    # 3. Assertions
    assert response.status_code == 200
    assert response.json()["title"] == "Trẻ ngã cầu thang"
    
    # Kiểm tra xem WebSocket Broadcast có được gọi đúng 1 lần không
    assert mock_broadcast.called
    assert mock_broadcast.call_count == 1
    
    # Kiểm tra xem Telegram API có được kích hoạt gửi ngầm không
    assert mock_telegram.called

def test_create_alert_camera_not_found(client):
    """Test bắt lỗi 404 khi gửi Cảnh báo với Camera ID không tồn tại."""
    alert_payload = {
        "camera_id": "camera_fake_99999", # ID này không có trong DB
        "title": "Cảnh báo giả mạo",
        "severity": "warning"
    }
    
    response = client.post("/api/alerts/", json=alert_payload)
    
    assert response.status_code == 404
    assert "Không tìm thấy Camera" in response.json()["detail"]

def test_get_alerts_with_filters(client, auth_headers, db_session):
    from domains.devices.device_models import Device
    from domains.cameras.camera_models import Camera
    from domains.alerts.alert_models import Alert
    
    device = Device(user_id=1, mac_address="MAC_FILTER_TEST", device_secret_key="key")
    db_session.add(device)
    db_session.commit()
    
    cam = Camera(device_id=device.id, camera_id_string="cam_alert_filter_01", name="Cam Filter", rtsp_url="rtsp://..")
    db_session.add(cam)
    db_session.commit()
    
    # 1. Tạo 2 cảnh báo có thời gian khác nhau cho cam_alert_filter_01
    alert1 = Alert(
        camera_id=cam.id,
        title="Old Alert",
        created_at=datetime.now() - timedelta(days=1)
    )
    alert2 = Alert(
        camera_id=cam.id,
        title="New Alert",
        created_at=datetime.now()
    )
    db_session.add_all([alert1, alert2])
    db_session.commit()
    
    # 2. Lấy cảnh báo chỉ trong vòng 1 tiếng trở lại
    start_date = (datetime.now() - timedelta(hours=1)).isoformat()
    response = client.get(
        f"/api/alerts/?camera_id=cam_alert_filter_01&start_date={start_date}", 
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    titles = [a["title"] for a in data]
    assert "New Alert" in titles
    assert "Old Alert" not in titles