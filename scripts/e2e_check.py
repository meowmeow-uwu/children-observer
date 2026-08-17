"""Smoke test cho Docker demo: API, MQTT ROI va alert/snapshot.

Chay sau `docker compose up --build -d`:
    uv run python scripts/e2e_check.py
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
import uuid

import aiomqtt


BASE_URL = "http://127.0.0.1:8007"
MQTT_HOST = "127.0.0.1"
CAMERA_ID = "camera_living_room_01"
DEMO_EMAIL = "demo@childrenobserver.org"
DEMO_PASSWORD = "demo12345"


def request(path: str, *, method: str = "GET", body: object | None = None, token: str | None = None) -> object:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


def wait_for_backend() -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if request("/healthz") == {"status": "ok"}:
                return
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    raise RuntimeError("Backend is not healthy at http://127.0.0.1:8007/healthz")


async def mqtt_contract_check(token: str) -> None:
    roi_topic = f"devices/{CAMERA_ID}/roi/update"
    event_id = f"e2e-{uuid.uuid4().hex}"
    alert = {
        "event_id": event_id,
        "camera_id": CAMERA_ID,
        "camera_name": "Living Room Demo",
        "title": "E2E MQTT alert",
        "severity": "warning",
        "roi_name": "play_area",
        "notes": "mqtt contract check",
        "snapshot_url": f"{event_id}.jpg",
    }
    zones = [{
        "name": "play_area",
        "type": "polygon",
        "points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}],
        "sensitivity": "high",
        "enabled": True,
        "rules": {"enterZone": True},
    }]

    async with aiomqtt.Client(hostname=MQTT_HOST, port=1883) as client:
        await client.subscribe(roi_topic)
        await asyncio.to_thread(request, f"/api/cameras/{CAMERA_ID}/roi", method="POST", body=zones, token=token)
        async with asyncio.timeout(10):
            async for message in client.messages:
                if message.topic.value == roi_topic:
                    payload = json.loads(message.payload.decode())
                    # The broker can deliver an older retained message first.
                    # Keep waiting for the update just submitted through the API.
                    if not payload.get("zones") or not payload["zones"][0].get("id"):
                        continue
                    assert payload["camera_id"] == CAMERA_ID
                    assert payload["zones"][0]["rules"]["enterZone"] is True
                    break

        await client.publish(f"devices/{CAMERA_ID}/alerts", json.dumps(alert))
        await client.publish(f"devices/{CAMERA_ID}/snapshots/{event_id}", b"\xff\xd8\xff\xd9")

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        alerts = await asyncio.to_thread(request, f"/api/alerts/?camera_id={CAMERA_ID}&limit=100", token=token)
        matched = next((item for item in alerts if item.get("event_id") == event_id), None)
        if matched:
            assert matched["snapshot_url"].endswith(f"/{event_id}.jpg")
            return
        await asyncio.sleep(0.5)
    raise AssertionError("Backend did not persist the MQTT alert")


def main() -> int:
    # aiomqtt uses add_reader/add_writer, which the Windows Proactor loop does
    # not implement. Docker/Linux deployments do not need this branch.
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        wait_for_backend()
        login = request("/api/auth/login", method="POST", body={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        token = login["access_token"]
        cameras = request("/api/cameras/", token=token)
        camera = next(item for item in cameras if item["camera_id_string"] == CAMERA_ID)
        assert camera["roi_zones"], "Demo camera has no ROI"
        asyncio.run(mqtt_contract_check(token))
    except Exception as error:
        print(f"E2E FAIL: {error}")
        return 1
    print("E2E PASS: auth, camera/ROI API, retained ROI MQTT, alert and snapshot MQTT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
