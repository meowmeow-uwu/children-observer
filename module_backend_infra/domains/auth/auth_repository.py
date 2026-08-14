# domains/auth/auth_repository.py
from sqlalchemy.orm import Session
from core.repository import CRUDBase
from .auth_models import User
from .auth_schemas import UserCreate

class UserRepository(CRUDBase[User, UserCreate, UserCreate]):
    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(self.model).filter(self.model.email == email).first()

# Khởi tạo instance duy nhất để dùng trong Service
user_repo = UserRepository(User)