"""Create idempotent local-demo data after Alembic migrations have run."""

from __future__ import annotations

import asyncio
import json
import os

import aiomqtt
from core.database import SessionLocal
from core.security import hash_password
from domains.auth.auth_models import User
from domains.devices.device_models import Device
from domains.cameras.camera_models import Camera, ROIZone
# Import registers the class used by Camera.alerts before SQLAlchemy configures
# mappers for the first query.
from domains.alerts.alert_models import Alert  # noqa: F401

DEMO_EMAIL = "demo@childrenobserver.org"
DEMO_PASSWORD = "demo12345"
CAMERA_ID = "camera_living_room_01"


def seed_demo() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            user = User(
                email=DEMO_EMAIL,
                full_name="Demo Parent",
                password_hash=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            db.flush()

        device = db.query(Device).filter(Device.mac_address == "02:00:00:00:00:01").first()
        if not device:
            device = Device(
                user_id=user.id,
                mac_address="02:00:00:00:00:01",
                name="Demo Raspberry Pi",
                device_secret_key="demo-device-secret",
                status="ONLINE",
            )
            db.add(device)
            db.flush()
        elif device.user_id != user.id:
            # A previous demo seed may have used a different email; keep the
            # deterministic demo device accessible to the current demo user.
            device.user_id = user.id

        camera = db.query(Camera).filter(Camera.camera_id_string == CAMERA_ID).first()
        if not camera:
            camera = Camera(
                camera_id_string=CAMERA_ID,
                device_id=device.id,
                name="Camera Phòng khách",
                location="Phòng khách",
                rtsp_url="demo://module_edge_firmware/test_video.mp4",
                status="online",
            )
            db.add(camera)
            db.flush()

        if not db.query(ROIZone).filter(ROIZone.camera_id == camera.id).first():
            db.add(
                ROIZone(
                    camera_id=camera.id,
                    name="Khu vực nguy hiểm demo",
                    zone_type="polygon",
                    polygon_points=[
                        {"x": 0.35, "y": 0.25},
                        {"x": 0.75, "y": 0.25},
                        {"x": 0.75, "y": 0.95},
                        {"x": 0.35, "y": 0.95},
                    ],
                    sensitivity="high",
                    enabled=True,
                    rules={"enterZone": True, "stayTooLong": False, "stayDurationSeconds": 5, "approachZone": False},
                )
            )
        db.commit()
        zones = db.query(ROIZone).filter(ROIZone.camera_id == camera.id).all()
        roi_payload = {
            "camera_id": CAMERA_ID,
            "zones": [
                {
                    "id": zone.id,
                    "name": zone.name,
                    "type": zone.zone_type,
                    "points": zone.polygon_points,
                    "sensitivity": zone.sensitivity,
                    "enabled": zone.enabled,
                    "rules": zone.rules,
                }
                for zone in zones
            ],
        }
        if os.getenv("SEED_PUBLISH_MQTT", "false").lower() == "true":
            asyncio.run(publish_seed_roi(roi_payload))
        print(f"Demo data ready. Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    finally:
        db.close()


async def publish_seed_roi(payload: dict) -> None:
    """Publish initial retained ROI so a freshly started edge is configured."""
    host = os.getenv("MQTT_BROKER_HOST", "mqtt")
    port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    topic = f"devices/{CAMERA_ID}/roi/update"
    async with aiomqtt.Client(hostname=host, port=port) as client:
        await client.publish(topic, json.dumps(payload), qos=1, retain=True)
    print(f"Published retained demo ROI: {topic}")


if __name__ == "__main__":
    seed_demo()
