"""
Model Registry - Theo dõi trạng thái model từ team AI.

Module 2 (Edge) sử dụng file này để biết model nào đã sẵn sàng,
model nào đang training, và tự động load những model available.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

from loguru import logger


@dataclass
class ModelInfo:
    """Thông tin một model AI."""
    task: str
    status: str  # "not_started", "training", "ready"
    path: str | None
    format: str | None
    metrics: dict
    note: str

    @property
    def is_ready(self) -> bool:
        """Model đã sẵn sàng để load."""
        return self.status == "ready" and self.path is not None

    @property
    def file_exists(self) -> bool:
        """File model tồn tại trên disk."""
        if self.path is None:
            return False
        return Path(self.path).exists()


class ModelRegistry:
    """
    Registry quản lý trạng thái model AI.

    Đọc từ file weights/registry.json để biết:
    - Model nào team AI đã train xong ("ready")
    - Model nào đang train ("training")
    - Model nào chưa bắt đầu ("not_started")
    """

    REGISTRY_PATH = Path("weights/registry.json")

    def __init__(self, registry_path: str | Path | None = None):
        self._path = Path(registry_path) if registry_path else self.REGISTRY_PATH
        self._models: dict[str, ModelInfo] = {}
        self.reload()

    def reload(self) -> None:
        """Đọc lại registry từ file."""
        if not self._path.exists():
            logger.warning(f"Registry not found: {self._path}")
            return

        data = json.loads(self._path.read_text())
        self._models = {}

        for task, info in data.items():
            self._models[task] = ModelInfo(
                task=task,
                status=info.get("status", "not_started"),
                path=info.get("path"),
                format=info.get("format"),
                metrics=info.get("metrics", {}),
                note=info.get("note", ""),
            )

    def get(self, task: str) -> ModelInfo | None:
        """Lấy thông tin model theo task."""
        return self._models.get(task)

    def is_ready(self, task: str) -> bool:
        """Kiểm tra model có sẵn sàng không."""
        info = self._models.get(task)
        if info is None:
            return False
        return info.is_ready and info.file_exists

    def get_ready_tasks(self) -> list[str]:
        """Danh sách các task đã có model sẵn sàng."""
        return [task for task, info in self._models.items()
                if info.is_ready and info.file_exists]

    def get_model_path(self, task: str) -> str | None:
        """Lấy đường dẫn model nếu sẵn sàng."""
        info = self._models.get(task)
        if info and info.is_ready and info.file_exists:
            return info.path
        return None

    def summary(self) -> str:
        """In tóm tắt trạng thái tất cả models."""
        lines = ["Model Registry Status:"]
        for task, info in self._models.items():
            icon = "✅" if (info.is_ready and info.file_exists) else "⏳" if info.status == "training" else "❌"
            lines.append(f"  {icon} {task}: {info.status} | path={info.path}")
        return "\n".join(lines)
