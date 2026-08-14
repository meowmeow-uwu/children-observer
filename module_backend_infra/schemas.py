from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Point Schema ---
class PointSchema(BaseModel):
    x: float
    y: float

    @field_validator("x", "y")
    @classmethod
    def _validate_coord(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"tọa độ phải trong [0,1], nhận {v}")
        return v


# --- ROI Rules Schema ---
class ROIRules(BaseModel):
    enterZone: bool = True
    stayTooLong: bool = False
    stayDurationSeconds: int = Field(default=5, ge=1, le=3600)
    approachZone: bool = False


# --- ROI Schemas ---
class ROIZoneBase(BaseModel):
    name: str
    points: List[PointSchema]
    type: Optional[str] = "polygon"  # polygon | rectangle
    sensitivity: Optional[str] = "high"
    enabled: Optional[bool] = True
    rules: Optional[ROIRules] = ROIRules()

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("polygon", "rectangle"):
            raise ValueError("type chỉ chấp nhận polygon|rectangle")
        return v

    @field_validator("sensitivity")
    @classmethod
    def _validate_sensitivity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("low", "medium", "high"):
            raise ValueError("sensitivity chỉ chấp nhận low|medium|high")
        return v

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name không được rỗng")
        if len(v) > 80:
            raise ValueError("name tối đa 80 ký tự")
        return v

    @model_validator(mode="after")
    def _validate_point_count(self) -> "ROIZoneBase":
        zone_type = self.type or "polygon"
        if zone_type == "polygon" and len(self.points) < 3:
            raise ValueError("polygon cần ít nhất 3 điểm")
        if zone_type == "rectangle" and len(self.points) != 4:
            raise ValueError("rectangle cần đúng 4 điểm")
        return self


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
    alerts_paused: Optional[bool] = False
    roi_zones: List[ROIZoneResponse] = []

    class Config:
        from_attributes = True


class CameraPauseUpdate(BaseModel):
    paused: bool


# --- Alert Log Schemas ---
class AlertCreate(BaseModel):
    camera_id: str
    camera_name: Optional[str] = ""
    title: str
    severity: Optional[str] = "warning"  # danger, warning, info
    status: Optional[str] = "unread"
    snapshot_url: Optional[str] = ""
    roi_name: Optional[str] = ""
    notes: Optional[str] = ""
    # Chỉ dùng ở request Edge→backend; backend lưu file và không broadcast base64.
    snapshot_base64: Optional[str] = None


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class AlertResponse(AlertCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
