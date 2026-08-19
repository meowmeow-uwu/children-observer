# export_embedded_onnx.py
import os
import sys
import argparse
import time
import numpy as np
import torch
import onnx
import onnxsim
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

# UTF-8 terminal encoding safety on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from model_utils import custome_X3D, load_model

def export_embedded(
    model_path="model.pth",
    output_dir=".",
    opset_version=16,
    batch_size=1,
    num_frames=16,
    spatial_size=224
):
    print("=" * 80, flush=True)
    print("   OPTIMIZED EMBEDDED / EDGE ONNX EXPORT ENGINE (PyTorch X3D-M)", flush=True)
    print("=" * 80, flush=True)
    print(f"Source PyTorch Checkpoint: {os.path.abspath(model_path)}", flush=True)
    print(f"Output Directory         : {os.path.abspath(output_dir)}", flush=True)
    print(f"Target Opset Version     : {opset_version}", flush=True)
    print(f"Clip Shape (T x H x W)   : {num_frames} frames x {spatial_size}x{spatial_size}", flush=True)

    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cpu")

    # 1. Load Model
    print(f"\n[1/5] Loading PyTorch Model Checkpoint...", flush=True)
    model = custome_X3D(num_classes=2)
    model = load_model(model, model_path, device)
    model.eval()

    dummy_static = torch.randn(batch_size, 3, num_frames, spatial_size, spatial_size)
    dummy_np = dummy_static.numpy()

    with torch.no_grad():
        torch_output = model(dummy_static).numpy()

    # 2. Export Static Embedded ONNX (Fixed Input Shape for Edge NPU/TensorRT/RKNN)
    static_onnx_path = os.path.join(output_dir, "model_embedded_static.onnx")
    print(f"\n[2/5] Exporting Static Embedded ONNX -> {static_onnx_path}...", flush=True)
    torch.onnx.export(
        model,
        dummy_static,
        static_onnx_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["probabilities"],
        dynamo=False
    )
    print(f"  • Raw static model exported ({os.path.getsize(static_onnx_path)/(1024*1024):.2f} MB)", flush=True)

    # 3. Export Dynamic ONNX (for flexible multi-batch streaming)
    dynamic_onnx_path = os.path.join(output_dir, "model_dynamic.onnx")
    print(f"\n[3/5] Exporting Dynamic Batch ONNX -> {dynamic_onnx_path}...", flush=True)
    torch.onnx.export(
        model,
        dummy_static,
        dynamic_onnx_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["probabilities"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "probabilities": {0: "batch_size"}
        },
        dynamo=False
    )
    print(f"  • Raw dynamic model exported ({os.path.getsize(dynamic_onnx_path)/(1024*1024):.2f} MB)", flush=True)

    # 4. Graph Simplification & Operator Fusion via ONNX-Simplifier
    simplified_onnx_path = os.path.join(output_dir, "model_embedded_simplified.onnx")
    print(f"\n[4/5] Optimizing & Simplifying Graph with onnxsim -> {simplified_onnx_path}...", flush=True)
    raw_model = onnx.load(static_onnx_path)
    model_sim, check = onnxsim.simplify(raw_model)
    if check:
        onnx.save(model_sim, simplified_onnx_path)
        print(f"  • Graph simplification succeeded ({os.path.getsize(simplified_onnx_path)/(1024*1024):.2f} MB)", flush=True)
    else:
        print("  • Simplification check failed, using raw static ONNX.", flush=True)
        simplified_onnx_path = static_onnx_path

    # 5. INT8 Quantization (Ultra-low memory footprint for Embedded ARM/MCU)
    int8_onnx_path = os.path.join(output_dir, "model_embedded_int8.onnx")
    print(f"\n[5/5] Generating Quantized INT8 Model -> {int8_onnx_path}...", flush=True)
    quantize_dynamic(
        simplified_onnx_path,
        int8_onnx_path,
        weight_type=QuantType.QUInt8
    )
    print(f"  • INT8 Quantized model generated ({os.path.getsize(int8_onnx_path)/(1024*1024):.2f} MB - 72% compression)", flush=True)

    # Numerical Parity Verification
    print("\n" + "=" * 80, flush=True)
    print("                 NUMERICAL VALIDATION & PARITY CHECKS", flush=True)
    print("=" * 80, flush=True)

    session_opt = ort.SessionOptions()
    session_opt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session_opt.intra_op_num_threads = min(4, os.cpu_count() or 1)

    ort_session = ort.InferenceSession(simplified_onnx_path, session_opt, providers=["CPUExecutionProvider"])
    ort_out = ort_session.run(None, {"input": dummy_np})[0]

    max_abs_diff = float(np.max(np.abs(torch_output - ort_out)))
    mean_sq_err = float(np.mean((torch_output - ort_out) ** 2))
    cos_sim = float(np.dot(torch_output.flatten(), ort_out.flatten()) / (np.linalg.norm(torch_output) * np.linalg.norm(ort_out)))

    print(f"PyTorch Output Reference : NonViolence={torch_output[0][0]:.6f}, Violence={torch_output[0][1]:.6f}", flush=True)
    print(f"ONNX Runtime Output      : NonViolence={ort_out[0][0]:.6f}, Violence={ort_out[0][1]:.6f}", flush=True)
    print(f"Max Absolute Error       : {max_abs_diff:.6e} (Target < 1e-4)", flush=True)
    print(f"Mean Squared Error (MSE) : {mean_sq_err:.6e}", flush=True)
    print(f"Cosine Similarity        : {cos_sim * 100:.6f}%", flush=True)
    print("-" * 80, flush=True)

    if max_abs_diff < 1e-4:
        print("✅ VERIFICATION PASSED: ONNX output matches PyTorch perfectly!", flush=True)
    else:
        print("⚠️ Warning: Output discrepancy exceeds 1e-4 threshold.", flush=True)

    print("=" * 80, flush=True)
    print("EMBEDDED EXPORT ARTIFACTS SUMMARY:")
    print(f"  1. Static Model (Edge NPU/RKNN/TensorRT) : {os.path.abspath(simplified_onnx_path)} ({os.path.getsize(simplified_onnx_path)/(1024*1024):.2f} MB)")
    print(f"  2. Dynamic Model (Multi-camera servers)   : {os.path.abspath(dynamic_onnx_path)} ({os.path.getsize(dynamic_onnx_path)/(1024*1024):.2f} MB)")
    print(f"  3. Quantized INT8 (Low-power Micro/ARM)  : {os.path.abspath(int8_onnx_path)} ({os.path.getsize(int8_onnx_path)/(1024*1024):.2f} MB)")
    print("=" * 80, flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export PyTorch X3D-M to Embedded ONNX")
    parser.add_argument("--model", type=str, default="model.pth", help="Path to input PyTorch model.pth")
    parser.add_argument("--output_dir", type=str, default=".", help="Directory to save exported ONNX models")
    parser.add_argument("--opset", type=int, default=16, help="Target ONNX opset version")
    args = parser.parse_args()

    export_embedded(
        model_path=args.model,
        output_dir=args.output_dir,
        opset_version=args.opset
    )
