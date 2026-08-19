import sys
from pathlib import Path

# Đảm bảo Python nhận diện thư mục module_backend_infra làm root path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import cấu hình Database Engine & Base
from core.database import engine, Base

# Import đầy đủ Models của các Domain để SQLAlchemy quét thấy toàn bộ cấu trúc bảng
from domains.auth import auth_models
from domains.devices import device_models
from domains.cameras import camera_models
from domains.alerts import alert_models

# Khởi tạo toàn bộ bảng trong PostgreSQL nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

# Import Routers
from infrastructure.signaling.server import router as signaling_router
from domains.auth.auth_controller import router as auth_router
from domains.cameras.camera_controller import router as cameras_router
from domains.alerts.alert_controller import router as alerts_router
from domains.devices.device_controller import router as devices_router
from domains.webrtc.webrtc_controller import router as webrtc_router

# Import MQTT Manager
from infrastructure.mqtt.client import mqtt_manager
from infrastructure.mqtt.router import handle_mqtt_message


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    mqtt_task = asyncio.create_task(
        mqtt_manager.connect_and_listen(handle_mqtt_message)
    )
    yield
    # --- SHUTDOWN ---
    mqtt_task.cancel()


app = FastAPI(title="AI Child Guardian Backend API", lifespan=lifespan)

os.makedirs("data/snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="data/snapshots"), name="snapshots")

origins = [
    "https://children-observer.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

import sys
from pathlib import Path

# Đảm bảo Python nhận diện thư mục module_backend_infra làm root path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import cấu hình Database Engine & Base
from core.database import engine, Base

# Import đầy đủ Models của các Domain để SQLAlchemy quét thấy toàn bộ cấu trúc bảng
from domains.auth import auth_models
from domains.devices import device_models
from domains.cameras import camera_models
from domains.alerts import alert_models

# Khởi tạo toàn bộ bảng trong PostgreSQL nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

# Import Routers
from infrastructure.signaling.server import router as signaling_router
from domains.auth.auth_controller import router as auth_router
from domains.cameras.camera_controller import router as cameras_router
from domains.alerts.alert_controller import router as alerts_router
from domains.devices.device_controller import router as devices_router
from domains.webrtc.webrtc_controller import router as webrtc_router

# Import MQTT Manager
from infrastructure.mqtt.client import mqtt_manager
from infrastructure.mqtt.router import handle_mqtt_message


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    mqtt_task = asyncio.create_task(
        mqtt_manager.connect_and_listen(handle_mqtt_message)
    )
    yield
    # --- SHUTDOWN ---
    mqtt_task.cancel()


app = FastAPI(title="AI Child Guardian Backend API", lifespan=lifespan)

os.makedirs("data/snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="data/snapshots"), name="snapshots")

origins = [
    "https://children-observer.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://children-observer.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=600,
)

# Nhúng Routers
app.include_router(signaling_router)
app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(alerts_router)
app.include_router(devices_router)
app.include_router(webrtc_router)


@app.get("/")
async def root():
    return {"message": "Hệ thống Modular Monolith & MQTT đã sẵn sàng."}

# Nhúng Routers
app.include_router(signaling_router)
app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(alerts_router)
app.include_router(devices_router)
app.include_router(webrtc_router)


@app.get("/")
async def root():
    return {"message": "Hệ thống Modular Monolith & MQTT đã sẵn sàng."}