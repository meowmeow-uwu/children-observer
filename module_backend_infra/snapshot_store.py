from __future__ import annotations

import base64
import binascii
import os
import uuid
from pathlib import Path

SNAPSHOT_DIR = Path(os.getenv("ALERT_SNAPSHOT_DIR", ".demo/snapshots")).resolve()
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


def save_snapshot(encoded: str) -> str:
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("snapshot_base64 không hợp lệ") from exc
    if not data or len(data) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot vượt giới hạn 2MB hoặc rỗng")
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("snapshot phải là JPEG")
    name = f"alert-{uuid.uuid4().hex}.jpg"
    (SNAPSHOT_DIR / name).write_bytes(data)
    return f"/snapshots/{name}"


def clear_snapshots() -> int:
    deleted = 0
    for path in SNAPSHOT_DIR.glob("alert-*.jpg"):
        if path.is_file():
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted
