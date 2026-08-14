"""FastAPI entrypoint for the authenticated modular-domain backend.

The localhost Child Observer demo keeps its compatibility API in ``main.py``.
This app exposes the newer auth/device/MQTT domain contracts without registering
duplicate camera and alert routes on the demo app.
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from domains.alerts.alert_controller import router as alerts_router
from domains.auth.auth_controller import router as auth_router
from domains.cameras.camera_controller import router as cameras_router
from domains.devices.device_controller import router as devices_router
from domains.webrtc.webrtc_controller import router as webrtc_router
from infrastructure.mqtt.client import mqtt_manager
from infrastructure.mqtt.router import handle_mqtt_message
from infrastructure.signaling.server import router as signaling_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    mqtt_task = asyncio.create_task(mqtt_manager.connect_and_listen(handle_mqtt_message))
    yield
    mqtt_task.cancel()


app = FastAPI(title="AI Child Guardian Domain API", lifespan=lifespan)

os.makedirs("data/snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="data/snapshots"), name="snapshots")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signaling_router)
app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(alerts_router)
app.include_router(devices_router)
app.include_router(webrtc_router)


@app.get("/")
async def root():
    return {"message": "Hệ thống Modular Monolith & MQTT đã sẵn sàng."}
