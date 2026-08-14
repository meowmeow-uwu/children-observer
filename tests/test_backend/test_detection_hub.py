"""
Tests cho DetectionHub relay — backend không chạy model, chỉ relay Edge → browser.
"""

import asyncio

import pytest

from module_backend_infra.video_analysis_service import DetectionHub


class FakeWS:
    def __init__(self):
        self.sent: list[str] = []
        self.closed = False

    async def send_text(self, data: str):
        self.sent.append(data)

    async def receive_text(self):
        await asyncio.sleep(60)


@pytest.mark.asyncio
async def test_relay_edge_message_to_browsers():
    hub = DetectionHub()
    hub.bind_loop(asyncio.get_running_loop())
    browser = FakeWS()
    hub.register_browser(browser)

    hub.relay_edge_message(
        {
            "type": "tracks",
            "camera_id": "camera_living_room_01",
            "frame_id": 10,
            "tracks": [
                {"track_id": 1, "class": "child", "confidence": 0.5, "box": [0.1, 0.1, 0.3, 0.4]}
            ],
        }
    )
    await asyncio.sleep(0.05)

    assert len(browser.sent) == 1
    import json

    msg = json.loads(browser.sent[0])
    assert msg["type"] == "tracks"
    assert msg["camera_id"] == "camera_living_room_01"


@pytest.mark.asyncio
async def test_relay_drops_non_json_safe_message():
    import numpy as np

    hub = DetectionHub()
    hub.bind_loop(asyncio.get_running_loop())
    browser = FakeWS()
    hub.register_browser(browser)

    # numpy.float32 trong message — phải bị drop chứ không crash thread
    hub.relay_edge_message({"type": "tracks", "bad": np.float32(0.5)})
    await asyncio.sleep(0.05)

    assert browser.sent == []
    assert hub.browser_count == 1


@pytest.mark.asyncio
async def test_edge_online_flag_and_unregister():
    hub = DetectionHub()
    hub.bind_loop(asyncio.get_running_loop())
    edge = FakeWS()
    hub.register_edge(edge)
    assert hub.edge_online is True

    hub.unregister(edge)
    assert hub.edge_online is False


@pytest.mark.asyncio
async def test_unregister_removes_dead_browser_after_send_failure():
    class BrokenWS(FakeWS):
        async def send_text(self, data: str):
            raise ConnectionError("gone")

    hub = DetectionHub()
    hub.bind_loop(asyncio.get_running_loop())
    broken = BrokenWS()
    hub.register_browser(broken)
    hub.relay_edge_message({"type": "status", "state": "tracking"})
    await asyncio.sleep(0.05)
    assert hub.browser_count == 0
