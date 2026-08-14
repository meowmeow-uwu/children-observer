# tests/infrastructure/test_signaling.py
import pytest
from unittest.mock import AsyncMock, patch

@patch("infrastructure.signaling.server.verify_ws_token", return_value=True)
@patch("infrastructure.signaling.server.mqtt_manager.publish", new_callable=AsyncMock)
def test_websocket_signaling_offer_to_camera(mock_publish, mock_verify, client):
    """
    Kịch bản: Web App (Phụ huynh) mở WebSocket và gửi SDP Offer tới Camera.
    Kỳ vọng: Signaling Server bóc tách gói tin và đẩy qua MQTT cho Camera.
    """
    # 1. Mở kết nối WebSocket với danh tính là 'web_parent_01' và JWT Token
    with client.websocket_connect("/ws/signaling/web_parent_01?token=mock_token") as websocket:
        
        # 2. Gói tin SDP Offer cần truyền P2P
        offer_payload = {
            "type": "offer",
            "target": "camera_01", # Target bắt đầu bằng 'camera_'
            "sdp": "v=0\r\no=parent_sdp_data..."
        }
        
        # Bắn qua luồng WebSocket
        websocket.send_json(offer_payload)
        
    # 3. Assert (Kiểm chứng)
    # Vì Server nhận được 'target' là 'camera_01', nó PHẢI gọi hàm MQTT Publish
    assert mock_publish.called
    assert mock_publish.call_count == 1
    
    # Lấy thông số (Arguments) mà hàm publish vừa được gọi để kiểm tra
    call_args = mock_publish.call_args.kwargs
    
    # Topic phải định tuyến chính xác tới camera_01
    assert call_args["topic"] == "devices/camera_01/webrtc/offer"
    
    # Payload phải tự động được bổ sung trường "sender"
    assert call_args["payload"]["sender"] == "web_parent_01"
    assert call_args["payload"]["type"] == "offer"