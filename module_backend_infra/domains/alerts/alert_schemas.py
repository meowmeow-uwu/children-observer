# domains/alerts/alert_schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AlertCreate(BaseModel):
    event_id: Optional[str] = None
    camera_id: str
    camera_name: Optional[str] = ""
    title: str
    severity: Optional[str] = "warning"
    status: Optional[str] = "unread"
    snapshot_url: Optional[str] = ""
    roi_name: Optional[str] = ""
    notes: Optional[str] = ""

class AlertUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

# TÁCH RỜI ALERT RESPONSE (Không kế thừa AlertCreate nữa)
class AlertResponse(BaseModel):
    id: int
    event_id: Optional[str] = None
    camera_id: int  # <-- Chuyển thành int để khớp với Khóa ngoại trong DB
    camera_name: Optional[str] = ""
    title: str
    severity: str
    status: str
    snapshot_url: Optional[str] = ""
    roi_name: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
