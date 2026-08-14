# domains/alerts/alert_repository.py
from sqlalchemy.orm import Session
from core.repository import CRUDBase
from .alert_models import Alert
from .alert_schemas import AlertCreate, AlertUpdate
from domains.cameras.camera_models import Camera
from datetime import datetime

class AlertRepository(CRUDBase[Alert, AlertCreate, AlertUpdate]):
    def get_recent_alerts(
        self, 
        db: Session, 
        camera_id_string: str = None, 
        start_date: datetime = None, 
        end_date: datetime = None, 
        limit: int = 50
    ):
        query = db.query(self.model)
        
        # Nếu filter theo String ID, ta phải JOIN với bảng Camera
        if camera_id_string:
            query = query.join(Camera).filter(Camera.camera_id_string == camera_id_string)
            
        # Lọc theo khung thời gian
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
            
        return query.order_by(self.model.created_at.desc()).limit(limit).all()

    def create_alert_record(self, db: Session, alert_data: dict) -> Alert:
        new_alert = Alert(**alert_data)
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert

alert_repo = AlertRepository(Alert)