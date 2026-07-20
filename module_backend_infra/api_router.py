import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .database.config import get_db
from .database import models
from . import schemas

router = APIRouter(prefix="/api", tags=["Restful API"])

# --- CAMERA ENDPOINTS ---

@router.get("/cameras", response_model=List[schemas.CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    cameras = db.query(models.Camera).all()
    result = []
    for cam in cameras:
        roi_db = db.query(models.ROIZone).filter(models.ROIZone.camera_id == cam.camera_id_string).all()
        roi_zones = []
        for r in roi_db:
            try:
                pts = json.loads(r.points) if r.points else []
            except Exception:
                pts = []
            roi_zones.append({
                "id": r.id,
                "camera_id": r.camera_id,
                "name": r.name,
                "points": pts,
                "sensitivity": r.sensitivity,
                "enabled": r.enabled
            })
        
        result.append({
            "id": cam.id,
            "camera_id_string": cam.camera_id_string,
            "name": cam.name,
            "location": cam.location,
            "status": cam.status,
            "is_active": cam.is_active,
            "roi_zones": roi_zones
        })
    return result

@router.post("/cameras", response_model=schemas.CameraResponse)
def create_camera(camera: schemas.CameraCreate, db: Session = Depends(get_db)):
    db_cam = db.query(models.Camera).filter(models.Camera.camera_id_string == camera.camera_id_string).first()
    if db_cam:
        raise HTTPException(status_code=400, detail="Camera ID đã tồn tại")
    
    new_cam = models.Camera(**camera.model_dump())
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)
    return {
        "id": new_cam.id,
        "camera_id_string": new_cam.camera_id_string,
        "name": new_cam.name,
        "location": new_cam.location,
        "status": new_cam.status,
        "is_active": new_cam.is_active,
        "roi_zones": []
    }

# --- ROI ENDPOINTS ---

@router.get("/cameras/{camera_id_string}/roi", response_model=List[schemas.ROIZoneResponse])
def get_camera_roi(camera_id_string: str, db: Session = Depends(get_db)):
    rois = db.query(models.ROIZone).filter(models.ROIZone.camera_id == camera_id_string).all()
    result = []
    for r in rois:
        try:
            pts = json.loads(r.points) if r.points else []
        except Exception:
            pts = []
        result.append({
            "id": r.id,
            "camera_id": r.camera_id,
            "name": r.name,
            "points": pts,
            "sensitivity": r.sensitivity,
            "enabled": r.enabled
        })
    return result

@router.post("/cameras/{camera_id_string}/roi", response_model=List[schemas.ROIZoneResponse])
def save_camera_roi(camera_id_string: str, zones: List[schemas.ROIZoneBase], db: Session = Depends(get_db)):
    # Xóa ROI cũ của camera này và thay thế bằng danh sách mới
    db.query(models.ROIZone).filter(models.ROIZone.camera_id == camera_id_string).delete()
    
    saved_zones = []
    for z in zones:
        pts_json = json.dumps([p.model_dump() for p in z.points])
        new_zone = models.ROIZone(
            camera_id=camera_id_string,
            name=z.name,
            points=pts_json,
            sensitivity=z.sensitivity,
            enabled=z.enabled
        )
        db.add(new_zone)
        db.commit()
        db.refresh(new_zone)
        
        saved_zones.append({
            "id": new_zone.id,
            "camera_id": new_zone.camera_id,
            "name": new_zone.name,
            "points": [p.model_dump() for p in z.points],
            "sensitivity": new_zone.sensitivity,
            "enabled": new_zone.enabled
        })
    return saved_zones

# --- ALERT ENDPOINTS ---

@router.get("/alerts", response_model=List[schemas.AlertResponse])
def get_alerts(camera_id: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(models.AlertLog)
    if camera_id:
        query = query.filter(models.AlertLog.camera_id == camera_id)
    alerts = query.order_by(models.AlertLog.created_at.desc()).limit(limit).all()
    return alerts

from module_backend_infra.signaling.server import manager

@router.post("/alerts", response_model=schemas.AlertResponse)
async def create_alert(alert: schemas.AlertCreate, db: Session = Depends(get_db)):
    new_alert = models.AlertLog(**alert.model_dump())
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    
    # Broadcast sự kiện cảnh báo thời gian thực qua WebSocket tới tất cả Frontend
    alert_dict = {
        "id": str(new_alert.id),
        "cameraId": new_alert.camera_id,
        "cameraName": new_alert.camera_name,
        "title": new_alert.title,
        "severity": new_alert.severity,
        "status": new_alert.status,
        "snapshotUrl": new_alert.snapshot_url,
        "roiName": new_alert.roi_name,
        "createdAt": new_alert.created_at.isoformat() if new_alert.created_at else ""
    }
    
    await manager.broadcast({
        "type": "new_alert",
        "alert": alert_dict
    })
    
    return new_alert

@router.patch("/alerts/{alert_id}", response_model=schemas.AlertResponse)
def update_alert_status(alert_id: int, update: schemas.AlertUpdate, db: Session = Depends(get_db)):
    alert = db.query(models.AlertLog).filter(models.AlertLog.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    
    if update.status is not None:
        alert.status = update.status
    if update.notes is not None:
        alert.notes = update.notes
        
    db.commit()
    db.refresh(alert)
    return alert
