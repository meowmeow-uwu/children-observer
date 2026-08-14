"""
Detection WebSocket endpoints — relay hub (không chạy model).

- /ws/detections       : browser clients nhận detection frames từ Edge.
- /ws/detections/edge  : Edge device bơm detection/status frames vào.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from module_backend_infra.video_analysis_service import get_detection_hub

router = APIRouter()

EDGE_MESSAGE_TYPES = {
    "detections",
    "tracks",
    "status",
    "heartbeat",
    "stream_sync",
    "roi_zones_updated",
}


def _parse_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        logger.warning("Detection WS: invalid JSON received")
        return None


@router.websocket("/ws/detections")
async def detection_ws_endpoint(websocket: WebSocket):
    """Browser endpoint: nhận detection frames, gửi ROI zone updates."""
    await websocket.accept()
    hub = get_detection_hub()
    hub.register_browser(websocket)

    try:
        await websocket.send_json(
            {
                "type": "status",
                "state": "tracking" if hub.edge_online else "offline",
            }
        )
        while True:
            data = _parse_json(await websocket.receive_text())
            if not data:
                continue
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "update_roi_zones":
                zones = data.get("zones", [])
                hub.relay_browser_message(websocket, {"type": "update_roi_zones", "zones": zones})
                await websocket.send_json({"type": "roi_zones_updated", "count": len(zones)})
            else:
                logger.debug(f"Detection WS (browser): unknown message type: {msg_type}")

    except WebSocketDisconnect:
        hub.unregister(websocket)
    except Exception as exc:
        logger.error(f"Detection WS (browser) error: {exc}")
        hub.unregister(websocket)


@router.websocket("/ws/detections/edge")
async def detection_ws_edge_endpoint(websocket: WebSocket):
    """Edge endpoint: bơm detection/status frames để relay tới browsers."""
    await websocket.accept()
    hub = get_detection_hub()
    hub.register_edge(websocket)

    try:
        await websocket.send_json({"type": "edge_registered"})
        while True:
            data = _parse_json(await websocket.receive_text())
            if not data:
                continue
            msg_type = data.get("type")

            if msg_type in EDGE_MESSAGE_TYPES:
                hub.relay_edge_message(data)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                logger.debug(f"Detection WS (edge): unknown message type: {msg_type}")

    except WebSocketDisconnect:
        hub.unregister(websocket)
    except Exception as exc:
        logger.error(f"Detection WS (edge) error: {exc}")
        hub.unregister(websocket)
