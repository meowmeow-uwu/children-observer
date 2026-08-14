import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import ValidationError

from core.config import settings
from core.database import get_db
from domains.auth.auth_models import User
from domains.auth.auth_repository import user_repo
from domains.auth.auth_schemas import TokenPayload

# Khai báo đường dẫn API mà Frontend sẽ dùng để lấy Token (dùng cho Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency kiểm tra JWT Token. 
    Nếu hợp lệ: Trả về object User.
    Nếu không: Bắn lỗi 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập (Token không hợp lệ hoặc đã hết hạn).",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Giải mã Token bằng Secret Key
        payload = jwt.decode(
            token, 
            settings.AUTH_JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        # 2. Bóc tách dữ liệu vào Schema
        token_data = TokenPayload(**payload)
        
        if token_data.sub is None:
            raise credentials_exception
            
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception
        
    # 3. Truy vấn User từ Database
    user = user_repo.get(db, id=int(token_data.sub))
    if not user:
        raise credentials_exception
        
    return user