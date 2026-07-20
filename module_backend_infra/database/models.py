from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .config import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_id_string = Column(String, unique=True, index=True) # Ví dụ: "camera_living_room_01"
    name = Column(String) # Ví dụ: "Phòng khách"
    location = Column(String, default="")
    status = Column(String, default="online") # online / offline
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ROIZone(Base):
    __tablename__ = "roi_zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True) # Tương ứng camera_id_string
    name = Column(String) # Ví dụ: "Khu vực cầu thang"
    points = Column(Text) # Chuỗi JSON chứa mảng tọa độ [{"x": 0.1, "y": 0.2}, ...]
    sensitivity = Column(String, default="high") # high, medium, low
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    camera_name = Column(String, default="")
    title = Column(String)
    severity = Column(String, default="warning") # danger, warning, info
    status = Column(String, default="unread") # unread, checking, resolved, false_alarm
    snapshot_url = Column(String, default="")
    roi_name = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())