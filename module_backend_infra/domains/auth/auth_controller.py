# domains/auth/auth_controller.py
from urllib.parse import parse_qs
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
async def login(request: Request, db: Session = Depends(get_db)):
    """Đăng nhập và nhận JWT Token (hỗ trợ cả JSON Body và Form Data của Swagger Authorize)."""
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    try:
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            raw_body = (await request.body()).decode("utf-8")
            parsed = parse_qs(raw_body)
            email_list = parsed.get("username") or parsed.get("email")
            password_list = parsed.get("password")
            if email_list:
                email = email_list[0]
            if password_list:
                password = password_list[0]
        else:
            body = await request.json()
            if isinstance(body, dict):
                email = body.get("email") or body.get("username")
                password = body.get("password")
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dữ liệu gửi lên không hợp lệ: {str(err)}"
        )

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email/username và password là bắt buộc."
        )

    try:
        user_in = auth_schemas.UserLogin(email=str(email), password=str(password))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Định dạng email không hợp lệ."
        )

    return AuthService.authenticate(db, user_in)

@router.get("/me", response_model=auth_schemas.UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Lấy thông tin của user đang đăng nhập.
    Bắt buộc phải truyền Token vào header (Authorization: Bearer <token>).
    """
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