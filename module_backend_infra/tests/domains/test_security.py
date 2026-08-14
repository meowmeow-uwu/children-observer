# tests/domains/test_security.py
import pytest
from domains.auth.auth_models import User
from domains.devices.device_models import Device
from domains.cameras.camera_models import Camera
from core.security import hash_password

@pytest.fixture
def setup_multi_users(db_session):
    """Fixture tạo sẵn 2 người dùng và thiết bị/camera tương ứng của họ."""
    # Tạo User A (Alice)
    user_a = User(email="alice@gmail.com", password_hash=hash_password("pw"))
    # Tạo User B (Bob)
    user_b = User(email="bob@gmail.com", password_hash=hash_password("pw"))
    
    db_session.add_all([user_a, user_b])
    db_session.commit()
    
    # Thiết bị và Camera của Alice
    dev_a = Device(user_id=user_a.id, mac_address="MAC_ALICE", device_secret_key="key")
    db_session.add(dev_a)
    db_session.commit()
    
    cam_a = Camera(
        device_id=dev_a.id, 
        camera_id_string="cam_alice_01", 
        name="Cam Alice", 
        rtsp_url="rtsp://"
    )
    db_session.add(cam_a)
    db_session.commit()
    
    # Thiết bị của Bob (Chưa có camera)
    dev_b = Device(user_id=user_b.id, mac_address="MAC_BOB", device_secret_key="key")
    db_session.add(dev_b)
    db_session.commit()
    
    return {"alice": user_a, "bob": user_b, "dev_alice": dev_a, "dev_bob": dev_b, "cam_alice": cam_a}

def test_data_isolation_get_cameras(client, setup_multi_users):
    """Alice chỉ được thấy Camera của Alice, Bob phải thấy danh sách rỗng."""
    data = setup_multi_users
    
    # 1. Lấy Token của Bob
    res_bob = client.post("/api/auth/login", json={"email": "bob@gmail.com", "password": "pw"})
    token_bob = res_bob.json()["access_token"]
    headers_bob = {"Authorization": f"Bearer {token_bob}"}
    
    # 2. Bob gọi API lấy danh sách Camera
    response = client.get("/api/cameras/", headers=headers_bob)
    
    # 3. Phải trả về danh sách rỗng (Không được thấy cam_alice_01)
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_security_prevent_cross_device_camera_creation(client, setup_multi_users):
    """Bob không được phép tạo Camera mới và gán khống vào Thiết bị của Alice."""
    data = setup_multi_users
    
    # Lấy Token của Bob
    res_bob = client.post("/api/auth/login", json={"email": "bob@gmail.com", "password": "pw"})
    headers_bob = {"Authorization": f"Bearer {res_bob.json()['access_token']}"}
    
    # Bob cố tình tạo Camera nhưng truyền device_id của Alice
    payload = {
        "camera_id_string": "cam_hacked_01",
        "device_id": data["dev_alice"].id, # Chọc vào thiết bị của Alice
        "name": "Hacked Camera",
        "rtsp_url": "rtsp://"
    }
    
    response = client.post("/api/cameras/", headers=headers_bob, json=payload)
    
    # API phải chặn lại với mã 403 Forbidden
    assert response.status_code == 403
    assert "không có quyền" in response.json()["detail"].lower()

def test_security_prevent_cross_camera_roi_update(client, setup_multi_users):
    """Bob không được phép sửa Vùng cấm (ROI) trên Camera của Alice."""
    data = setup_multi_users
    
    # Lấy Token của Bob
    res_bob = client.post("/api/auth/login", json={"email": "bob@gmail.com", "password": "pw"})
    headers_bob = {"Authorization": f"Bearer {res_bob.json()['access_token']}"}
    
    # Bob cố tình vẽ ROI lên cam_alice_01
    roi_payload = [{"name": "Ban công Bob vẽ bậy", "points": [{"x": 0.1, "y": 0.1}]}]
    
    response = client.post(
        f"/api/cameras/{data['cam_alice'].camera_id_string}/roi", 
        headers=headers_bob, 
        json=roi_payload
    )
    
    # API phải chặn lại với mã 403 Forbidden
    assert response.status_code == 403
    assert "không có quyền" in response.json()["detail"].lower()