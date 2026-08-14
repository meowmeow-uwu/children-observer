# domains/auth/auth_repository.py
from sqlalchemy.orm import Session
from core.repository import CRUDBase
from .auth_models import User
from .auth_schemas import UserCreate

class UserRepository(CRUDBase[User, UserCreate, UserCreate]):
    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(self.model).filter(self.model.email == email).first()

    def create_user(self, db: Session, email: str, password_hash: str) -> User:
        db_user = User(email=email, password_hash=password_hash)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def is_telegram_id_taken(self, db: Session, telegram_chat_id: int, exclude_user_id: int) -> bool:
        return db.query(self.model).filter(
            self.model.telegram_chat_id == telegram_chat_id,
            self.model.id != exclude_user_id
        ).first() is not None

# Khởi tạo instance duy nhất để dùng trong Service
user_repo = UserRepository(User)