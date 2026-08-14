from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeviceBase(BaseModel):
    mac_address: str
    name: Optional[str] = "Raspberry Pi"

class DeviceCreate(DeviceBase):
    device_secret_key: str

class DeviceResponse(DeviceBase):
    id: int
    status: str
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True

class DeviceShareRequest(BaseModel):
    email: str
    role: Optional[str] = "VIEWER"  # Tương lai có thể nâng cấp thành "ADMIN"
    
class MessageResponse(BaseModel):
    detail: str