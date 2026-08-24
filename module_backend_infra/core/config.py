# core/config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # ================= DATABASE =================
    # Chuỗi kết nối PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:yourpassword@localhost:5432/child_guardian_db"

    # ================= AUTHENTICATION =================
    AUTH_JWT_SECRET: str = "super-secret-key-change-it-in-production"  # Thay đổi trong file .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # Mặc định token sống 7 ngày

    # ================= SERVERS =================
    BACKEND_URL: str = "http://localhost:8007"
    FEDERATED_SERVER_URL: str = "http://localhost:8007/federated"

    # ================= MQTT BROKER =================
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None

    # ================= EXTERNAL INTEGRATIONS =================
    # Cấu hình Zalo OA Bot / Telegram
    ZALO_OA_TOKEN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ALERTS_ENABLED: bool = True

    # ================= WEBRTC / TURN SERVER =================
    TURN_SERVER_URL: Optional[str] = None
    TURN_SERVER_SECRET: Optional[str] = None

    # Cấu hình Pydantic để tự động đọc từ file .env
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Bỏ qua các biến môi trường không được khai báo trong class này
    )

# Khởi tạo một object settings duy nhất (Singleton) để import dùng chung toàn dự án
settings = Settings()
