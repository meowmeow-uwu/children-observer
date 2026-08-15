import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.signaling.server import router as signaling_router
from domains.auth.auth_controller import router as auth_router
from domains.cameras.camera_controller import router as cameras_router
from domains.alerts.alert_controller import router as alerts_router
from domains.devices.device_controller import router as devices_router
from domains.webrtc.webrtc_controller import router as webrtc_router

from infrastructure.mqtt.client import mqtt_manager
from infrastructure.mqtt.router import handle_mqtt_message

from fastapi.staticfiles import StaticFiles
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # Chạy vòng lặp lắng nghe MQTT như một Task chạy ngầm (Background Task)
    mqtt_task = asyncio.create_task(
        mqtt_manager.connect_and_listen(handle_mqtt_message)
    )
    yield
    # --- SHUTDOWN ---
    # Hủy tiến trình khi tắt server
    mqtt_task.cancel()

app = FastAPI(title="AI Child Guardian Backend API", lifespan=lifespan)

os.makedirs("data/snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="data/snapshots"), name="snapshots")

# 3. Cấu hình CORS cho phép Frontend truy cập API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nhúng Signaling Server & Restful API Router
app.include_router(signaling_router)
app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(alerts_router)
app.include_router(devices_router)
app.include_router(webrtc_router)

@app.get("/")
async def root():
    return {"message": "Hệ thống Modular Monolith & MQTT đã sẵn sàng."}