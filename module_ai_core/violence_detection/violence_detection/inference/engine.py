"""
Strategy Pattern implementation for Violence Detection Inference Engines (PyTorch vs ONNX Runtime).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.model.loader import load_model


class BaseInferenceEngine(ABC):
    """
    Abstract Strategy Interface for Inference Engines.
    """

    @abstractmethod
    def predict_raw_prob(self, clip_tensor: torch.Tensor) -> float:
        """
        Predict raw violence probability from preprocessed clip tensor.

        Args:
            clip_tensor: Tensor of shape [1, C, T, H, W]

        Returns:
            Raw probability float value between 0.0 and 1.0.
        """
        pass


class PyTorchInferenceEngine(BaseInferenceEngine):
    """
    Concrete Strategy for PyTorch Inference Engine (Server / GPU CUDA / PyTorch CPU).
    """

    def __init__(self, config: ViolenceDetectionConfig):
        self.config = config
        self.device = config.get_resolved_device()
        logger.info(f"Initializing PyTorchInferenceEngine on device: {self.device}")
        self.model = load_model(config)

    def predict_raw_prob(self, clip_tensor: torch.Tensor) -> float:
        input_tensor = clip_tensor.to(self.device)
        with torch.inference_mode():
            logits = self.model(input_tensor)
            probs = F.softmax(logits, dim=1)

            if self.device.type == "cuda":
                torch.cuda.synchronize()

            raw_prob = float(probs[0, 1].item())
        return raw_prob


class ONNXInferenceEngine(BaseInferenceEngine):
    """
    Concrete Strategy for ONNX Runtime Inference Engine (Edge / Embedded / Optimized CPU & GPU).
    """

    def __init__(self, config: ViolenceDetectionConfig):
        self.config = config

        try:
            import onnxruntime as ort
        except ImportError as err:
            logger.error("onnxruntime package is not installed. Cannot use ONNXInferenceEngine.")
            raise RuntimeError("Install onnxruntime via `pip install onnxruntime` to use ONNX engine.") from err

        model_path = Path(config.onnx_model_path or "weights/x3d_violence.onnx")
        if not model_path.exists():
            logger.error(f"ONNX model file not found at: {model_path}")
            raise FileNotFoundError(f"ONNX model file missing: {model_path}. Run scripts/export_onnx.py first.")

        providers = config.onnx_providers or ["CUDAExecutionProvider", "CPUExecutionProvider"]
        logger.info(f"Initializing ONNXInferenceEngine from '{model_path}' with providers: {providers}")

        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        logger.info(f"ONNXInferenceEngine initialized using active provider: {self.session.get_providers()[0]}")

    def predict_raw_prob(self, clip_tensor: torch.Tensor) -> float:
        input_array = clip_tensor.cpu().numpy().astype(np.float32)
        raw_logits = self.session.run([self.output_name], {self.input_name: input_array})[0]

        # Softmax over logits [1, 2]
        logits = raw_logits[0]
        e_x = np.exp(logits - np.max(logits))
        probs = e_x / e_x.sum()

        return float(probs[1])


class InferenceEngineFactory:
    """
    Factory to create appropriate Inference Engine Strategy based on configuration.
    """

    @staticmethod
    def create_engine(config: ViolenceDetectionConfig) -> BaseInferenceEngine:
        backend = (config.backend or "pytorch").lower()

        if backend == "pytorch":
            return PyTorchInferenceEngine(config)

        elif backend == "onnx":
            return ONNXInferenceEngine(config)

        elif backend == "auto":
            onnx_path = Path(config.onnx_model_path or "weights/x3d_violence.onnx")
            try:
                import onnxruntime
                if onnx_path.exists():
                    logger.info("Auto-selected ONNXInferenceEngine (ONNX model file found).")
                    return ONNXInferenceEngine(config)
            except ImportError:
                pass

            logger.info("Auto-selected PyTorchInferenceEngine (Fallback).")
            return PyTorchInferenceEngine(config)

        else:
            raise ValueError(f"Unsupported inference backend: '{config.backend}'. Supported: 'pytorch', 'onnx', 'auto'")
