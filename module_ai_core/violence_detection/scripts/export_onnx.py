"""
Export PyTorch X3D Violence Detection model to ONNX format for Edge & Server Deployment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import numpy as np
import torch
from loguru import logger

# Add root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.model.loader import load_model


def export_to_onnx(
    output_path: str = "weights/x3d_violence.onnx",
    opset_version: int = 16,
    dynamic_batch: bool = True,
    verify: bool = True,
) -> Path:
    """
    Export ViolenceX3D model to ONNX format.

    Args:
        output_path: File path to save exported ONNX model.
        opset_version: ONNX opset version (default: 16).
        dynamic_batch: Whether to enable dynamic batch size axis.
        verify: Verify exported ONNX model against PyTorch output.

    Returns:
        Path object of saved ONNX file.
    """
    config = ViolenceDetectionConfig(device="cpu")
    logger.info("Loading PyTorch model for ONNX export (CPU)...")
    model = load_model(config)
    model.eval()

    # Input tensor shape: [Batch=1, Channels=3, Frames=16, Height=224, Width=224]
    dummy_input = torch.randn(
        1, 3, config.clip_length, config.spatial_size, config.spatial_size,
        dtype=torch.float32
    )

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    input_names = ["input_clip"]
    output_names = ["logits"]

    dynamic_axes = None
    if dynamic_batch:
        dynamic_axes = {
            "input_clip": {0: "batch_size"},
            "logits": {0: "batch_size"},
        }

    logger.info(f"Exporting model to ONNX: {out_file} (opset={opset_version})...")

    torch.onnx.export(
        model,
        dummy_input,
        str(out_file),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=input_names,
        output_names=output_names,
        dynamic_axes=dynamic_axes,
    )

    logger.success(f"ONNX model successfully saved to: {out_file.resolve()}")

    # Optional ONNX Structure Verification
    try:
        import onnx
        onnx_model = onnx.load(str(out_file))
        onnx.checker.check_model(onnx_model)
        logger.info("ONNX model structure check passed successfully!")
    except ImportError:
        logger.warning("Package 'onnx' is not installed. Skipping structural validation.")
    except Exception as err:
        logger.error(f"ONNX validation error: {err}")

    # Optional Numerical Matching Verification
    if verify:
        try:
            import onnxruntime as ort

            logger.info("Verifying ONNX model inference output against PyTorch...")
            with torch.no_grad():
                pt_output = model(dummy_input).numpy()

            session = ort.InferenceSession(str(out_file), providers=["CPUExecutionProvider"])
            ort_inputs = {session.get_inputs()[0].name: dummy_input.numpy()}
            ort_output = session.run(None, ort_inputs)[0]

            max_diff = np.max(np.abs(pt_output - ort_output))
            logger.info(f"Max absolute difference (PyTorch vs ONNXRuntime): {max_diff:.6f}")

            if max_diff < 1e-4:
                logger.success("Verification PASSED! ONNX model outputs match PyTorch model.")
            else:
                logger.warning(f"Verification warning: Max diff {max_diff} exceeds 1e-4 threshold.")
        except ImportError:
            logger.warning("Package 'onnxruntime' is not installed. Skipping ONNX inference verification.")
        except Exception as err:
            logger.error(f"ONNXRuntime inference verification failed: {err}")

    return out_file


def main():
    parser = argparse.ArgumentParser(description="Export Violence Detection X3D Model to ONNX format.")
    parser.add_argument(
        "--output",
        type=str,
        default="weights/x3d_violence.onnx",
        help="Target output ONNX file path (default: weights/x3d_violence.onnx)",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=16,
        help="ONNX opset version (default: 16)",
    )
    parser.add_argument(
        "--no-dynamic-batch",
        action="store_true",
        help="Disable dynamic batch size axis",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip numerical comparison verification using onnxruntime",
    )

    args = parser.parse_args()

    export_to_onnx(
        output_path=args.output,
        opset_version=args.opset,
        dynamic_batch=not args.no_dynamic_batch,
        verify=not args.skip_verify,
    )


if __name__ == "__main__":
    main()
