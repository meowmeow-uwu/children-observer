"""
BackendSync — Edge đồng bộ cấu hình từ Backend REST + đẩy alert lên.

- Poll GET /api/cameras/{id} (alerts_paused) + GET /api/cameras/{id}/roi
  mỗi poll_interval giây; áp dụng trực tiếp vào RoiStateEngine.
- POST /api/alerts cho mỗi AlertEvent (bỏ qua khi camera đang paused).
- Chịu lỗi mạng: giữ cấu hình cuối cùng, retry sau mỗi poll.
"""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.error
import urllib.request
from typing import Callable

from loguru import logger

from module_edge_firmware.demo_stream.roi_engine import AlertEvent


class BackendSync:
    def __init__(
        self,
        backend_url: str,
        camera_id: str,
        poll_interval: float = 5.0,
        on_roi_update: Callable[[list[dict]], None] | None = None,
        on_pause_change: Callable[[bool], None] | None = None,
        on_camera_meta: Callable[[str], None] | None = None,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.camera_id = camera_id
        self.poll_interval = poll_interval
        self.on_roi_update = on_roi_update
        self.on_pause_change = on_pause_change
        self.on_camera_meta = on_camera_meta
        self.camera_name = ""

        self._running = False
        self._thread: threading.Thread | None = None
        self._last_poll_ok = False

    # ---- Lifecycle ----
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, name="backend-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    # ---- Polling ----
    def _poll_loop(self) -> None:
        while self._running:
            try:
                self.poll_once()
            except Exception as exc:
                logger.warning(f"BackendSync poll error: {exc}")
            for _ in range(int(max(1.0, self.poll_interval))):
                if not self._running:
                    return
                time.sleep(1.0)

    def poll_once(self) -> None:
        camera = self._fetch(f"/api/cameras/{self.camera_id}")
        if camera:
            self._last_poll_ok = True
            paused = bool(camera.get("alerts_paused", False))
            if self.on_pause_change:
                self.on_pause_change(paused)

            name = camera.get("name") or ""
            if name and name != self.camera_name:
                self.camera_name = name
                if self.on_camera_meta:
                    self.on_camera_meta(name)

            zones = camera.get("roi_zones") or []
            if self.on_roi_update:
                self.on_roi_update(zones)
        elif not self._last_poll_ok:
            logger.warning(f"BackendSync: camera {self.camera_id} chưa sẵn sàng trên backend")

    def _fetch(self, path: str) -> dict | list | None:
        url = f"{self.backend_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            logger.debug(f"BackendSync fetch {url} failed: {exc}")
        return None

    # ---- Alert posting ----
    def post_alert(self, alert: AlertEvent, snapshot_jpeg: bytes | None = None) -> bool:
        payload = json.dumps(
            {
                "camera_id": alert.camera_id,
                "camera_name": self.camera_name,
                "title": f"{alert.title} ({alert.zone_name})",
                "severity": "danger" if alert.rule == "enterZone" else "warning",
                "status": "unread",
                "snapshot_url": "",
                "snapshot_base64": (
                    base64.b64encode(snapshot_jpeg).decode("ascii")
                    if snapshot_jpeg else None
                ),
                "roi_name": alert.zone_name,
                "notes": json.dumps(
                    {
                        "rule": alert.rule,
                        "track_id": alert.track_id,
                        "confidence": alert.confidence,
                        "box": alert.box,
                        "at_ms": alert.at_ms,
                    }
                ),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.backend_url}/api/alerts",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                ok = resp.status == 200
                logger.info(
                    f"Alert posted [{alert.rule}] zone={alert.zone_name} "
                    f"track={alert.track_id} -> {ok}"
                )
                return ok
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            logger.warning(f"Alert post failed: {exc}")
            return False

    def post_fall_alert(self, alert, snapshot_jpeg: bytes | None = None) -> bool:
        """Post a fall event through REST when MQTT is unavailable.

        FallAlert deliberately has no ROI rule, zone name, or bounding-box fields,
        so it cannot use the ROI-specific ``post_alert`` serializer above.
        """
        payload = json.dumps(
            {
                "camera_id": alert.camera_id,
                "camera_name": self.camera_name,
                "title": alert.title,
                "severity": alert.severity,
                "status": "unread",
                "snapshot_url": "",
                "snapshot_base64": (
                    base64.b64encode(snapshot_jpeg).decode("ascii")
                    if snapshot_jpeg else None
                ),
                "roi_name": alert.roi_name,
                "notes": alert.notes,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.backend_url}/api/alerts",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                ok = resp.status == 200
                logger.info(f"Fall alert posted track={alert.track_id} -> {ok}")
                return ok
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            logger.warning(f"Fall alert post failed: {exc}")
            return False
