"""
Inference Engine.

Abstraction layer cho runtime inference:
- PyTorch native (.pt)
- ONNX Runtime
- TensorRT
- OpenVINO
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger


class BaseInferenceEngine(ABC):
    """Abstract base class cho inference engines."""

    @abstractmethod
    def load(self, model_path: Path) -> None:
        ...

    @abstractmethod
    def predict(self, input_data: np.ndarray) -> Any:
        ...

    @abstractmethod
    def get_latency_ms(self) -> float:
        ...


class ONNXEngine(BaseInferenceEngine):
    """ONNX Runtime inference engine."""

    def __init__(self, providers: list[str] | None = None):
        self.providers = providers or ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self._session = None
        self._latency_ms = 0.0

    def load(self, model_path: Path) -> None:
        import onnxruntime as ort

        self._session = ort.InferenceSession(str(model_path), providers=self.providers)
        input_info = self._session.get_inputs()[0]
        logger.info(
            f"ONNX model loaded: {model_path.name} | "
            f"input={input_info.name} shape={input_info.shape}"
        )

    def predict(self, input_data: np.ndarray) -> Any:
        import time

        if self._session is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        input_name = self._session.get_inputs()[0].name
        start = time.perf_counter()
        outputs = self._session.run(None, {input_name: input_data})
        self._latency_ms = (time.perf_counter() - start) * 1000

        return outputs

    def get_latency_ms(self) -> float:
        return self._latency_ms


class TensorRTEngine(BaseInferenceEngine):
    """TensorRT inference engine (placeholder - cần cài TensorRT)."""

    def __init__(self):
        self._latency_ms = 0.0

    def load(self, model_path: Path) -> None:
        logger.info(f"TensorRT engine loading: {model_path}")
        # TensorRT implementation sẽ bổ sung khi deploy lên Jetson
        logger.warning("TensorRT not yet implemented. Use ONNX engine instead.")

    def predict(self, input_data: np.ndarray) -> Any:
        raise NotImplementedError("TensorRT engine not yet implemented")

    def get_latency_ms(self) -> float:
        return self._latency_ms


def create_engine(engine_type: str = "onnx") -> BaseInferenceEngine:
    """Factory function tạo inference engine."""
    engines = {
        "onnx": ONNXEngine,
        "tensorrt": TensorRTEngine,
    }
    if engine_type not in engines:
        raise ValueError(f"Unknown engine type: {engine_type}. Available: {list(engines.keys())}")
    return engines[engine_type]()
