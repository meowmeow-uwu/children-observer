# domains/cameras/camera_repository.py
from sqlalchemy.orm import Session
from core.repository import CRUDBase
from .camera_models import Camera, ROIZone
from .camera_schemas import CameraCreate, ROIZoneCreate

from domains.devices.device_models import Device

class CameraRepository(CRUDBase[Camera, CameraCreate, CameraCreate]):
    def get_by_camera_id_string(self, db: Session, camera_id_string: str) -> Camera | None:
        return db.query(self.model).filter(self.model.camera_id_string == camera_id_string).first()

    def get_user_cameras(self, db: Session, user_id: int) -> list[Camera]:
        return db.query(self.model).join(Device).filter(Device.user_id == user_id).all()

class ROIRepository(CRUDBase[ROIZone, ROIZoneCreate, ROIZoneCreate]):
    def get_by_camera_pk(self, db: Session, camera_pk: int) -> list[ROIZone]:
        return db.query(self.model).filter(self.model.camera_id == camera_pk).all()

    def replace_rois_for_camera(self, db: Session, camera_pk: int, zones_data: list[dict]) -> list[ROIZone]:
        db.query(self.model).filter(self.model.camera_id == camera_pk).delete()
        saved_zones = []
        for zd in zones_data:
            new_zone = ROIZone(
                camera_id=camera_pk,
                name=zd["name"],
                polygon_points=zd["polygon_points"],
                zone_type=zd.get("zone_type", "polygon"),
                sensitivity=zd.get("sensitivity", "high"),
                enabled=zd.get("enabled", True),
                rules=zd.get("rules", {}),
            )
            db.add(new_zone)
            saved_zones.append(new_zone)
        db.commit()
        for zone in saved_zones:
            db.refresh(zone)
        return saved_zones

camera_repo = CameraRepository(Camera)
roi_repo = ROIRepository(ROIZone)
