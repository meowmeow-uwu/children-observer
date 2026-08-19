import asyncio
import json

from module_edge_firmware.mqtt_client import EdgeMqttClient


def _client(*, on_roi_update=None, on_webrtc_offer=None) -> EdgeMqttClient:
    return EdgeMqttClient(
        host="broker.test",
        port=1883,
        device_id="camera_01",
        on_roi_update=on_roi_update,
        on_webrtc_offer=on_webrtc_offer,
    )


def test_retained_roi_payload_is_forwarded_to_pipeline() -> None:
    received = []
    client = _client(on_roi_update=received.append)
    zones = [{"name": "Ban cong", "points": [{"x": 0.1, "y": 0.2}]}]

    asyncio.run(client._dispatch_message(client.roi_topic, json.dumps({"zones": zones}).encode()))

    assert received == [zones]
    assert client.roi_topic == "devices/camera_01/roi/update"


def test_offer_queues_answer_on_device_topic() -> None:
    async def create_answer(offer: dict) -> dict:
        return {"type": "answer", "target": offer["sender"], "sdp": "answer-sdp"}

    client = _client(on_webrtc_offer=create_answer)
    asyncio.run(
        client._dispatch_message(
            client.offer_topic,
            json.dumps({"sender": "web_parent_01", "type": "offer", "sdp": "offer-sdp"}).encode(),
        )
    )

    queued = client._outbox.get_nowait()
    assert queued.topic == "devices/camera_01/webrtc/answer"
    assert json.loads(queued.payload) == {
        "type": "answer",
        "target": "web_parent_01",
        "sdp": "answer-sdp",
    }


def test_alert_and_snapshot_use_separate_required_topics() -> None:
    client = _client()
    client.publish_alert_and_snapshot(
        camera_id="camera_01",
        title="Child entered danger zone",
        severity="danger",
        roi_name="Balcony",
        snapshot_jpeg=b"jpeg-bytes",
    )

    alert = client._outbox.get_nowait()
    snapshot = client._outbox.get_nowait()
    assert alert.topic == "devices/camera_01/alerts"
    alert_data = json.loads(alert.payload)
    assert alert_data["camera_id"] == "camera_01"
    assert alert_data["event_id"]
    assert snapshot.topic == f"devices/camera_01/snapshots/{alert_data['event_id']}"
    assert snapshot.payload == b"jpeg-bytes"


def test_camera_status_is_retained_on_device_topic() -> None:
    client = _client()

    assert client.publish_camera_status(online=False, reason="rtsp_unavailable") is True

    queued = client._outbox.get_nowait()
    assert queued.topic == "devices/camera_01/status"
    assert queued.retain is True
    assert json.loads(queued.payload) | {"timestamp_ms": 0} == {
        "camera_id": "camera_01",
        "online": False,
        "state": "offline",
        "reason": "rtsp_unavailable",
        "timestamp_ms": 0,
    }
