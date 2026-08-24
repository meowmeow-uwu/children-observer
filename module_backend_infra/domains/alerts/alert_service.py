from fastapi import HTTPException
from sqlalchemy.orm import Session
from .alert_repository import alert_repo
from .alert_schemas import AlertCreate, AlertUpdate
from infrastructure.signaling.server import manager
from infrastructure.telegram.client import send_telegram_alert
from core.config import settings

from domains.cameras.camera_repository import camera_repo
from domains.auth.auth_repository import user_repo
import os

class AlertService:
    @staticmethod
    async def create_and_broadcast_alert(db: Session, alert_in: AlertCreate):
        # 1. Tra cứu Camera ID thực tế trong Database từ chuỗi camera_id_string do Pi gửi lên
        camera_obj = camera_repo.get_by_camera_id_string(db, alert_in.camera_id)
        if not camera_obj:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy Camera với mã: {alert_in.camera_id}")

        # 2. Tạo bản sao dữ liệu Alert và ghi đè camera_id thành Integer để lưu DB hợp lệ
        alert_data = alert_in.model_dump()
        alert_data["camera_id"] = camera_obj.id # Ép về ID kiểu Integer

        # Xử lý URL ảnh
        if alert_data.get("snapshot_url") and not alert_data["snapshot_url"].startswith("http"):
            alert_data["snapshot_url"] = f"{settings.BACKEND_URL}/snapshots/{alert_data['snapshot_url']}"
            
        # 3. Lưu vào Database qua Repository
        new_alert = alert_repo.create_alert_record(db, alert_data)
        
        # 4. Đóng gói dữ liệu gửi qua WebSocket cho Frontend
        alert_dict = {
            "id": new_alert.id,
            "event_id": new_alert.event_id,
            "camera_id": camera_obj.camera_id_string,
            "camera_name": camera_obj.name,
            "title": new_alert.title,
            "severity": new_alert.severity,
            "status": new_alert.status,
            "snapshot_url": new_alert.snapshot_url,
            "roi_name": new_alert.roi_name,
        }
        await manager.broadcast({"type": "ALERT_NEW", "data": alert_dict})
        
        # 5. Lấy Telegram Chat ID tự động từ Chủ sở hữu Camera (Owner)
        telegram_chat_id = None
        if camera_obj.device and camera_obj.device.owner:
            telegram_chat_id = camera_obj.device.owner.telegram_chat_id

        # Fallback về TEST ID nếu User chưa cấu hình
        if not telegram_chat_id:
            telegram_chat_id = os.getenv("TEST_TELEGRAM_CHAT_ID")
            
        if settings.TELEGRAM_ALERTS_ENABLED and telegram_chat_id:
            telegram_msg = (
                f"🚨 <b>BÁO ĐỘNG: {new_alert.title}</b>\n\n"
                f"📍 <b>Khu vực:</b> {getattr(new_alert, 'roi_name', 'Không xác định')}\n"
                f"📷 <b>Camera:</b> {camera_obj.name}"
            )
            await send_telegram_alert(
                chat_id=telegram_chat_id,
                message=telegram_msg,
                image_url=new_alert.snapshot_url
            )
        
        return new_alert
    
    @staticmethod
    def update_alert(db: Session, alert_id: int, update_in: AlertUpdate):
        alert_obj = alert_repo.get(db, id=alert_id)
        if not alert_obj:
            return None
        return alert_repo.update(db, db_obj=alert_obj, obj_in=update_in)
        
    @staticmethod
    def delete_all_alerts(db: Session):
        alert_repo.delete_all_alerts(db)
