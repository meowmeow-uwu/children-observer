from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mac_address = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, default="Raspberry Pi")
    device_secret_key = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="OFFLINE")
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="owned_devices")
    members = relationship("DeviceMember", back_populates="device", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="device", cascade="all, delete-orphan")


class DeviceMember(Base):
    __tablename__ = "device_members"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False, default="VIEWER")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="members")
    user = relationship("User", back_populates="shared_devices")

    __table_args__ = (UniqueConstraint("device_id", "user_id", name="uq_device_user"),)