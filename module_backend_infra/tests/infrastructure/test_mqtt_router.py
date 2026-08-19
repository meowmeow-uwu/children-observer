# tests/infrastructure/test_mqtt_router.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from infrastructure.mqtt.router import handle_mqtt_message

# Tạo cấu trúc giả lập (Mock) cho tin nhắn aiomqtt
class MockTopic:
    def __init__(self, value):
        self.value = value

class MockMessage:
    def __init__(self, topic_string, payload_bytes):
        self.topic = MockTopic(topic_string)
        self.payload = payload_bytes

@pytest.mark.asyncio
@patch("infrastructure.mqtt.router._process_alert", new_callable=AsyncMock)
async def test_mqtt_route_to_alert(mock_process_alert):
    """Test bộ định tuyến chuyển hướng đúng tin nhắn Alert."""
    fake_payload = json.dumps({"title": "Test Alert"}).encode('utf-8')
    msg = MockMessage("devices/cam_01/alerts", fake_payload)
    
    await handle_mqtt_message(msg)
    
    # Đảm bảo hàm _process_alert được gọi với đúng payload
    mock_process_alert.assert_called_once_with(fake_payload)

@pytest.mark.asyncio
@patch("infrastructure.mqtt.router._process_snapshot", new_callable=AsyncMock)
async def test_mqtt_route_to_snapshot(mock_process_snapshot):
    """Test bộ định tuyến chuyển hướng đúng mảng byte Snapshot."""
    fake_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" # Fake JPEG header
    msg = MockMessage("devices/mac_123/snapshots", fake_image_bytes)
    
    await handle_mqtt_message(msg)
    
    # Đảm bảo hàm xử lý ảnh được gọi và bóc tách đúng device_id
    mock_process_snapshot.assert_called_once_with("mac_123", fake_image_bytes, None)

@pytest.mark.asyncio
@patch("infrastructure.mqtt.router.manager.send_personal_message", new_callable=AsyncMock)
async def test_mqtt_route_to_webrtc_answer(mock_send_ws):
    """Test bộ định tuyến chuyển SDP Answer từ Pi lên WebSocket Web App."""
    fake_sdp = {
        "type": "answer",
        "sdp": "v=0\r\no=...",
        "target": "web_parent_01"
    }
    msg = MockMessage("devices/cam_01/webrtc/answer", json.dumps(fake_sdp).encode('utf-8'))
    
    await handle_mqtt_message(msg)
    
    # Đảm bảo lệnh đẩy WebSocket tới Web App được gọi
    mock_send_ws.assert_called_once_with(fake_sdp, "web_parent_01")


@pytest.mark.asyncio
@patch("infrastructure.mqtt.router._process_camera_status", new_callable=AsyncMock)
async def test_mqtt_route_to_camera_status(mock_process_status):
    payload = json.dumps({"online": False, "reason": "rtsp_unavailable"}).encode()
    msg = MockMessage("devices/camera_01/status", payload)

    await handle_mqtt_message(msg)

    mock_process_status.assert_called_once_with("camera_01", payload)
