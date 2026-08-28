# domains/cameras/camera_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from domains.auth.dependencies import get_current_user
from domains.auth.auth_models import User
from . import camera_schemas
from .camera_service import CameraService

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])


@router.get("", response_model=List[camera_schemas.CameraResponse])
def get_cameras(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # TRUYỀN THÊM current_user
    return CameraService.get_cameras_with_roi(db, current_user)


@router.get("/{camera_id_string}", response_model=camera_schemas.CameraResponse)
def get_camera(
    camera_id_string: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CameraService.get_camera_with_roi(db, camera_id_string, current_user)


@router.get("/{camera_id_string}/roi", response_model=List[camera_schemas.ROIZoneResponse])
def get_camera_roi(
    camera_id_string: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CameraService.get_camera_with_roi(db, camera_id_string, current_user)["roi_zones"]

@router.post("/", response_model=camera_schemas.CameraResponse)
def create_camera(
    camera: camera_schemas.CameraCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # TRUYỀN THÊM current_user
    return CameraService.create_camera(db, camera, current_user)

@router.post("/{camera_id_string}/roi", response_model=List[camera_schemas.ROIZoneResponse])
async def save_camera_roi(
    camera_id_string: str, 
    zones: List[camera_schemas.ROIZoneBase], 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # TRUYỀN THÊM current_user
    return await CameraService.update_camera_roi(db, camera_id_string, zones, current_user)


@router.post("/{camera_id_string}/alerts-paused")
def set_alerts_paused(
    camera_id_string: str,
    payload: camera_schemas.CameraAlertsPausedUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CameraService.update_alerts_paused(db, camera_id_string, payload.paused, current_user)

@router.delete("/{camera_id_string}")
def delete_camera(
    camera_id_string: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CameraService.delete_camera(db, camera_id_string, current_user)
