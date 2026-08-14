import json
import logging
from typing import Dict
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from infrastructure.mqtt.client import mqtt_manager
from core.config import settings
from core.database import SessionLocal
from domains.auth.auth_repository import user_repo
from domains.auth.auth_schemas import TokenPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SignalingServer")
router = APIRouter()

class ConnectionManager:
    """
    Lớp quản lý các kết nối WebSocket đang hoạt động.
    Lưu trữ theo dạng: { "client_id": WebSocket_Object }
    """
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        # Chấp nhận kết nối WebSocket
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client kết nối mới: {client_id}. Tổng số kết nối: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        # Xóa kết nối khi client ngắt
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client ngắt kết nối: {client_id}. Tổng số kết nối: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, target_id: str):
        # Gửi tin nhắn trực tiếp đến một client cụ thể
        target_ws = self.active_connections.get(target_id)
        if target_ws:
            await target_ws.send_json(message)
        else:
            logger.warning(f"Không tìm thấy client đích: {target_id} để gửi tin nhắn.")

    async def broadcast(self, message: dict):
        # Gửi tin nhắn tới tất cả client đang kết nối
        logger.info(f"Broadcast tin nhắn type='{message.get('type')}' tới {len(self.active_connections)} kết nối WebSocket.")
        disconnected = []
        for client_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Lỗi gửi broadcast tới {client_id}: {e}")
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)

# Khởi tạo một đối tượng quản lý kết nối duy nhất (Singleton)
manager = ConnectionManager()

def verify_ws_token(token: str):
    """Hàm xác thực JWT Token dành riêng cho WebSocket"""
    try:
        payload = jwt.decode(token, settings.AUTH_JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
        if not token_data.sub:
            return None
        db = SessionLocal()
        user = user_repo.get(db, id=int(token_data.sub))
        db.close()
        return user
    except Exception:
        return None

@router.websocket("/ws/signaling/{client_id}")
async def websocket_signaling_endpoint(websocket: WebSocket, client_id: str, token: str = Query(None)):
    """
    Endpoint WebSocket xử lý việc trao đổi tín hiệu WebRTC.
    - Edge (Camera) có thể kết nối với ID dạng: "camera_01"
    - Web (Phụ huynh) có thể kết nối với ID dạng: "web_parent_01"
    """

    if not token or not verify_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            target_id = message.get("target")
            
            if target_id:
                message["sender"] = client_id
                
                # NẾU ĐÍCH LÀ CAMERA -> ĐẨY QUA MQTT
                if target_id.startswith("camera_"):
                    logger.info(f"Đẩy SDP Offer qua MQTT tới: {target_id}")
                    await mqtt_manager.publish(
                        topic=f"devices/{target_id}/webrtc/offer",
                        payload=message
                    )
                # NẾU ĐÍCH LÀ WEB APP KHÁC -> ĐẨY QUA WEBSOCKET
                else:
                    await manager.send_personal_message(message, target_id)
            else:
                logger.warning(f"Tin nhắn từ {client_id} không có 'target'.")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except json.JSONDecodeError:
        logger.error(f"Nhận được dữ liệu không phải JSON từ {client_id}")
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Lỗi WebSocket: {str(e)}")
        manager.disconnect(client_id)