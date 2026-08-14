# domains/auth/auth_schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# Schema dùng để kiểm tra dữ liệu người dùng gửi lên khi Đăng ký
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Schema dùng để kiểm tra dữ liệu khi Đăng nhập
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema dữ liệu trả về cho Frontend (tuyệt đối không trả về password_hash)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    telegram_chat_id: Optional[int] = None

    class Config:
        from_attributes = True

# Schema trả về Token
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class UserUpdate(BaseModel):
    telegram_chat_id: Optional[int] = None