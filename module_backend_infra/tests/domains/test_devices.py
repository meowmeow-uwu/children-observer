# tests/domains/test_devices.py
import pytest

@pytest.fixture
def auth_headers(client):
    """Fixture tạo user và trả về headers chứa JWT Token."""
    client.post("/api/auth/register", json={"email": "deviceowner@gmail.com", "password": "123"})
    res = client.post("/api/auth/login", json={"email": "deviceowner@gmail.com", "password": "123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_register_device_unauthorized(client):
    # Cố tình gọi API mà không đính kèm Token
    response = client.post("/api/devices/", json={
        "mac_address": "B8:27:EB:00:00:01",
        "device_secret_key": "secret123"
    })
    assert response.status_code == 401

def test_register_device_success(client, auth_headers):
    response = client.post(
        "/api/devices/",
        headers=auth_headers,
        json={
            "mac_address": "B8:27:EB:00:00:01",
            "name": "Pi Phòng Khách",
            "device_secret_key": "secret123"
        }
    )
    assert response.status_code == 200
    assert response.json()["mac_address"] == "B8:27:EB:00:00:01"

def test_get_user_devices(client, auth_headers):
    """Test API lấy danh sách thiết bị của phụ huynh."""
    # 1. Tạo 1 thiết bị mẫu trước
    client.post(
        "/api/devices/",
        headers=auth_headers,
        json={"mac_address": "MAC_TEST_GET_API", "device_secret_key": "secret"}
    )
    
    # 2. Gọi API lấy danh sách
    response = client.get("/api/devices/", headers=auth_headers)
    
    # 3. Kiểm tra kết quả
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Đảm bảo thiết bị vừa tạo có trong danh sách
    mac_addresses = [device["mac_address"] for device in data]
    assert "MAC_TEST_GET_API" in mac_addresses

def test_share_device_success(client, auth_headers, db_session):
    """Test chia sẻ thiết bị thành công cho email hợp lệ."""
    # 1. Tạo 1 User để nhận chia sẻ (Guest)
    from domains.auth.auth_models import User
    from core.security import hash_password
    guest = User(email="guest_user@gmail.com", password_hash=hash_password("pw"))
    db_session.add(guest)
    db_session.commit()
    
    # 2. Tạo Thiết bị do User chính (từ auth_headers) sở hữu
    # test_user.id mặc định là 1 dựa theo conftest.py
    from domains.devices.device_models import Device
    dev = Device(user_id=1, mac_address="MAC_SHARE_TEST", device_secret_key="key")
    db_session.add(dev)
    db_session.commit()
    db_session.refresh(dev)
    
    # 3. Gọi API Chia sẻ
    payload = {"email": "guest_user@gmail.com", "role": "VIEWER"}
    response = client.post(f"/api/devices/{dev.id}/share", headers=auth_headers, json=payload)
    
    assert response.status_code == 200
    assert "thành công" in response.json()["detail"].lower()

def test_delete_device_success(client, auth_headers, db_session):
    """Test xóa thiết bị chính chủ."""
    # Tạo thiết bị
    from domains.devices.device_models import Device
    dev = Device(user_id=1, mac_address="MAC_DELETE_TEST", device_secret_key="key")
    db_session.add(dev)
    db_session.commit()
    db_session.refresh(dev)
    
    # Xóa thiết bị
    response = client.delete(f"/api/devices/{dev.id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Kiểm tra lại DB xem đã mất chưa
    deleted_dev = db_session.query(Device).filter(Device.id == dev.id).first()
    assert deleted_dev is None

def test_revoke_device_share_success(client, auth_headers, db_session):
    """Test hủy chia sẻ thiết bị cho phụ huynh được chỉ định."""
    from domains.auth.auth_models import User
    from domains.devices.device_models import Device, DeviceMember
    from core.security import hash_password

    # 1. Tạo guest user và thiết bị
    guest = User(email="shared_guest@gmail.com", password_hash=hash_password("pw"))
    db_session.add(guest)
    db_session.commit()

    dev = Device(user_id=1, mac_address="MAC_REVOKE_TEST", device_secret_key="key")
    db_session.add(dev)
    db_session.commit()

    # 2. Thêm member vào DeviceMember
    member = DeviceMember(device_id=dev.id, user_id=guest.id, role="VIEWER")
    db_session.add(member)
    db_session.commit()

    # 3. Gọi API hủy chia sẻ
    response = client.delete(f"/api/devices/{dev.id}/share/shared_guest@gmail.com", headers=auth_headers)
    assert response.status_code == 200
    assert "thu hồi" in response.json()["detail"].lower()

def test_share_device_not_owner(client, auth_headers, db_session):
    """Test lỗi khi user không sở hữu thiết bị cố chia sẻ."""
    from domains.devices.device_models import Device
    # Thiết bị sở hữu bởi user_id=999
    other_dev = Device(user_id=999, mac_address="MAC_OTHER_OWNER", device_secret_key="key")
    db_session.add(other_dev)
    db_session.commit()

    payload = {"email": "someone@gmail.com", "role": "VIEWER"}
    response = client.post(f"/api/devices/{other_dev.id}/share", headers=auth_headers, json=payload)
    assert response.status_code == 403