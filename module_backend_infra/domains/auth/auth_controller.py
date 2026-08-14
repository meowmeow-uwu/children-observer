# domains/auth/auth_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from . import auth_schemas
from .auth_service import AuthService

from .dependencies import get_current_user
from .auth_models import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=auth_schemas.UserResponse)
def register(user_in: auth_schemas.UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản phụ huynh mới."""
    return AuthService.register_user(db, user_in)

@router.post("/login", response_model=auth_schemas.TokenResponse)
def login(user_in: auth_schemas.UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập và nhận JWT Token."""
    return AuthService.authenticate(db, user_in)

@router.get("/me", response_model=auth_schemas.UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Lấy thông tin của user đang đăng nhập.
    Bắt buộc phải truyền Token vào header (Authorization: Bearer <token>).
    """
    # Vì get_current_user đã làm hết việc kiểm tra và tìm DB, 
    # ở đây bạn chỉ việc trả về current_user.
    return current_user

@router.patch("/me", response_model=auth_schemas.UserResponse)
def update_my_profile(
    user_in: auth_schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật thông tin cá nhân (VD: telegram_chat_id để nhận cảnh báo).
    """
    return AuthService.update_profile(db, current_user, user_in)