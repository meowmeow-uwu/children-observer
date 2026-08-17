import os
import time
from loguru import logger

SNAPSHOT_DIR = "data/snapshots"

def save_snapshot_bytes(device_id: str, payload: bytes, event_id: str | None = None) -> str | None:
    """
    Lưu dữ liệu binary snapshot nhận từ camera xuống disk.
    Trả về đường dẫn tới file ảnh đã lưu hoặc None nếu có lỗi.
    """
    try:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        timestamp = int(time.time() * 1000)
        filename = f"{event_id or f'{device_id}_{timestamp}'}.jpg"
        filepath = os.path.join(SNAPSHOT_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(payload)
            
        logger.info(f"📸 Đã lưu snapshot: {filepath}")
        return filename
    except Exception as e:
        logger.error(f"Lỗi lưu ảnh Snapshot: {e}")
        return None
