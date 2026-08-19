from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from domains.auth.dependencies import get_current_user
from domains.auth.auth_models import User
from . import device_schemas
from .device_service import DeviceService

router = APIRouter(prefix="/api/devices", tags=["Devices"])

@router.get("", response_model=List[device_schemas.DeviceResponse])
def get_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách toàn bộ Raspberry Pi đang thuộc quyền sở hữu của Phụ huynh.
    """
    return DeviceService.get_user_devices(db, current_user)

@router.post("", response_model=device_schemas.DeviceResponse)
def register_device(
    device_in: device_schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Đăng ký Raspberry Pi mới vào tài khoản của Phụ huynh.
    Yêu cầu nhập MAC Address và Secret Key (lấy từ tem dán trên thiết bị).
    """
    return DeviceService.register_device(db, device_in, current_user)

@router.delete("/{device_id}", response_model=device_schemas.MessageResponse)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Xóa một Raspberry Pi khỏi hệ thống.
    Xóa toàn bộ camera, vùng cấm và cảnh báo liên kết với nó.
    """
    return DeviceService.delete_device(db, device_id, current_user)


@router.post("/{device_id}/share", response_model=device_schemas.MessageResponse)
def share_device(
    device_id: int,
    share_in: device_schemas.DeviceShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chia sẻ quyền xem Camera từ thiết bị cho một tài khoản phụ huynh khác (qua Email).
    """
    return DeviceService.share_device(db, device_id, share_in, current_user)

@router.delete("/{device_id}/share/{email}", response_model=device_schemas.MessageResponse)
def revoke_device_share(
    device_id: int,
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return DeviceService.revoke_share(db, device_id, email, current_user)