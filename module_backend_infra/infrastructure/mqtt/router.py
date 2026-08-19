import json
from loguru import logger
from core.database import SessionLocal
from domains.alerts.alert_service import AlertService
from domains.alerts.alert_schemas import AlertCreate
from domains.cameras.camera_repository import camera_repo
from infrastructure.signaling.server import manager
from utils.image_helpers import save_snapshot_bytes

async def handle_mqtt_message(message):
    """Bộ định tuyến trung tâm cho mọi tin nhắn MQTT"""
    topic = message.topic.value
    payload = message.payload

    logger.info(f"[MQTT SUB] Nhận dữ liệu từ: {topic}")

    if topic.endswith("/alerts"):
        await _process_alert(payload)
    elif "/snapshots" in topic:
        parts = topic.split("/")
        device_id = parts[1]
        event_id = parts[3] if len(parts) > 3 and parts[3] else None
        await _process_snapshot(device_id, payload, event_id)
    elif topic.endswith("/webrtc/answer"):
        try:
            answer_data = json.loads(payload.decode())
            target_web_id = answer_data.get("target") # ID của Parent App
            if target_web_id:
                await manager.send_personal_message(answer_data, target_web_id)
        except Exception as e:
            logger.error(f"[MQTT] Lỗi parse WebRTC Answer: {e}")
    elif topic.endswith("/status"):
        parts = topic.split("/")
        if len(parts) >= 3:
            await _process_camera_status(parts[1], payload)

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

async def _process_snapshot(device_id: str, payload: bytes, event_id: str | None = None):
    """Ủy quyền lưu byte ảnh chụp xuống đĩa cho image_helpers"""
    save_snapshot_bytes(device_id, payload, event_id)


async def _process_camera_status(camera_id: str, payload: bytes) -> None:
    """Persist the retained RTSP availability published by the Edge."""
    try:
        data = json.loads(payload.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("[MQTT] Bỏ qua camera status không phải JSON: {}", camera_id)
        return

    online = data.get("online")
    if not isinstance(online, bool):
        logger.warning("[MQTT] Bỏ qua camera status thiếu online boolean: {}", camera_id)
        return

    db = SessionLocal()
    try:
        camera = camera_repo.get_by_camera_id_string(db, camera_id)
        if not camera:
            logger.warning("[MQTT] Camera status cho ID chưa đăng ký: {}", camera_id)
            return
        next_status = "online" if online else "offline"
        if camera.status != next_status:
            camera.status = next_status
            db.commit()
            logger.info(
                "[MQTT] Camera {} -> {} ({})",
                camera_id,
                next_status,
                data.get("reason", "unknown"),
            )
    finally:
        db.close()
