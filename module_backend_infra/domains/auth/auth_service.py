# domains/auth/auth_service.py
from domains.auth import auth_schemas
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from .auth_repository import user_repo
from .auth_schemas import UserCreate, UserLogin
from .auth_models import User
from core.security import hash_password, verify_password, create_access_token

class AuthService:
    
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        # 1. Kiểm tra email đã tồn tại chưa
        user = user_repo.get_by_email(db, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email này đã được đăng ký."
            )
        
        # 2. Băm mật khẩu
        hashed_pw = hash_password(user_in.password)
        
        # 3. Tạo User mới trong DB
        db_user = User(
            email=user_in.email,
            password_hash=hashed_pw
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate(db: Session, user_in: UserLogin) -> dict:
        # 1. Tìm user theo email
        user = user_repo.get_by_email(db, email=user_in.email)
        
        # 2. Xác thực mật khẩu
        if not user or not verify_password(user_in.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 3. Tạo JWT Access Token
        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    @staticmethod
    def update_profile(db: Session, current_user: User, update_in: auth_schemas.UserUpdate) -> User:
        """Cập nhật thông tin cá nhân của User"""
        if update_in.telegram_chat_id is not None:
            # Kiểm tra xem ID này có bị tài khoản khác chiếm dụng chưa
            existing_user = db.query(User).filter(
                User.telegram_chat_id == update_in.telegram_chat_id,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telegram Chat ID này đã được liên kết với một tài khoản khác."
                )
            
            current_user.telegram_chat_id = update_in.telegram_chat_id
            
        db.commit()
        db.refresh(current_user)
        return current_user