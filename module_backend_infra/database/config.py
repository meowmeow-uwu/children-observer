import os

from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Lấy URL kết nối từ biến môi trường (sẽ được truyền vào qua Docker)
# Mặc định dùng sqlite nếu chạy local không có Docker để tránh lỗi tạm thời
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_local.db")

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


def upgrade_schema() -> None:
    """Thêm các cột mới vào bảng đã tồn tại (migration nhẹ cho demo).

    create_all() chỉ tạo bảng mới, không ALTER bảng cũ. Hàm này kiểm tra
    và bổ sung các cột được giới thiệu sau schema ban đầu.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    # (table, column, DDL type)
    additions = [
        ("cameras", "alerts_paused", "BOOLEAN NOT NULL DEFAULT 0"),
        ("roi_zones", "type", "VARCHAR NOT NULL DEFAULT 'polygon'"),
        ("roi_zones", "rules", "TEXT NOT NULL DEFAULT '{}'"),
    ]

    with engine.begin() as conn:
        for table, column, ddl_type in additions:
            if table not in tables:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            try:
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl_type}'))
                logger.info(f"Schema upgrade: added {table}.{column}")
            except Exception as exc:  # noqa: BLE001 - best-effort migration
                logger.warning(f"Schema upgrade skipped {table}.{column}: {exc}")
