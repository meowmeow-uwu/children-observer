# domains/cameras/camera_repository.py
from sqlalchemy.orm import Session
from core.repository import CRUDBase
from .camera_models import Camera, ROIZone
from .camera_schemas import CameraCreate, ROIZoneCreate

class CameraRepository(CRUDBase[Camera, CameraCreate, CameraCreate]):
    def get_by_camera_id_string(self, db: Session, camera_id_string: str) -> Camera | None:
        return db.query(self.model).filter(self.model.camera_id_string == camera_id_string).first()

class ROIRepository(CRUDBase[ROIZone, ROIZoneCreate, ROIZoneCreate]):
    def get_by_camera_id(self, db: Session, camera_id_string: str):
        return db.query(self.model).filter(self.model.camera_id == camera_id_string).all()

    def delete_by_camera_id(self, db: Session, camera_id_string: str):
        db.query(self.model).filter(self.model.camera_id == camera_id_string).delete()
        db.commit()

camera_repo = CameraRepository(Camera)
roi_repo = ROIRepository(ROIZone)