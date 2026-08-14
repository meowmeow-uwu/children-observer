import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from module_backend_infra.signaling.server import manager

from . import schemas
from .database import models
from .database.config import get_db
from .snapshot_store import clear_snapshots, save_snapshot

router = APIRouter(prefix="/api", tags=["Restful API"])

DEFAULT_RULES = {
    "enterZone": True,
    "stayTooLong": False,
    "stayDurationSeconds": 5,
    "approachZone": False,
}


def parse_points(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [p for p in data if isinstance(p, dict) and "x" in p and "y" in p]
    except (json.JSONDecodeError, TypeError):
        return []


def parse_rules(raw: str | None) -> dict:
    if not raw:
        return dict(DEFAULT_RULES)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return dict(DEFAULT_RULES)
        merged = dict(DEFAULT_RULES)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, TypeError):
        return dict(DEFAULT_RULES)


def serialize_rules(rules: dict) -> str:
    merged = dict(DEFAULT_RULES)
    if rules:
        merged.update(rules)
    return json.dumps(merged)


def _roi_to_dict(r: models.ROIZone) -> dict:
    return {
        "id": r.id,
        "camera_id": r.camera_id,
        "name": r.name,
        "type": r.type or "polygon",
        "points": parse_points(r.points),
        "sensitivity": r.sensitivity,
        "enabled": r.enabled,
        "rules": parse_rules(r.rules),
    }


# --- CAMERA ENDPOINTS ---


@router.get("/cameras", response_model=List[schemas.CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    cameras = db.query(models.Camera).all()
    result = []
    for cam in cameras:
        roi_db = (
            db.query(models.ROIZone).filter(models.ROIZone.camera_id == cam.camera_id_string).all()
        )
        result.append(
            {
                "id": cam.id,
                "camera_id_string": cam.camera_id_string,
                "name": cam.name,
                "location": cam.location,
                "status": cam.status,
                "is_active": cam.is_active,
                "alerts_paused": bool(cam.alerts_paused),
                "roi_zones": [_roi_to_dict(r) for r in roi_db],
            }
        )
    return result


@router.get("/cameras/{camera_id_string}", response_model=schemas.CameraResponse)
def get_camera(camera_id_string: str, db: Session = Depends(get_db)):
    cam = db.query(models.Camera).filter(models.Camera.camera_id_string == camera_id_string).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    roi_db = db.query(models.ROIZone).filter(models.ROIZone.camera_id == cam.camera_id_string).all()
    return {
        "id": cam.id,
        "camera_id_string": cam.camera_id_string,
        "name": cam.name,
        "location": cam.location,
        "status": cam.status,
        "is_active": cam.is_active,
        "alerts_paused": bool(cam.alerts_paused),
        "roi_zones": [_roi_to_dict(r) for r in roi_db],
    }


@router.post("/cameras", response_model=schemas.CameraResponse)
def create_camera(camera: schemas.CameraCreate, db: Session = Depends(get_db)):
    db_cam = (
        db.query(models.Camera)
        .filter(models.Camera.camera_id_string == camera.camera_id_string)
        .first()
    )
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
        "alerts_paused": bool(new_cam.alerts_paused),
        "roi_zones": [],
    }


@router.post("/cameras/{camera_id_string}/alerts-paused", response_model=schemas.CameraResponse)
def set_camera_alerts_paused(
    camera_id_string: str, update: schemas.CameraPauseUpdate, db: Session = Depends(get_db)
):
    cam = db.query(models.Camera).filter(models.Camera.camera_id_string == camera_id_string).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")

    cam.alerts_paused = update.paused
    db.commit()
    db.refresh(cam)
    roi_db = db.query(models.ROIZone).filter(models.ROIZone.camera_id == cam.camera_id_string).all()
    return {
        "id": cam.id,
        "camera_id_string": cam.camera_id_string,
        "name": cam.name,
        "location": cam.location,
        "status": cam.status,
        "is_active": cam.is_active,
        "alerts_paused": bool(cam.alerts_paused),
        "roi_zones": [_roi_to_dict(r) for r in roi_db],
    }


# --- ROI ENDPOINTS ---


@router.get("/cameras/{camera_id_string}/roi", response_model=List[schemas.ROIZoneResponse])
def get_camera_roi(camera_id_string: str, db: Session = Depends(get_db)):
    rois = db.query(models.ROIZone).filter(models.ROIZone.camera_id == camera_id_string).all()
    return [_roi_to_dict(r) for r in rois]


@router.post("/cameras/{camera_id_string}/roi", response_model=List[schemas.ROIZoneResponse])
def save_camera_roi(
    camera_id_string: str, zones: List[schemas.ROIZoneBase], db: Session = Depends(get_db)
):
    """Thay thế toàn bộ danh sách ROI của camera (replace-whole-list có chủ đích).

    Frontend luôn gửi danh sách đầy đủ các vùng của camera; toàn bộ thao tác
    delete + insert nằm trong một transaction để tránh trạng thái mất dữ liệu.
    """
    cam = db.query(models.Camera).filter(models.Camera.camera_id_string == camera_id_string).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")

    saved_zones = []
    try:
        db.query(models.ROIZone).filter(models.ROIZone.camera_id == camera_id_string).delete()
        for z in zones:
            pts_json = json.dumps([p.model_dump() for p in z.points])
            rules_json = serialize_rules(z.rules.model_dump() if z.rules else None)
            new_zone = models.ROIZone(
                camera_id=camera_id_string,
                name=z.name,
                type=z.type or "polygon",
                points=pts_json,
                sensitivity=z.sensitivity,
                enabled=z.enabled,
                rules=rules_json,
            )
            db.add(new_zone)
            db.flush()
            db.refresh(new_zone)
            saved_zones.append(
                {
                    "id": new_zone.id,
                    "camera_id": new_zone.camera_id,
                    "name": new_zone.name,
                    "type": new_zone.type or "polygon",
                    "points": [p.model_dump() for p in z.points],
                    "sensitivity": new_zone.sensitivity,
                    "enabled": new_zone.enabled,
                    "rules": parse_rules(new_zone.rules),
                }
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return saved_zones


# --- ALERT ENDPOINTS ---


@router.get("/alerts", response_model=List[schemas.AlertResponse])
def get_alerts(camera_id: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(models.AlertLog)
    if camera_id:
        query = query.filter(models.AlertLog.camera_id == camera_id)
    alerts = query.order_by(models.AlertLog.created_at.desc()).limit(limit).all()
    return alerts


@router.delete("/alerts")
async def clear_alerts(db: Session = Depends(get_db)):
    """Xóa lịch sử cảnh báo của phiên demo và đồng bộ mọi tab đang mở."""
    deleted = db.query(models.AlertLog).delete(synchronize_session=False)
    db.commit()
    deleted_snapshots = clear_snapshots()
    await manager.broadcast({"type": "alerts_cleared"})
    return {"deleted": deleted, "deleted_snapshots": deleted_snapshots}


@router.post("/alerts", response_model=schemas.AlertResponse)
async def create_alert(alert: schemas.AlertCreate, db: Session = Depends(get_db)):
    values = alert.model_dump(exclude={"snapshot_base64"})
    if alert.snapshot_base64:
        try:
            values["snapshot_url"] = save_snapshot(alert.snapshot_base64)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    new_alert = models.AlertLog(**values)
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
        "createdAt": new_alert.created_at.isoformat() if new_alert.created_at else "",
    }

    await manager.broadcast({"type": "new_alert", "alert": alert_dict})

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
