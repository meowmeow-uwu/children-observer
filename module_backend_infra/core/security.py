# core/security.py
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt  # Sử dụng trực tiếp bcrypt thay vì passlib
from core.config import settings

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng bcrypt."""
    # Bcrypt yêu cầu đầu vào là kiểu bytes (encode utf-8)
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')  # Giải mã về string để lưu vào DB

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu nhập vào với mã băm trong DB."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except ValueError:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT Access Token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.AUTH_JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt