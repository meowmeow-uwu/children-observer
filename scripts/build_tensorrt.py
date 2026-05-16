"""
TensorRT Build Tool.

Tiện ích giúp compile mô hình YOLO (.onnx) sang TensorRT (.engine)
để đạt hiệu năng tối đa (< 2ms) trên NVIDIA GPU / Jetson.

Cách dùng:
    python scripts/build_tensorrt.py --model ./weights/yolo26n.onnx --precision fp16
"""

import argparse
from pathlib import Path
from loguru import logger
from module_edge_firmware.inference.engine import TensorRTEngine

def build(model_path: str, precision: str):
    path = Path(model_path)
    if not path.exists():
        logger.error(f"Model file not found: {path}")
        return

    logger.info(f"🚀 Starting TensorRT build for {path.name}")
    logger.info(f"   Precision: {precision.upper()}")
    
    try:
        engine = TensorRTEngine(precision=precision)
        # engine.load() sẽ tự động build nếu .engine chưa có và .onnx có sẵn
        engine.load(path)
        
        logger.info(f"✅ Build successful!")
        logger.info(f"   Output: {path.with_suffix('.engine')}")
        
        # Test performance
        logger.info("Running speed test...")
        avg_latency = engine.warmup(n_runs=50)
        logger.info(f"🚀 Average Latency: {avg_latency:.2f} ms")
        
        if avg_latency < 2.0:
            logger.info("✨ Performance target MET (< 2ms)!")
        else:
            logger.warning("⚠️ Performance target not met. Consider FP16 or Jetson/GPU upgrade.")
            
    except Exception as e:
        logger.error(f"❌ Build failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO to TensorRT Compiler")
    parser.add_argument("--model", required=True, help="Path to .onnx or .pt file")
    parser.add_argument("--precision", choices=["fp32", "fp16", "int8"], default="fp16")
    
    args = parser.parse_args()
    
    # Nếu là .pt, nhắc người dùng export sang onnx trước
    path = Path(args.model)
    if path.suffix == ".pt":
        logger.warning("Bạn đang dùng file .pt. Đang cố gắng tự động export sang ONNX...")
        try:
            from ultralytics import YOLO
            model = YOLO(args.model)
            onnx_path = model.export(format="onnx", dynamic=True)
            args.model = onnx_path
            logger.info(f"Exported to: {onnx_path}")
        except Exception as e:
            logger.error(f"Tự động export thất bại: {e}. Vui lòng dùng: yolo export format=onnx")
            exit(1)
            
    build(args.model, args.precision)
