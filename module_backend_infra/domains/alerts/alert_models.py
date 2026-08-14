# domains/alerts/alert_models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from core.database import Base

class Alert(Base):
    __tablename__ = "alerts"
    
    # ID dạng số nguyên (Khớp với AlertResponse schema)
    id = Column(Integer, primary_key=True, index=True)
    
    # Khóa ngoại liên kết tới camera
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    
    # Các trường thông tin cảnh báo (Khớp với AlertCreate schema)
    camera_name = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(50), default="warning")
    status = Column(String(50), default="unread")
    snapshot_url = Column(String(500), nullable=True)
    roi_name = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Quan hệ (Relationship)
    camera = relationship("Camera", back_populates="alerts")