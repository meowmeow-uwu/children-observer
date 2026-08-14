# core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings  # Import settings vừa tạo

# Lấy URL từ pydantic settings
DATABASE_URL = settings.DATABASE_URL

# Khởi tạo engine với pool connection tối ưu
engine = create_engine(
    DATABASE_URL, 
    pool_size=5, 
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()