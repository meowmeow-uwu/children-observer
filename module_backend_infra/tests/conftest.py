# tests/conftest.py
import sys
from pathlib import Path

# Thêm cả root dự án và module_backend_infra vào sys.path để hỗ trợ chạy pytest từ bất kỳ thư mục nào
root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = Path(__file__).resolve().parent.parent
for path_str in [str(root_dir), str(backend_dir)]:
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from module_backend_infra.domain_app import app

# Sử dụng SQLite in-memory để test chạy nhanh và bị xóa ngay sau khi test xong
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_database():
    """Tạo bảng trước khi test và xóa bảng sau khi test xong."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Cung cấp session DB sạch cho mỗi test case."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    """Tạo TestClient và ghi đè dependency get_db của FastAPI."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(client, db_session):
    """Tạo hoặc lấy một user mặc định để dùng trong các test case cần xác thực."""
    from domains.auth.auth_models import User
    from core.security import hash_password
    
    # 1. Kiểm tra xem user này đã được tạo ở test case trước đó chưa
    user = db_session.query(User).filter(User.email == "parent_test@gmail.com").first()
    
    # 2. Nếu chưa có thì mới tạo mới
    if not user:
        user = User(
            email="parent_test@gmail.com", 
            password_hash=hash_password("securepassword")
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
    return user

@pytest.fixture
def auth_headers(client, test_user):
    """Tự động đăng nhập và trả về headers chứa Bearer Token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "parent_test@gmail.com", "password": "securepassword"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
