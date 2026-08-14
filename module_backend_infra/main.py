import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from module_backend_infra.api_router import router as api_router
from module_backend_infra.database import models
from module_backend_infra.database.config import Base, SessionLocal, engine, upgrade_schema
from module_backend_infra.detection_ws import router as detection_router
from module_backend_infra.snapshot_store import SNAPSHOT_DIR
from module_backend_infra.signaling.server import router as signaling_router
from module_backend_infra.video_analysis_service import get_detection_hub

# 1. Tự động tạo các bảng trong Database nếu chưa có + migration cột mới
Base.metadata.create_all(bind=engine)
upgrade_schema()


# 2. Khởi tạo dữ liệu mẫu (Seed Data) nếu Database đang rỗng
def init_seed_data():
    db = SessionLocal()
    try:
        if db.query(models.Camera).count() == 0:
            cam1 = models.Camera(
                camera_id_string="camera_living_room_01",
                name="Phòng khách",
                location="Tầng 1 - Khu vực chính",
                status="online",
            )
            cam2 = models.Camera(
                camera_id_string="camera_balcony_02",
                name="Ban công",
                location="Tầng 2 - Ngoài trời",
                status="online",
            )
            cam3 = models.Camera(
                camera_id_string="camera_kitchen_03",
                name="Nhà bếp",
                location="Tầng 1 - Khu vực bếp",
                status="online",
            )
            cam4 = models.Camera(
                camera_id_string="camera_stairs_04",
                name="Cầu thang",
                location="Tầng 1 - Nối tầng 2",
                status="offline",
            )
            db.add_all([cam1, cam2, cam3, cam4])
            db.commit()

            # Seed dữ liệu ROI mẫu cho camera phòng khách — giao với đường đi
            # thật của trẻ trong đoạn demo [10s, 22.6s]: trẻ xuất hiện lần 2
            # (~19.6s) với track mới ngay trong zone → enter alert xác thực mỗi loop.
            roi1 = models.ROIZone(
                camera_id="camera_living_room_01",
                name="Khu vực nguy hiểm",
                type="rectangle",
                points=json.dumps(
                    [
                        {"x": 0.35, "y": 0.5},
                        {"x": 0.55, "y": 0.5},
                        {"x": 0.55, "y": 0.8},
                        {"x": 0.35, "y": 0.8},
                    ]
                ),
                sensitivity="high",
                enabled=True,
                rules=json.dumps(
                    {
                        "enterZone": True,
                        "stayTooLong": False,
                        "stayDurationSeconds": 5,
                        "approachZone": False,
                    }
                ),
            )
            db.add(roi1)
            db.commit()
    finally:
        db.close()


init_seed_data()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle cho FastAPI app.

    Backend chỉ relay signaling/WebSocket — KHÔNG load model AI, KHÔNG đọc video.
    Tiến trình Edge là nơi duy nhất sở hữu VideoCapture, ONNX session và ByteTrack.
    """
    # Ghi nhận event loop cho DetectionHub (relay từ Edge → browser)
    get_detection_hub().bind_loop(asyncio.get_running_loop())

    yield


app = FastAPI(title="AI Child Guardian Backend API", lifespan=lifespan)

# 3. Cấu hình CORS cho phép Frontend truy cập API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Nhúng Signaling Server & Restful API Router & Detection WS
app.include_router(signaling_router)
app.include_router(api_router)
app.include_router(detection_router)
app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOT_DIR)), name="alert-snapshots")


@app.get("/")
async def root():
    return {
        "message": "Backend API đang hoạt động. Signaling Server sẵn sàng. Detection relay active."
    }
