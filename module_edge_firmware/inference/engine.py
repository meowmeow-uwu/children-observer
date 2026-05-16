"""
Inference Engine.

Abstraction layer cho runtime inference:
- PyTorch native (.pt)
- ONNX Runtime       → GPU qua CUDAExecutionProvider
- TensorRT           → Tối ưu cho Jetson/NVIDIA GPU, latency < 2ms
- OpenVINO           → Tối ưu cho Intel CPU/iGPU

Mục tiêu latency: < 2ms mỗi frame inference (sau tối ưu).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger


# =============================================================================
# Base Class
# =============================================================================

class BaseInferenceEngine(ABC):
    """Abstract base class cho tất cả inference engines."""

    @abstractmethod
    def load(self, model_path: Path) -> None:
        """Load model vào bộ nhớ."""
        ...

    @abstractmethod
    def predict(self, input_data: np.ndarray) -> Any:
        """Chạy inference trên input data (NCHW float32)."""
        ...

    @abstractmethod
    def get_latency_ms(self) -> float:
        """Latency inference lần cuối (ms)."""
        ...

    def warmup(self, input_shape: tuple = (1, 3, 640, 640), n_runs: int = 5) -> float:
        """
        Warmup engine để ổn định latency (quan trọng với GPU/TensorRT).

        Args:
            input_shape: Shape của input tensor (N, C, H, W).
            n_runs: Số lần warmup.

        Returns:
            Latency trung bình sau warmup (ms).
        """
        dummy = np.random.rand(*input_shape).astype(np.float32)
        latencies = []
        for i in range(n_runs):
            self.predict(dummy)
            latencies.append(self.get_latency_ms())
        avg = sum(latencies) / len(latencies)
        logger.info(f"Warmup ({n_runs} runs): avg_latency={avg:.2f}ms")
        return avg


# =============================================================================
# ONNX Runtime Engine
# =============================================================================

class ONNXEngine(BaseInferenceEngine):
    """
    ONNX Runtime inference engine.

    Hỗ trợ:
    - CUDAExecutionProvider: GPU inference (~3-10ms)
    - CPUExecutionProvider: CPU fallback (~15-50ms)

    Sử dụng khi chưa có TensorRT hoặc target là cloud deployment.
    """

    def __init__(self, providers: list[str] | None = None):
        # Ưu tiên CUDA, fallback CPU
        self.providers = providers or ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self._session = None
        self._input_name: str = ""
        self._latency_ms = 0.0

    def load(self, model_path: Path) -> None:
        """Load ONNX model và tạo InferenceSession."""
        import onnxruntime as ort

        # Log providers thực sự được dùng
        available = ort.get_available_providers()
        active_providers = [p for p in self.providers if p in available]
        logger.info(f"ONNX providers available: {available}")
        logger.info(f"ONNX providers active: {active_providers}")

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.enable_mem_pattern = True

        self._session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_options,
            providers=active_providers,
        )

        input_info = self._session.get_inputs()[0]
        self._input_name = input_info.name
        logger.info(
            f"ONNX model loaded: {model_path.name} | "
            f"input={self._input_name} shape={input_info.shape}"
        )

    def predict(self, input_data: np.ndarray) -> Any:
        """Chạy inference. Input: (N, C, H, W) float32."""
        if self._session is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.perf_counter()
        outputs = self._session.run(None, {self._input_name: input_data})
        self._latency_ms = (time.perf_counter() - start) * 1000

        return outputs

    def get_latency_ms(self) -> float:
        return self._latency_ms


# =============================================================================
# TensorRT Engine
# =============================================================================

class TensorRTEngine(BaseInferenceEngine):
    """
    TensorRT inference engine cho NVIDIA GPU / Jetson.

    Đây là engine tối ưu nhất — nhắm tới latency < 2ms trên Jetson Orin.

    Luồng:
    1. Export YOLO → ONNX (ObjectDetector.export("onnx"))
    2. Compile ONNX → TensorRT .engine file (build_engine())
    3. Load .engine và chạy inference qua CUDA stream

    Yêu cầu: tensorrt>=10.0, pycuda

    Precision modes:
    - FP32: Đầy đủ độ chính xác (baseline)
    - FP16: ~2x nhanh, mất <1% accuracy (khuyến nghị)
    - INT8: ~4x nhanh, cần calibration dataset
    """

    def __init__(self, precision: str = "fp16"):
        """
        Args:
            precision: "fp32", "fp16", hoặc "int8".
        """
        assert precision in ("fp32", "fp16", "int8"), f"Invalid precision: {precision}"
        self.precision = precision
        self._engine = None
        self._context = None
        self._stream = None
        self._bindings: list = []
        self._input_idx: int = 0
        self._output_idx: int = 1
        self._latency_ms = 0.0
        self._dtype = np.float16 if precision in ("fp16", "int8") else np.float32

    def load(self, model_path: Path) -> None:
        """
        Load TensorRT .engine file từ disk.

        Nếu file .engine chưa tồn tại nhưng file .onnx tồn tại,
        tự động build engine (lần đầu mất ~1-5 phút, các lần sau dùng cache).
        """
        engine_path = model_path.with_suffix(".engine")
        onnx_path = model_path.with_suffix(".onnx")

        # Nếu chưa có .engine, build từ .onnx
        if not engine_path.exists():
            if onnx_path.exists():
                logger.info(f"Building TensorRT engine from: {onnx_path}")
                logger.info(f"Precision: {self.precision} | This may take 1-5 minutes...")
                self.build_engine(onnx_path, engine_path)
            else:
                raise FileNotFoundError(
                    f"Neither .engine ({engine_path}) nor .onnx ({onnx_path}) found. "
                    "Export model first: ObjectDetector.export('onnx')"
                )

        self._load_engine(engine_path)

    def build_engine(self, onnx_path: Path, output_path: Path) -> None:
        """
        Compile ONNX model → TensorRT .engine.

        Args:
            onnx_path: Đường dẫn tới file .onnx.
            output_path: Đường dẫn lưu file .engine.
        """
        try:
            import tensorrt as trt
        except ImportError:
            raise ImportError(
                "TensorRT not installed. Install via: pip install tensorrt>=10.0\n"
                "Or use ONNXEngine as fallback."
            )

        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        network = builder.create_network(network_flags)
        parser = trt.OnnxParser(network, TRT_LOGGER)

        # Parse ONNX
        with open(onnx_path, "rb") as f:
            onnx_bytes = f.read()

        if not parser.parse(onnx_bytes):
            errors = [str(parser.get_error(i)) for i in range(parser.num_errors)]
            raise RuntimeError(f"ONNX parse failed:\n" + "\n".join(errors))

        # Build config
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB workspace

        # Precision flags
        if self.precision == "fp16" and builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
            logger.info("TensorRT FP16 mode enabled")
        elif self.precision == "int8" and builder.platform_has_fast_int8:
            config.set_flag(trt.BuilderFlag.INT8)
            logger.warning("INT8 cần calibration dataset để đạt accuracy tốt nhất!")
        else:
            logger.info("TensorRT FP32 mode (baseline)")

        # Dynamic shape profile
        profile = builder.create_optimization_profile()
        input_tensor = network.get_input(0)
        input_name = input_tensor.name
        profile.set_shape(input_name, (1, 3, 640, 640), (1, 3, 640, 640), (4, 3, 640, 640))
        config.add_optimization_profile(profile)

        # Build serialized engine
        logger.info("Building TensorRT engine (vui lòng chờ)...")
        serialized = builder.build_serialized_network(network, config)
        if serialized is None:
            raise RuntimeError("TensorRT engine build failed!")

        with open(output_path, "wb") as f:
            f.write(serialized)

        logger.info(f"✅ TensorRT engine saved: {output_path}")

    def _load_engine(self, engine_path: Path) -> None:
        """Load serialized .engine file và chuẩn bị CUDA buffers."""
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit  # noqa: F401 - init CUDA driver
        except ImportError as e:
            raise ImportError(f"TensorRT/PyCUDA not installed: {e}")

        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        runtime = trt.Runtime(TRT_LOGGER)

        with open(engine_path, "rb") as f:
            engine_data = f.read()

        self._engine = runtime.deserialize_cuda_engine(engine_data)
        self._context = self._engine.create_execution_context()
        self._stream = cuda.Stream()

        # Allocate bindings (input + output buffers trên GPU)
        self._bindings = []
        for i in range(self._engine.num_io_tensors):
            tensor_name = self._engine.get_tensor_name(i)
            shape = self._engine.get_tensor_shape(tensor_name)
            dtype = trt.nptype(self._engine.get_tensor_dtype(tensor_name))
            size = int(np.prod(shape)) * np.dtype(dtype).itemsize
            buf = cuda.mem_alloc(size)
            self._bindings.append(int(buf))

        logger.info(
            f"✅ TensorRT engine loaded: {engine_path.name} | "
            f"precision={self.precision}"
        )

    def predict(self, input_data: np.ndarray) -> Any:
        """
        Chạy inference với TensorRT.

        Args:
            input_data: (N, C, H, W) float32 numpy array.

        Returns:
            List of output numpy arrays.
        """
        if self._engine is None or self._context is None:
            raise RuntimeError("Engine not loaded. Call load() first.")

        try:
            import pycuda.driver as cuda
            import tensorrt as trt
        except ImportError as e:
            raise RuntimeError(f"PyCUDA/TensorRT not available: {e}")

        start = time.perf_counter()

        # Cast đúng precision
        input_data = input_data.astype(self._dtype)

        # Copy input lên GPU
        input_name = self._engine.get_tensor_name(0)
        cuda.memcpy_htod_async(self._bindings[0], input_data, self._stream)

        # Inference
        self._context.execute_async_v3(self._stream.handle)

        # Copy output về CPU
        output_name = self._engine.get_tensor_name(1)
        output_shape = tuple(self._engine.get_tensor_shape(output_name))
        output_dtype = trt.nptype(self._engine.get_tensor_dtype(output_name))
        output = np.empty(output_shape, dtype=output_dtype)
        cuda.memcpy_dtoh_async(output, self._bindings[1], self._stream)
        self._stream.synchronize()

        self._latency_ms = (time.perf_counter() - start) * 1000
        return [output]

    def get_latency_ms(self) -> float:
        return self._latency_ms


# =============================================================================
# OpenVINO Engine (Intel CPU / iGPU)
# =============================================================================

class OpenVINOEngine(BaseInferenceEngine):
    """
    OpenVINO inference engine cho Intel CPU / iGPU / VPU.

    Tối ưu cho thiết bị không có NVIDIA GPU (Intel NUC, Raspberry Pi với OpenVINO).
    Latency mục tiêu: ~5-15ms trên Intel CPU (thấp hơn pure PyTorch ~3-5x).

    Cài đặt: pip install openvino>=2024.0

    Luồng:
    1. Export YOLO → ONNX
    2. OpenVINO tự động convert và tối ưu graph
    """

    def __init__(self, device: str = "CPU"):
        """
        Args:
            device: "CPU", "GPU" (Intel iGPU), "AUTO", "MULTI:CPU,GPU"
        """
        self.device = device
        self._compiled_model = None
        self._infer_request = None
        self._input_key = None
        self._latency_ms = 0.0

    def load(self, model_path: Path) -> None:
        """
        Load model qua OpenVINO Runtime.

        Hỗ trợ: .onnx, .xml (IR format), .pt (OpenVINO FE).
        """
        try:
            from openvino.runtime import Core
        except ImportError:
            raise ImportError(
                "OpenVINO not installed. Install via: pip install openvino>=2024.0\n"
                "Or use ONNXEngine as fallback."
            )

        core = Core()

        logger.info(f"OpenVINO available devices: {core.available_devices}")
        logger.info(f"Loading model on device: {self.device}")

        # Read model (auto-detect format: .onnx, .xml)
        model = core.read_model(str(model_path))

        # Compile với tối ưu hóa
        self._compiled_model = core.compile_model(
            model=model,
            device_name=self.device,
            config={
                "PERFORMANCE_HINT": "THROUGHPUT" if self.device == "CPU" else "LATENCY",
                "NUM_STREAMS": "AUTO",
            },
        )

        self._infer_request = self._compiled_model.create_infer_request()
        self._input_key = self._compiled_model.input(0)

        logger.info(
            f"✅ OpenVINO model loaded: {model_path.name} | device={self.device}"
        )

    def predict(self, input_data: np.ndarray) -> Any:
        """
        Chạy inference với OpenVINO.

        Args:
            input_data: (N, C, H, W) float32 numpy array.
        """
        if self._infer_request is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.perf_counter()

        self._infer_request.infer({self._input_key: input_data})
        outputs = [
            self._infer_request.get_output_tensor(i).data.copy()
            for i in range(len(self._compiled_model.outputs))
        ]

        self._latency_ms = (time.perf_counter() - start) * 1000
        return outputs

    def get_latency_ms(self) -> float:
        return self._latency_ms


# =============================================================================
# Factory
# =============================================================================

def create_engine(engine_type: str = "onnx", **kwargs) -> BaseInferenceEngine:
    """
    Factory function tạo inference engine.

    Args:
        engine_type: "onnx", "tensorrt", "openvino"
        **kwargs: Tham số truyền vào engine constructor.
            - tensorrt: precision="fp16" | "fp32" | "int8"
            - openvino: device="CPU" | "GPU" | "AUTO"
            - onnx: providers=[...]

    Returns:
        BaseInferenceEngine instance.

    Examples:
        >>> engine = create_engine("tensorrt", precision="fp16")
        >>> engine = create_engine("openvino", device="CPU")
        >>> engine = create_engine("onnx")
    """
    engines = {
        "onnx": ONNXEngine,
        "tensorrt": TensorRTEngine,
        "openvino": OpenVINOEngine,
    }
    if engine_type not in engines:
        raise ValueError(
            f"Unknown engine type: {engine_type!r}. "
            f"Available: {list(engines.keys())}"
        )
    engine = engines[engine_type](**kwargs)
    logger.info(f"Created inference engine: {engine_type}")
    return engine


def auto_select_engine() -> BaseInferenceEngine:
    """
    Tự động chọn engine tốt nhất dựa trên phần cứng hiện có.

    Priority: TensorRT (NVIDIA GPU) > OpenVINO (Intel) > ONNX (fallback)
    """
    # Thử TensorRT
    try:
        import tensorrt  # noqa: F401
        import pycuda.driver as cuda  # noqa: F401
        cuda.init()
        if cuda.Device.count() > 0:
            logger.info("Auto-selected: TensorRT (NVIDIA GPU detected)")
            return TensorRTEngine(precision="fp16")
    except ImportError:
        pass

    # Thử OpenVINO
    try:
        import openvino.runtime  # noqa: F401
        logger.info("Auto-selected: OpenVINO (Intel hardware)")
        return OpenVINOEngine(device="AUTO")
    except ImportError:
        pass

    # Fallback ONNX
    logger.info("Auto-selected: ONNX Runtime (universal fallback)")
    return ONNXEngine()
