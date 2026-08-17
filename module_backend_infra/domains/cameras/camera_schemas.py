from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# --- Point Schema ---
class PointSchema(BaseModel):
    x: float
    y: float

# --- ROI Schemas ---
class ROIZoneBase(BaseModel):
    name: str
    type: str = "polygon"
    points: List[PointSchema]
    sensitivity: Optional[str] = "high"
    enabled: Optional[bool] = True
    rules: dict = Field(default_factory=dict)

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
    alerts_paused: bool = False
    roi_zones: List[ROIZoneResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
