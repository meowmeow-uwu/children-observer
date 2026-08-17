from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from core.database import Base
from sqlalchemy.dialects.postgresql import JSONB

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_id_string = Column(String(100), unique=True, nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(50), nullable=True)
    rtsp_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    location = Column(String(255), nullable=True, default="")
    status = Column(String(50), nullable=True, default="online")
    alerts_paused = Column(Boolean, nullable=False, default=False)

    device = relationship("Device", back_populates="cameras")
    roi_zones = relationship("ROIZone", back_populates="camera", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="camera", cascade="all, delete-orphan")


class ROIZone(Base):
    __tablename__ = "roi_zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False, default="Vùng cấm")
    polygon_points = Column(JSON, nullable=False)
    zone_type = Column(String(20), nullable=False, default="polygon")
    sensitivity = Column(String(20), nullable=False, default="high")
    enabled = Column(Boolean, nullable=False, default=True)
    rules = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    camera = relationship("Camera", back_populates="roi_zones")
