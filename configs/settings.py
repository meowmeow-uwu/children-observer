"""
Centralized settings management using Pydantic Settings.

All sensitive values are loaded from .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Main application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- General ----
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    # ---- Dataset Paths ----
    dataset_childsun_path: Path = Path("./data/childsun")
    dataset_violence_path: Path = Path("./data/violence")
    model_weights_dir: Path = Path("./weights")

    # ---- RTSP Camera ----
    rtsp_url: str
    rtsp_fps: int = 25
    rtsp_resolution: str = "1920x1080"

    # ---- AI Inference ----
    inference_device: str = "cuda:0"
    inference_engine_type: Literal["yolo", "onnx", "tensorrt", "openvino"] = "onnx"
    edge_use_mock_ai_when_no_model: bool = False
    inference_conf_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    inference_iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    yolo_model_path: Path = Path("./weights/yolo26n.pt")
    pose_model_path: Path = Path("./weights/yolo26n-pose.pt")
    behavior_model_path: Path = Path("./weights/stgcn_violence.pt")

    # ---- Alert ----
    alert_cooldown_seconds: int = Field(default=30, ge=5)
    alert_clip_duration: int = Field(default=7, ge=3, le=15)
    alert_buffer_seconds: int = Field(default=15, ge=5, le=30)

    # ---- Security / Encryption ----
    e2ee_secret_key: str
    hmac_secret_key: str

    # ---- Backend Server ----
    backend_url: str = "http://localhost:8000"
    auth_jwt_secret: str
    auth_2fa_issuer: str = "AIChildGuardian"

    # ---- Mobile Gateway ----
    mobile_gateway_enabled: bool = True
    mobile_gateway_host: str = "0.0.0.0"
    mobile_gateway_port: int = Field(default=8765, ge=1024, le=65535)
    feedback_log_dir: Path = Path("./data/feedback")

    # ---- Federated Learning ----
    federated_server_url: str = "http://localhost:9000"
    ota_update_interval_hours: int = Field(default=24, ge=1)

    # ---- Privacy ----
    privacy_blur_strangers: bool = True
    privacy_face_detection_conf: float = Field(default=0.6, ge=0.0, le=1.0)

    @property
    def rtsp_width(self) -> int:
        """Get width from resolution string."""
        return int(self.rtsp_resolution.split("x")[0])

    @property
    def rtsp_height(self) -> int:
        """Get height from resolution string."""
        return int(self.rtsp_resolution.split("x")[1])

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Get cached application settings singleton."""
    return AppSettings()
