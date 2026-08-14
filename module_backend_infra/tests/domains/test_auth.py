# tests/domains/test_auth.py
def test_register_user_success(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "testparent@gmail.com", "password": "strongpassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testparent@gmail.com"
    assert "password" not in data  # Tuyệt đối không được trả về password

def test_register_duplicate_email(client):
    # Đăng ký lần 1 (Đã làm ở test trên, nhưng ta chạy lại độc lập)
    client.post("/api/auth/register", json={"email": "duplicate@gmail.com", "password": "123"})
    # Đăng ký lần 2
    response = client.post("/api/auth/register", json={"email": "duplicate@gmail.com", "password": "456"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email này đã được đăng ký."

def test_login_success(client):
    # Tạo user trước
    client.post("/api/auth/register", json={"email": "login@gmail.com", "password": "mypassword"})
    
    # Test đăng nhập
    response = client.post(
        "/api/auth/login",
        json={"email": "login@gmail.com", "password": "mypassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "wrong@gmail.com", "password": "rightpassword"})
    response = client.post(
        "/api/auth/login",
        json={"email": "wrong@gmail.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_get_me_success(client, auth_headers):
    """Test API trả về đúng profile khi có token hợp lệ."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "parent_test@gmail.com" # Trùng với dữ liệu ở conftest.py
    assert "id" in data

def test_get_me_invalid_token(client):
    """Test bắt lỗi khi truyền token rác."""
    headers = {"Authorization": "Bearer token_nhap_linh_tinh_khong_hop_le"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "không thể xác thực" in response.json()["detail"].lower()

def test_update_profile_telegram_id_success(client, auth_headers):
    """Test cập nhật Telegram Chat ID thành công."""
    payload = {"telegram_chat_id": 987654321}
    response = client.patch("/api/auth/me", headers=auth_headers, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_chat_id"] == 987654321

def test_update_profile_telegram_id_duplicate(client, auth_headers, db_session):
    """Test chặn cập nhật khi Telegram Chat ID đã bị tài khoản khác chiếm dụng."""
    # 1. Tạo một User "hàng xóm" (User B) và gán sẵn Chat ID
    from domains.auth.auth_models import User
    from core.security import hash_password
    
    user_b = User(
        email="neighbor@gmail.com", 
        password_hash=hash_password("123"), 
        telegram_chat_id=55555
    )
    db_session.add(user_b)
    db_session.commit()
    
    # 2. Dùng Token của User A (từ auth_headers) cố tình cập nhật trùng Chat ID của User B
    payload = {"telegram_chat_id": 55555}
    response = client.patch("/api/auth/me", headers=auth_headers, json=payload)
    
    # 3. Hệ thống phải báo lỗi 400
    assert response.status_code == 400
    assert "đã được liên kết" in response.json()["detail"].lower()