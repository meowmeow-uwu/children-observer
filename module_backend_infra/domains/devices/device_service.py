# domains/devices/device_service.py
from domains.devices import device_schemas
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from domains.auth.auth_models import User
from .device_schemas import DeviceCreate
from .device_repository import device_repo
from domains.auth.auth_repository import user_repo
from .device_models import DeviceMember

class DeviceService:
    @staticmethod
    def register_device(db: Session, device_in: DeviceCreate, current_user: User):
        # 1. Kiểm tra xem MAC Address đã có ai đăng ký chưa
        existing_device = device_repo.get_by_mac_address(db, device_in.mac_address)
        if existing_device:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Thiết bị với MAC Address này đã được đăng ký trên hệ thống."
            )
            
        # 2. Gọi Repo để lưu và gán thiết bị cho User hiện tại
        return device_repo.create_with_owner(db, obj_in=device_in, user_id=current_user.id)

    @staticmethod
    def get_user_devices(db: Session, current_user: User):
        # Lấy danh sách thiết bị
        return device_repo.get_by_user_id(db, user_id=current_user.id)

    @staticmethod
    def delete_device(db: Session, device_id: int, current_user: User):
        # 1. Kiểm tra tồn tại
        device = device_repo.get(db, id=device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị.")
            
        # 2. BẢO MẬT: Chỉ chủ sở hữu (Owner) mới được xóa
        if device.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xóa thiết bị này.")
            
        # Xóa (CASCADE tự động dọn Camera, ROI, Alerts liên quan trong DB)
        device_repo.remove(db, id=device_id)
        return {"detail": "Đã xóa thiết bị thành công."}

    @staticmethod
    def share_device(db: Session, device_id: int, share_in: device_schemas.DeviceShareRequest, current_user: User):
        # 1. Kiểm tra thiết bị và quyền Owner
        device = device_repo.get(db, id=device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị.")
        if device.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Chỉ chủ sở hữu mới có quyền chia sẻ thiết bị.")
            
        # 2. Tìm người dùng được chia sẻ qua Email
        target_user = user_repo.get_by_email(db, email=share_in.email)
        if not target_user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng với email này trong hệ thống.")
            
        # 3. Tránh tự chia sẻ cho chính mình
        if target_user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Bạn không thể tự chia sẻ thiết bị cho chính mình.")
            
        # 4. Kiểm tra xem đã chia sẻ trước đó chưa
        existing_share = db.query(DeviceMember).filter(
            DeviceMember.device_id == device_id,
            DeviceMember.user_id == target_user.id
        ).first()
        if existing_share:
            raise HTTPException(status_code=400, detail="Thiết bị này đã được chia sẻ với người dùng này từ trước.")
            
        # 5. Lưu vào bảng DeviceMember
        new_member = DeviceMember(
            device_id=device_id,
            user_id=target_user.id,
            role=share_in.role
        )
        db.add(new_member)
        db.commit()
        
        return {"detail": f"Đã chia sẻ thiết bị thành công cho {target_user.email}"}

    @staticmethod
    def revoke_share(db: Session, device_id: int, email: str, current_user: User):
        device = device_repo.get(db, id=device_id)
        if not device or device.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Chỉ Owner mới có quyền thu hồi chia sẻ.")
            
        target_user = user_repo.get_by_email(db, email=email)
        if not target_user:
            raise HTTPException(status_code=404, detail="Email không tồn tại.")
            
        share_record = db.query(DeviceMember).filter(
            DeviceMember.device_id == device_id,
            DeviceMember.user_id == target_user.id
        ).first()
        
        if not share_record:
            raise HTTPException(status_code=404, detail="Người dùng này chưa được chia sẻ thiết bị.")
            
        db.delete(share_record)
        db.commit()
        return {"detail": f"Đã thu hồi quyền truy cập của {email}."}