from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db

# Chắc chắn rằng domains/auth/dependencies.py ĐÃ ĐƯỢC TẠO thì dòng này mới không lỗi
from domains.auth.dependencies import get_current_user
from domains.auth.auth_models import User

from . import alert_schemas
from .alert_repository import alert_repo
from .alert_service import AlertService
from datetime import datetime

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("/", response_model=List[alert_schemas.AlertResponse])
def get_alerts(
    camera_id: Optional[str] = None, 
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách cảnh báo. Hỗ trợ lọc theo camera ID và khoảng thời gian (ISO 8601).
    """
    return alert_repo.get_recent_alerts(
        db, 
        camera_id_string=camera_id, 
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

@router.post("/", response_model=alert_schemas.AlertResponse)
async def create_alert(alert: alert_schemas.AlertCreate, db: Session = Depends(get_db)):
    return await AlertService.create_and_broadcast_alert(db, alert)

@router.delete("/")
def delete_all_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Xóa toàn bộ cảnh báo (Demo mục đích).
    """
    AlertService.delete_all_alerts(db)
    return {"detail": "Đã xóa toàn bộ cảnh báo"}

@router.patch("/{alert_id}", response_model=alert_schemas.AlertResponse)
def update_alert_status(
    alert_id: int,
    alert_in: alert_schemas.AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật trạng thái hoặc ghi chú của cảnh báo.
    """
    alert = AlertService.update_alert(db, alert_id, alert_in)
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    return alert