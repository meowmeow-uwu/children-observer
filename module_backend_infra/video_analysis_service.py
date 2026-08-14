"""
Detection Relay Hub.

Backend KHÔNG chạy model AI hay đọc video nữa. Hub chỉ làm nhiệm vụ relay:

    Edge (tiến trình duy nhất đọc video + chạy ONNX + ByteTrack)
        └── /ws/detections/edge ──► DetectionHub ──► /ws/detections (browser)

- Message từ Edge (detections / status / heartbeat) được fan-out tới mọi
  browser client đang kết nối.
- Message từ browser (update_roi_zones) được relay tới Edge để đồng bộ nhanh;
  nguồn dữ liệu bền vững vẫn là REST (POST /api/cameras/{id}/roi).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

from loguru import logger


class DetectionHub:
    """In-memory relay giữa các Edge device và browser clients."""

    def __init__(self) -> None:
        self._edge_clients: set[Any] = set()
        self._browser_clients: set[Any] = set()
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_message_at = 0.0
        self._edge_online = False

    # ---- Lifecycle ----
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Ghi nhận event loop để gửi message từ các thread ngoài."""
        self._loop = loop

    @property
    def edge_online(self) -> bool:
        with self._lock:
            return self._edge_online

    @property
    def browser_count(self) -> int:
        with self._lock:
            return len(self._browser_clients)

    def register_edge(self, ws) -> None:
        with self._lock:
            self._edge_clients.add(ws)
            self._edge_online = True
            self._last_message_at = time.time()
        logger.info(f"Detection hub: edge connected (total {len(self._edge_clients)})")

    def register_browser(self, ws) -> None:
        with self._lock:
            self._browser_clients.add(ws)
        logger.info(f"Detection hub: browser connected (total {len(self._browser_clients)})")

    def unregister(self, ws) -> None:
        with self._lock:
            self._edge_clients.discard(ws)
            self._browser_clients.discard(ws)
            self._edge_online = len(self._edge_clients) > 0
        logger.info(
            "Detection hub: client disconnected "
            f"(edge={len(self._edge_clients)}, browser={len(self._browser_clients)})"
        )

    # ---- Relay paths ----
    def relay_edge_message(self, message: dict) -> None:
        """Edge → browser. Message phải là dict JSON-safe."""
        with self._lock:
            clients = list(self._browser_clients)
            self._last_message_at = time.time()
        self._broadcast(message, clients)

    def relay_browser_message(self, ws, message: dict) -> None:
        """Browser → Edge (ví dụ update_roi_zones)."""
        with self._lock:
            edges = list(self._edge_clients)
        self._broadcast(message, edges, exclude=ws)

    def _broadcast(self, message: dict, clients: list, exclude=None) -> None:
        if not clients:
            return
        if self._loop is None:
            return
        try:
            data = json.dumps(message)
        except (TypeError, ValueError) as exc:
            logger.warning(f"Detection hub: message not JSON serializable ({exc}) — dropped")
            return

        async def _send():
            dead = []
            for ws in clients:
                if ws is exclude:
                    continue
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.unregister(ws)

        try:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except RuntimeError:
            logger.warning("Detection hub: event loop unavailable, broadcast dropped")


# Singleton instance
_hub: DetectionHub | None = None


def get_detection_hub() -> DetectionHub:
    """Lazy singleton cho DetectionHub."""
    global _hub
    if _hub is None:
        _hub = DetectionHub()
    return _hub
