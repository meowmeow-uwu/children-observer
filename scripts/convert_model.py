"""
Script chuyển đổi model format.

Usage:
    python scripts/convert_model.py --model weights/best.pt --format onnx
    python scripts/convert_model.py --model weights/best.pt --format tensorrt
"""

import argparse
from pathlib import Path

from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Convert model format")
    parser.add_argument("--model", required=True, help="Path to model weights (.pt)")
    parser.add_argument("--format", default="onnx", choices=["onnx", "engine", "openvino"])
    parser.add_argument("--img-size", type=int, default=640)
    parser.add_argument("--half", action="store_true", help="FP16 quantization")
    args = parser.parse_args()

    from module_ai_core.training.export import ModelExporter

    exporter = ModelExporter()
    model_path = Path(args.model)

    if "pose" in model_path.stem.lower():
        result = exporter.export_pose(model_path, args.format, args.img_size, args.half)
    else:
        result = exporter.export_detector(model_path, args.format, args.img_size, args.half)

    logger.info(f"Model exported to: {result}")


if __name__ == "__main__":
    main()
