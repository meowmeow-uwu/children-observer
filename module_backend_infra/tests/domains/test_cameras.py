# tests/domains/test_cameras.py

def test_get_cameras_empty(client, auth_headers):
    """Test lấy danh sách camera khi chưa có camera nào."""
    response = client.get("/api/cameras/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

def test_create_camera_success(client, auth_headers, db_session):
    """Test thêm mới một camera hợp lệ."""
    # 1. Bắt buộc phải tạo Device trước để không bị lỗi Khóa ngoại (Foreign Key)
    from domains.devices.device_models import Device
    test_device = Device(user_id=1, mac_address="MAC_CAM_TEST", device_secret_key="secret")
    db_session.add(test_device)
    db_session.commit()

    # 2. Tạo Camera
    payload = {
        "camera_id_string": "cam_living_room_01",
        "device_id": 1,
        "name": "Camera Phòng Khách",
        "location": "Tầng 1",
        "status": "online",
        "is_active": True
    }
    
    response = client.post("/api/cameras/", headers=auth_headers, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["camera_id_string"] == "cam_living_room_01"
    assert data["name"] == "Camera Phòng Khách"
    assert data["roi_zones"] == [] # Camera mới chưa có ROI

def test_create_camera_duplicate_id(client, auth_headers, db_session):
    """Test bắt lỗi khi thêm 2 camera trùng ID."""
    from domains.devices.device_models import Device
    test_device = Device(user_id=1, mac_address="MAC_CAM_DUP_TEST", device_secret_key="secret")
    db_session.add(test_device)
    db_session.commit()

    payload = {
        "camera_id_string": "cam_duplicate",
        "device_id": test_device.id,
        "name": "Cam 1",
    }
    # Lần 1 thành công
    client.post("/api/cameras/", headers=auth_headers, json=payload)
    
    # Lần 2 phải báo lỗi 400
    response = client.post("/api/cameras/", headers=auth_headers, json=payload)
    assert response.status_code == 400
    assert "đã tồn tại" in response.json()["detail"].lower()

def test_save_camera_roi_success(client, auth_headers, db_session):
    """Test cấu hình mảng đa giác Vùng cấm (ROI) thành công."""
    from domains.devices.device_models import Device
    test_device = Device(user_id=1, mac_address="MAC_CAM_ROI_TEST", device_secret_key="secret")
    db_session.add(test_device)
    db_session.commit()

    # 1. Đảm bảo đã có Camera trong DB
    payload_cam = {"camera_id_string": "cam_roi_test", "device_id": test_device.id, "name": "Cam ROI"}
    client.post("/api/cameras/", headers=auth_headers, json=payload_cam)

    # 2. Gửi mảng tọa độ ROI
    roi_payload = [
        {
            "name": "Ban công",
            "sensitivity": "high",
            "enabled": True,
            "points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.5, "y": 0.1},
                {"x": 0.5, "y": 0.5},
                {"x": 0.1, "y": 0.5}
            ]
        }
    ]
    
    response = client.post(
        "/api/cameras/cam_roi_test/roi", 
        headers=auth_headers, 
        json=roi_payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Ban công"
    assert len(data[0]["points"]) == 4

def test_unauthorized_camera_access(client):
    """Test bảo mật: Không có token thì không được gọi API."""
    response = client.get("/api/cameras/")
    assert response.status_code == 401