"""
Federated Learning Server (Skeleton).

Cập nhật trọng số mô hình qua OTA mà không cần nhận video thô.
Đảm bảo quyền riêng tư - chỉ truyền model weights, không data.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from configs.settings import get_settings


class FederatedServer:
    """
    Federated learning server skeleton.

    Quản lý:
    - Thu nhận model updates từ các edge devices
    - Aggregate weights (FedAvg)
    - Phân phối weights mới qua OTA
    """

    def __init__(self):
        self.settings = get_settings()
        self._global_weights: dict | None = None
        self._client_updates: list[dict] = []
        self._round = 0

    def receive_update(self, client_id: str, weights: dict) -> None:
        """Nhận model update từ edge device."""
        self._client_updates.append({
            "client_id": client_id,
            "weights": weights,
        })
        logger.info(f"Received update from {client_id}. "
                     f"Total: {len(self._client_updates)} updates")

    def aggregate(self, min_clients: int = 3) -> dict | None:
        """Aggregate weights sử dụng FedAvg."""
        if len(self._client_updates) < min_clients:
            logger.info(f"Need {min_clients - len(self._client_updates)} more clients")
            return None

        self._round += 1
        logger.info(f"Aggregating round {self._round} with {len(self._client_updates)} clients")

        # TODO: Implement FedAvg aggregation
        # Placeholder: return first client's weights
        self._global_weights = self._client_updates[0]["weights"]
        self._client_updates.clear()

        return self._global_weights

    def get_global_weights(self) -> dict | None:
        """Lấy global weights cho OTA distribution."""
        return self._global_weights
