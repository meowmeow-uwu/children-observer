import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from module_backend_infra.signaling.server import router as signaling_router
from module_backend_infra.api_router import router as api_router
from module_backend_infra.database.config import engine, Base, SessionLocal
from module_backend_infra.database import models

# 1. Tự động tạo các bảng trong Database nếu chưa có
Base.metadata.create_all(bind=engine)

# 2. Khởi tạo dữ liệu mẫu (Seed Data) nếu Database đang rỗng
def init_seed_data():
    db = SessionLocal()
    try:
        if db.query(models.Camera).count() == 0:
            cam1 = models.Camera(camera_id_string="camera_living_room_01", name="Phòng khách", location="Tầng 1 - Khu vực chính", status="online")
            cam2 = models.Camera(camera_id_string="camera_balcony_02", name="Ban công", location="Tầng 2 - Ngoài trời", status="online")
            cam3 = models.Camera(camera_id_string="camera_kitchen_03", name="Nhà bếp", location="Tầng 1 - Khu vực bếp", status="online")
            cam4 = models.Camera(camera_id_string="camera_stairs_04", name="Cầu thang", location="Tầng 1 - Nối tầng 2", status="offline")
            db.add_all([cam1, cam2, cam3, cam4])
            db.commit()

            # Seed dữ liệu ROI mẫu cho camera phòng khách
            roi1 = models.ROIZone(
                camera_id="camera_living_room_01",
                name="Khu vực TV & Cầu thang",
                points=json.dumps([{"x": 0.1, "y": 0.1}, {"x": 0.5, "y": 0.1}, {"x": 0.5, "y": 0.6}, {"x": 0.1, "y": 0.6}]),
                sensitivity="high",
                enabled=True
            )
            db.add(roi1)
            db.commit()
    finally:
        db.close()

init_seed_data()

app = FastAPI(title="AI Child Guardian Backend API")

# 3. Cấu hình CORS cho phép Frontend truy cập API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Nhúng Signaling Server & Restful API Router
app.include_router(signaling_router)
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Backend API đang hoạt động. Signaling Server sẵn sàng."}