"""
Lightweight mobile communication gateway for the edge device.

Protocol: newline-delimited JSON over TCP.
Mobile can send: ping, status, update_roi, feedback, get_alerts.
Edge broadcasts alert events to connected clients.
"""

from __future__ import annotations

import json
import socketserver
import threading
from collections.abc import Callable
from typing import Any

from loguru import logger


GatewayHandler = Callable[[dict[str, Any]], dict[str, Any]]


class _GatewayTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _GatewayRequestHandler(socketserver.StreamRequestHandler):
    def setup(self) -> None:
        super().setup()
        self.server.gateway._add_client(self.request)

    def finish(self) -> None:
        try:
            self.server.gateway._remove_client(self.request)
        finally:
            super().finish()

    def handle(self) -> None:
        gateway: MobileGateway = self.server.gateway
        for raw_line in self.rfile:
            try:
                message = json.loads(raw_line.decode("utf-8"))
                response = gateway.handle_message(message)
            except json.JSONDecodeError as exc:
                response = {"ok": False, "error": f"invalid_json: {exc.msg}"}
            except Exception as exc:
                logger.exception(f"Mobile gateway request failed: {exc}")
                response = {"ok": False, "error": str(exc)}

            self.wfile.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
            self.wfile.flush()


class MobileGateway:
    """TCP gateway that lets the future mobile app control ROI and send feedback."""

    def __init__(self, host: str, port: int, request_handler: GatewayHandler):
        self.host = host
        self.port = port
        self._request_handler = request_handler
        self._server: _GatewayTCPServer | None = None
        self._thread: threading.Thread | None = None
        self._clients: set = set()
        self._clients_lock = threading.Lock()

    def start(self) -> None:
        if self._server is not None:
            logger.warning("MobileGateway is already running")
            return

        self._server = _GatewayTCPServer((self.host, self.port), _GatewayRequestHandler)
        self._server.gateway = self
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"Mobile gateway listening on {self.host}:{self.port}")

    def stop(self) -> None:
        if self._server is None:
            return

        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=3.0)
        self._server = None
        self._thread = None

        with self._clients_lock:
            self._clients.clear()
        logger.info("Mobile gateway stopped")

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(message, dict):
            return {"ok": False, "error": "message_must_be_object"}
        return self._request_handler(message)

    def broadcast(self, event_type: str, payload: dict[str, Any]) -> int:
        message = json.dumps(
            {"type": event_type, "ok": True, "payload": payload},
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"

        delivered = 0
        stale_clients = []
        with self._clients_lock:
            clients = list(self._clients)

        for client in clients:
            try:
                client.sendall(message)
                delivered += 1
            except OSError:
                stale_clients.append(client)

        for client in stale_clients:
            self._remove_client(client)

        if delivered:
            logger.debug(f"Broadcast {event_type} to {delivered} mobile client(s)")
        return delivered

    @property
    def client_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    @property
    def address(self) -> tuple[str, int]:
        if self._server is None:
            return (self.host, self.port)
        return self._server.server_address

    def _add_client(self, client) -> None:
        with self._clients_lock:
            self._clients.add(client)
        logger.info(f"Mobile client connected | clients={self.client_count}")

    def _remove_client(self, client) -> None:
        with self._clients_lock:
            self._clients.discard(client)
        logger.info(f"Mobile client disconnected | clients={self.client_count}")
