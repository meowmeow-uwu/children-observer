"""MQTT transport for the production Edge firmware.

The Edge owns one long-lived MQTT connection.  It receives retained ROI
configuration and WebRTC offers, then publishes SDP answers, alert metadata,
and raw JPEG snapshots using the topics specified in the edge integration task.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import aiomqtt
from loguru import logger


@dataclass(frozen=True)
class MqttMessage:
    topic: str
    payload: bytes
    retain: bool = False


class EdgeMqttClient:
    """Thread-owned asyncio MQTT client with a thread-safe publish outbox."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        device_id: str,
        username: str | None = None,
        password: str | None = None,
        on_roi_update: Callable[[list[dict[str, Any]]], None] | None = None,
        on_webrtc_offer: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.device_id = device_id
        self.username = username or None
        self.password = password or None
        self.on_roi_update = on_roi_update
        self.on_webrtc_offer = on_webrtc_offer

        self._outbox: queue.Queue[MqttMessage] = queue.Queue(maxsize=128)
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def roi_topic(self) -> str:
        return f"devices/{self.device_id}/roi/update"

    @property
    def offer_topic(self) -> str:
        return f"devices/{self.device_id}/webrtc/offer"

    @property
    def answer_topic(self) -> str:
        return f"devices/{self.device_id}/webrtc/answer"

    @property
    def alerts_topic(self) -> str:
        return f"devices/{self.device_id}/alerts"

    @property
    def snapshots_topic(self) -> str:
        return f"devices/{self.device_id}/snapshots"

    @property
    def status_topic(self) -> str:
        return f"devices/{self.device_id}/status"

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_thread, name="edge-mqtt", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._connected.clear()
        if self._thread:
            self._thread.join(timeout=5)

    def publish_json(self, topic: str, payload: dict[str, Any], *, retain: bool = False) -> bool:
        return self._enqueue(MqttMessage(topic, json.dumps(payload).encode("utf-8"), retain))

    def publish_bytes(self, topic: str, payload: bytes, *, retain: bool = False) -> bool:
        return self._enqueue(MqttMessage(topic, payload, retain))

    def publish_camera_status(self, *, online: bool, reason: str) -> bool:
        """Publish the current RTSP availability as retained device state."""
        return self.publish_json(
            self.status_topic,
            {
                "camera_id": self.device_id,
                "online": online,
                "state": "online" if online else "offline",
                "reason": reason,
                "timestamp_ms": int(time.time() * 1000),
            },
            retain=True,
        )

    def _enqueue(self, message: MqttMessage) -> bool:
        try:
            self._outbox.put_nowait(message)
            return True
        except queue.Full:
            logger.error("MQTT outbox is full; dropping message for {}", message.topic)
            return False

    def _run_thread(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                async with aiomqtt.Client(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    identifier=f"edge-{self.device_id}",
                ) as client:
                    await client.subscribe(self.roi_topic, qos=1)
                    await client.subscribe(self.offer_topic, qos=1)
                    self._connected.set()
                    logger.info("MQTT connected: {}:{} (device={})", self.host, self.port, self.device_id)
                    await self._serve(client)
            except aiomqtt.MqttError as exc:
                logger.warning("MQTT connection failed: {}", exc)
            except Exception as exc:
                logger.exception("Unexpected MQTT client error: {}", exc)
            finally:
                self._connected.clear()
            if not self._stop.is_set():
                await asyncio.sleep(3)

    async def _serve(self, client: aiomqtt.Client) -> None:
        listener = asyncio.create_task(self._listen(client))
        publisher = asyncio.create_task(self._publish_loop(client))
        done, pending = await asyncio.wait(
            {listener, publisher}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc:
                raise exc

    async def _listen(self, client: aiomqtt.Client) -> None:
        async for message in client.messages:
            if self._stop.is_set():
                return
            await self._dispatch_message(str(message.topic.value), bytes(message.payload))

    async def _publish_loop(self, client: aiomqtt.Client) -> None:
        while not self._stop.is_set():
            try:
                message = await asyncio.to_thread(self._outbox.get, True, 0.5)
            except queue.Empty:
                continue
            await client.publish(message.topic, payload=message.payload, qos=1, retain=message.retain)

    async def _dispatch_message(self, topic: str, payload: bytes) -> None:
        """Dispatch one broker message; kept separate for deterministic tests."""
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Ignoring invalid JSON on MQTT topic {}", topic)
            return

        if topic == self.roi_topic:
            zones = data.get("zones", data) if isinstance(data, dict) else data
            if not isinstance(zones, list):
                logger.warning("Ignoring ROI update without a zones list")
                return
            if self.on_roi_update:
                self.on_roi_update(zones)
            logger.info("Applied {} ROI zones from MQTT", len(zones))
            return

        if topic == self.offer_topic:
            if not self.on_webrtc_offer:
                logger.warning("Ignoring WebRTC offer: no handler configured")
                return
            try:
                answer = await self.on_webrtc_offer(data)
                self.publish_json(self.answer_topic, answer)
                logger.info("Queued WebRTC answer for {}", data.get("sender", "unknown"))
            except Exception as exc:
                logger.warning("Could not handle WebRTC offer: {}", exc)

    def publish_alert_and_snapshot(
        self,
        *,
        camera_id: str,
        title: str,
        severity: str,
        roi_name: str,
        snapshot_jpeg: bytes | None,
        notes: str = "",
    ) -> None:
        """Queue the two task-mandated alert messages without blocking AI inference."""
        timestamp_ms = int(time.time() * 1000)
        event_id = f"evt-{self.device_id}-{timestamp_ms}"
        snapshot_name = f"{event_id}.jpg"
        self.publish_json(
            self.alerts_topic,
            {
                "event_id": event_id,
                "camera_id": camera_id,
                "title": title,
                "severity": severity,
                "snapshot_url": snapshot_name,
                "roi_name": roi_name,
                "notes": notes,
            },
        )
        if snapshot_jpeg:
            self.publish_bytes(f"{self.snapshots_topic}/{event_id}", snapshot_jpeg)
