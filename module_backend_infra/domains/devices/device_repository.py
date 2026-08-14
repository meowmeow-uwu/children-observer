# domains/devices/device_repository.py
from sqlalchemy.orm import Session
from core.repository import CRUDBase
from .device_models import Device
from .device_schemas import DeviceCreate

class DeviceRepository(CRUDBase[Device, DeviceCreate, DeviceCreate]):
    def get_by_mac_address(self, db: Session, mac_address: str) -> Device | None:
        """Tìm thiết bị dựa trên địa chỉ MAC."""
        return db.query(self.model).filter(self.model.mac_address == mac_address).first()

    def get_by_user_id(self, db: Session, user_id: int):
        """Lấy toàn bộ thiết bị mà User đang sở hữu."""
        return db.query(self.model).filter(self.model.user_id == user_id).all()

    def create_with_owner(self, db: Session, obj_in: DeviceCreate, user_id: int) -> Device:
        """Tạo thiết bị mới và gán ngay cho User (Owner)."""
        db_obj = Device(
            user_id=user_id,
            mac_address=obj_in.mac_address,
            name=obj_in.name,
            device_secret_key=obj_in.device_secret_key,
            status="ONLINE"
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
        
    def check_user_owns_device(self, db: Session, device_id: int, user_id: int) -> bool:
        """Kiểm tra xem User có phải là chủ sở hữu của Device này không."""
        device = db.query(self.model).filter(
            self.model.id == device_id, 
            self.model.user_id == user_id
        ).first()
        return device is not None

# Khởi tạo instance dùng chung
device_repo = DeviceRepository(Device)