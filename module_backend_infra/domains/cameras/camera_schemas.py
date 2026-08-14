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
    device_id: int
    rtsp_url: str = ""
    
class CameraResponse(CameraBase):
    id: int
    roi_zones: List[ROIZoneResponse] = []

    class Config:
        from_attributes = True
