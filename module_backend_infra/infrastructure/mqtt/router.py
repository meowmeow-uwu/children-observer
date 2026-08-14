import json
from loguru import logger
from core.database import SessionLocal
from domains.alerts.alert_service import AlertService
from domains.alerts.alert_schemas import AlertCreate
from infrastructure.signaling.server import manager
from utils.image_helpers import save_snapshot_bytes

async def handle_mqtt_message(message):
    """Bộ định tuyến trung tâm cho mọi tin nhắn MQTT"""
    topic = message.topic.value
    payload = message.payload

    logger.info(f"[MQTT SUB] Nhận dữ liệu từ: {topic}")

    if topic.endswith("/alerts"):
        await _process_alert(payload)
    elif topic.endswith("/snapshots"):
        device_id = topic.split("/")[1]
        await _process_snapshot(device_id, payload)
    elif topic.endswith("/webrtc/answer"):
        try:
            answer_data = json.loads(payload.decode())
            target_web_id = answer_data.get("target") # ID của Parent App
            if target_web_id:
                await manager.send_personal_message(answer_data, target_web_id)
        except Exception as e:
            logger.error(f"[MQTT] Lỗi parse WebRTC Answer: {e}")

async def _process_alert(payload: bytes):
    """Xử lý JSON Cảnh báo từ Edge AI"""
    db = SessionLocal()
    try:
        data = json.loads(payload.decode())
        alert_in = AlertCreate(**data)
        
        # Tái sử dụng Service để lưu DB & Broadcast WebSocket
        await AlertService.create_and_broadcast_alert(db, alert_in)
        
    except json.JSONDecodeError:
        logger.error("[MQTT] Lỗi parse JSON Alert")
    except Exception as e:
        logger.error(f"[MQTT] Lỗi xử lý Alert: {e}")
    finally:
        db.close()

async def _process_snapshot(device_id: str, payload: bytes):
    """Ủy quyền lưu byte ảnh chụp xuống đĩa cho image_helpers"""
    save_snapshot_bytes(device_id, payload)