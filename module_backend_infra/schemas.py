from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Point Schema ---
class PointSchema(BaseModel):
    x: float
    y: float

# --- ROI Schemas ---
class ROIZoneBase(BaseModel):
    name: str
    points: List[PointSchema]
    sensitivity: Optional[str] = "high"
    enabled: Optional[bool] = True

class ROIZoneCreate(ROIZoneBase):
    camera_id: str

class ROIZoneResponse(ROIZoneBase):
    id: int
    camera_id: str

    class Config:
        from_attributes = True

# --- Camera Schemas ---
class CameraBase(BaseModel):
    camera_id_string: str
    name: str
    location: Optional[str] = ""
    status: Optional[str] = "online"
    is_active: Optional[bool] = True

class CameraCreate(CameraBase):
    pass

class CameraResponse(CameraBase):
    id: int
    roi_zones: List[ROIZoneResponse] = []

    class Config:
        from_attributes = True

# --- Alert Log Schemas ---
class AlertCreate(BaseModel):
    camera_id: str
    camera_name: Optional[str] = ""
    title: str
    severity: Optional[str] = "warning" # danger, warning, info
    status: Optional[str] = "unread"
    snapshot_url: Optional[str] = ""
    roi_name: Optional[str] = ""
    notes: Optional[str] = ""

class AlertUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class AlertResponse(AlertCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
