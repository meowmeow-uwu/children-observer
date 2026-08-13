import json
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Cấu hình logging cơ bản để dễ debug
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

@router.websocket("/ws/signaling/{client_id}")
async def websocket_signaling_endpoint(websocket: WebSocket, client_id: str):
    """
    Endpoint WebSocket xử lý việc trao đổi tín hiệu WebRTC.
    - Edge (Camera) có thể kết nối với ID dạng: "camera_01"
    - Web (Phụ huynh) có thể kết nối với ID dạng: "web_parent_01"
    """
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Lắng nghe tin nhắn từ client gửi lên dưới dạng văn bản (JSON string)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Tin nhắn chuẩn WebRTC Signaling cần có trường 'target_id' để biết gửi đi đâu
            target_id = message.get("target")
            
            if target_id:
                # Thêm thông tin người gửi vào bản tin để target biết đường phản hồi
                message["sender"] = client_id
                logger.info(f"Đang chuyển tiếp tín hiệu type='{message.get('type')}' từ {client_id} -> {target_id}")
                
                # Chuyển tiếp bản tin sang đích đến
                await manager.send_personal_message(message, target_id)
            else:
                logger.warning(f"Tin nhắn từ {client_id} không có trường 'target'. Bỏ qua.")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except json.JSONDecodeError:
        logger.error(f"Nhận được dữ liệu không phải JSON từ {client_id}")
    except Exception as e:
        logger.error(f"Lỗi không xác định với client {client_id}: {str(e)}")
        manager.disconnect(client_id)