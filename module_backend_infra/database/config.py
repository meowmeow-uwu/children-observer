import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Lấy URL kết nối từ biến môi trường (sẽ được truyền vào qua Docker)
# Mặc định dùng sqlite nếu chạy local không có Docker để tránh lỗi tạm thời
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./test_local.db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency để sử dụng trong các API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()