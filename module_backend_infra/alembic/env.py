import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 1. Thêm thư mục gốc của project vào sys.path để Python có thể import các module
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# 2. Import config và Base dùng chung
from core.config import settings
from core.database import Base

# 3. IMPORT BẮT BUỘC: Nạp tất cả các Models vào bộ nhớ
# Alembic cần đọc qua các file này để gom metadata của các bảng
from domains.auth.auth_models import User
from domains.devices.device_models import Device, DeviceMember
from domains.cameras.camera_models import Camera, ROIZone
from domains.alerts.alert_models import Alert

# Cấu hình log của Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. Ghi đè URL kết nối database trong alembic.ini bằng biến DATABASE_URL từ tệp .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 5. Gán target_metadata để Alembic so sánh CSDL thực tế với Code
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()