"""
Storage Manager - Quản lý dung lượng đĩa.

Tự động dọn dẹp các file cũ (snapshots, clips) khi bộ nhớ đầy.
"""

from __future__ import annotations

from pathlib import Path
from loguru import logger
import psutil

class StorageManager:
    def __init__(self, dirs: list[Path], min_free_gb: float = 1.0):
        self.dirs = dirs
        self.min_free_gb = min_free_gb

    def check_and_cleanup(self):
        """Kiểm tra dung lượng và xóa file cũ nếu cần."""
        for d in self.dirs:
            if not d.exists(): continue
            
            usage = psutil.disk_usage(str(d))
            free_gb = usage.free / (1024**3)
            
            if free_gb < self.min_free_gb:
                logger.warning(f"Low disk space ({free_gb:.2f}GB). Cleaning up {d}...")
                self._cleanup_dir(d)

    def _cleanup_dir(self, directory: Path):
        """Xóa 20% số file cũ nhất trong thư mục."""
        files = sorted(
            [f for f in directory.glob("*") if f.is_file()],
            key=lambda x: x.stat().st_mtime
        )
        
        if not files: return
        
        # Xóa 20% file cũ nhất
        num_to_delete = max(1, len(files) // 5)
        for i in range(num_to_delete):
            try:
                files[i].unlink()
                logger.info(f"Auto-deleted old file: {files[i].name}")
            except Exception as e:
                logger.error(f"Failed to delete {files[i]}: {e}")
