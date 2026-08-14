# domains/cameras/camera_service.py
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from .camera_repository import camera_repo, roi_repo
from .camera_schemas import CameraCreate, ROIZoneBase
from .camera_models import ROIZone, Camera
from infrastructure.mqtt.client import mqtt_manager 
from domains.auth.auth_models import User
from domains.devices.device_models import Device
from domains.devices.device_repository import device_repo

class CameraService:
    @staticmethod
    def create_camera(db: Session, cam_in: CameraCreate, current_user: User):
        # 1. BẢO MẬT: Kiểm tra xem User có quyền với Device này không
        owns_device = device_repo.check_user_owns_device(db, cam_in.device_id, current_user.id)
        if not owns_device:
            raise HTTPException(status_code=403, detail="Bạn không có quyền thêm camera vào thiết bị này.")

        existing_cam = camera_repo.get_by_camera_id_string(db, cam_in.camera_id_string)
        if existing_cam:
            raise HTTPException(status_code=400, detail="Camera ID đã tồn tại.")
            
        return camera_repo.create(db, obj_in=cam_in)

    @staticmethod
    def get_cameras_with_roi(db: Session, current_user: User):
        # 1. BẢO MẬT: Chỉ lấy Camera thuộc về Device của current_user (INNER JOIN)
        cameras = db.query(Camera).join(Device).filter(Device.user_id == current_user.id).all()
        
        result = []
        for cam in cameras:
            roi_db = db.query(ROIZone).filter(ROIZone.camera_id == cam.id).all()
            roi_zones = []
            for r in roi_db:
                try:
                    pts = json.loads(r.polygon_points) if r.polygon_points else []
                except Exception:
                    pts = []
                roi_zones.append({
                    "id": r.id,
                    "camera_id": cam.camera_id_string,
                    "name": r.name,
                    "points": pts,
                    "sensitivity": getattr(r, "sensitivity", "high"),
                    "enabled": getattr(r, "enabled", True)
                })
            
            cam_data = cam.__dict__.copy()
            cam_data["roi_zones"] = roi_zones
            result.append(cam_data)
            
        return result

    @staticmethod
    async def update_camera_roi(db: Session, camera_id_string: str, zones: list[ROIZoneBase], current_user: User):
        camera_obj = camera_repo.get_by_camera_id_string(db, camera_id_string)
        if not camera_obj:
            raise HTTPException(status_code=404, detail="Camera không tồn tại")

        # 1. BẢO MẬT: Kiểm tra xem User có quyền sửa Camera này không
        if camera_obj.device.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền tinh chỉnh vùng cấm của camera này.")

        db.query(ROIZone).filter(ROIZone.camera_id == camera_obj.id).delete()
        db.commit()
        
        saved_zones = []
        for z in zones:
            pts_json = json.dumps([p.model_dump() for p in z.points])
            new_zone_data = {
                "camera_id": camera_obj.id,
                "name": z.name,
                "polygon_points": pts_json,
            }
            new_zone = ROIZone(**new_zone_data)
            db.add(new_zone)
            db.commit()
            db.refresh(new_zone)
            
            zone_response = {
                "id": new_zone.id,
                "camera_id": camera_id_string,
                "name": new_zone.name,
                "points": [p.model_dump() for p in z.points],
                "sensitivity": getattr(z, "sensitivity", "high"),
                "enabled": getattr(z, "enabled", True)
            }
            saved_zones.append(zone_response)
            
        roi_payload = {
            "camera_id": camera_id_string,
            "zones": [
                {
                    "name": z.name,
                    "points": [{"x": p.x, "y": p.y} for p in z.points]
                } for z in zones
            ]
        }
        
        await mqtt_manager.publish(
            topic=f"devices/{camera_id_string}/roi/update",
            payload=roi_payload,
            retain=True
        )
        
        return saved_zones

    @staticmethod
    def delete_camera(db: Session, camera_id_string: str, current_user: User):
        cam = camera_repo.get_by_camera_id_string(db, camera_id_string)
        if not cam:
            raise HTTPException(status_code=404, detail="Không tìm thấy Camera.")
        # Bảo mật: Chỉ chủ thiết bị mới được xóa
        if cam.device.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền xóa Camera này.")
            
        camera_repo.remove(db, id=cam.id)
        return {"detail": "Xóa camera thành công."}