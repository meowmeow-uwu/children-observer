from sqlalchemy import Column, Integer, String, BigInteger, DateTime, func
from sqlalchemy.orm import relationship
from core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False, default="")
    telegram_chat_id = Column(BigInteger, unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owned_devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    shared_devices = relationship("DeviceMember", back_populates="user", cascade="all, delete-orphan")
