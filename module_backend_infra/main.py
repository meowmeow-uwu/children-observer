from fastapi import FastAPI
from module_backend_infra.signaling.server import router as signaling_router

app = FastAPI(title="AI Child Guardian Backend API")

# Nhúng router signaling vào app chính
app.include_router(signaling_router)

@app.get("/")
async def root():
    return {"message": "Backend API đang hoạt động. Signaling Server sẵn sàng."}