"""
Pipeline Profiling Script.

Đo lường thời gian xử lý (latency) của từng công đoạn trong Edge Pipeline:
1. Ingestion (Capture + Preprocess)
2. AI Inference (3 tasks)
3. Risk Assessment
4. Buffer & Alert Logic

Mục tiêu: Đảm bảo Inference < 2ms (với TensorRT) và tổng pipeline < 30ms.
"""

import time
import argparse
import numpy as np
from loguru import logger

from module_edge_firmware.ingestion.preprocessor import FramePreprocessor
from module_edge_firmware.inference.engine import create_engine
from module_ai_core.models.object_detector import ObjectDetector

def profile_inference(engine_type: str, model_path: str, n_runs: int = 100):
    logger.info(f"Profiling Inference Engine: {engine_type} | model={model_path}")
    
    try:
        # 1. Setup Preprocessor
        preprocessor = FramePreprocessor(target_size=640, normalize=True)
        
        # 2. Setup Detector
        detector = ObjectDetector(model_path=model_path, engine_type=engine_type)
        detector.load()
        
        # 3. Create dummy frame
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        # Warmup
        logger.info("Warming up...")
        for _ in range(10):
            detector.predict(frame)
            
        # Benchmark
        logger.info(f"Running benchmark for {n_runs} iterations...")
        latencies_preprocess = []
        latencies_inference = []
        
        for i in range(n_runs):
            # Measure Preprocess
            t0 = time.perf_counter()
            _ = preprocessor.to_tensor(frame)
            latencies_preprocess.append((time.perf_counter() - t0) * 1000)
            
            # Measure Inference (Detector.predict đã bao gồm preprocess nếu dùng engine_type != yolo)
            # Ở đây chúng ta đo trực tiếp detector.predict
            t1 = time.perf_counter()
            detector.predict(frame)
            latencies_inference.append((time.perf_counter() - t1) * 1000)
            
        avg_pre = np.mean(latencies_preprocess)
        avg_inf = np.mean(latencies_inference)
        p95_inf = np.percentile(latencies_inference, 95)
        
        print(f"\n{'='*50}")
        print(f" RESULTS: {engine_type.upper()}")
        print(f"{'='*50}")
        print(f" Avg Preprocess: {avg_pre:.2f} ms")
        print(f" Avg Total Predict: {avg_inf:.2f} ms")
        print(f" P95 Total Predict: {p95_inf:.2f} ms")
        print(f"{'='*50}\n")
        
    except Exception as e:
        logger.error(f"Profiling failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge Pipeline Profiler")
    parser.add_argument("--engine", choices=["yolo", "onnx", "tensorrt", "openvino"], default="onnx")
    parser.add_argument("--model", default="./weights/yolo26n.pt")
    parser.add_argument("--runs", type=int, default=100)
    
    args = parser.parse_args()
    profile_inference(args.engine, args.model, args.runs)
