# onnx_demo.py
import os
import sys
import argparse
import time
import cv2
import numpy as np
from collections import deque
import onnxruntime as ort

# UTF-8 terminal encoding safety on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def preprocess_frame(frame_bgr, spatial_size=224):
    """
    Standard ImageNet preprocessing using pure NumPy / OpenCV (no PyTorch dependency).
    """
    frame_resized = cv2.resize(frame_bgr, (spatial_size, spatial_size), interpolation=cv2.INTER_LINEAR)
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (frame_rgb - mean) / std
    
    # HWC -> CHW
    return np.transpose(normalized, (2, 0, 1))

class ONNXViolenceDetector:
    def __init__(self, model_path, num_threads=4):
        session_opt = ort.SessionOptions()
        session_opt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_opt.intra_op_num_threads = num_threads
        
        # Auto-detect available execution providers (CUDA, TensorRT, OpenVINO, DirectML, CPU)
        available_providers = ort.get_available_providers()
        selected_providers = []
        if "CUDAExecutionProvider" in available_providers:
            selected_providers.append("CUDAExecutionProvider")
        if "TensorrtExecutionProvider" in available_providers:
            selected_providers.append("TensorrtExecutionProvider")
        if "OpenVINOExecutionProvider" in available_providers:
            selected_providers.append("OpenVINOExecutionProvider")
        if "DmlExecutionProvider" in available_providers:
            selected_providers.append("DmlExecutionProvider")
        selected_providers.append("CPUExecutionProvider")
        
        self.session = ort.InferenceSession(model_path, session_opt, providers=selected_providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        print(f"ONNX Model Loaded: {os.path.basename(model_path)} with provider: {self.session.get_providers()[0]}")

    def predict_clip(self, clip_tensor):
        """
        clip_tensor: shape (1, 3, 16, 224, 224) as float32 np.ndarray
        """
        outputs = self.session.run([self.output_name], {self.input_name: clip_tensor})[0]
        # outputs shape: (1, 2)
        prob_non_violence = float(outputs[0][0])
        prob_violence = float(outputs[0][1])
        return prob_non_violence, prob_violence

def run_onnx_video_demo(video_path, model_path, threshold=0.5, stride=4, clip_length=16):
    print("=" * 76)
    print("        EMBEDDED ONNX VIOLENCE DETECTION VIDEO RUNNER")
    print("=" * 76)
    print(f"Video File:  {video_path}")
    print(f"ONNX Model:  {model_path}")
    print(f"Threshold:   {threshold}")
    print("-" * 76)

    detector = ONNXViolenceDetector(model_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    max_ring_len = clip_length * stride
    frame_ring = deque(maxlen=max_ring_len)

    frame_count = 0
    detections = []
    violence_alerts = 0

    print(f"{'Time':<8} | {'Status':<16} | {'Violence %':<12} | {'NonViolence %':<15} | {'Latency'}")
    print("-" * 76)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        current_sec = frame_count / fps

        processed_frame = preprocess_frame(frame)
        frame_ring.append(processed_frame)

        if len(frame_ring) >= max_ring_len and (frame_count % 8 == 0 or frame_count == total_frames):
            ring_list = list(frame_ring)
            strided_frames = [ring_list[i * stride] for i in range(clip_length)]
            # (16, 3, 224, 224) -> (3, 16, 224, 224) -> (1, 3, 16, 224, 224)
            clip_array = np.stack(strided_frames, axis=1) # (3, 16, 224, 224)
            clip_input = np.expand_dims(clip_array, axis=0).astype(np.float32)

            t0 = time.time()
            prob_nv, prob_v = detector.predict_clip(clip_input)
            latency_ms = (time.time() - t0) * 1000.0

            if prob_v >= threshold:
                status = "🚨 VIOLENCE"
                violence_alerts += 1
            else:
                status = "✅ NORMAL"

            print(f"{current_sec:05.2f}s  | {status:<16} | {prob_v * 100:6.2f}%      | {prob_nv * 100:6.2f}%         | {latency_ms:5.1f} ms")
            detections.append((current_sec, prob_v, prob_nv, latency_ms))

    cap.release()

    print("=" * 76)
    print("DEMO SUMMARY:")
    print(f"  • Total Frames Processed : {frame_count}")
    print(f"  • Sliding Inferences     : {len(detections)}")
    print(f"  • Violence Alert Count   : {violence_alerts}")
    if detections:
        peak_v = max(d[1] for d in detections)
        avg_lat = sum(d[3] for d in detections) / len(detections)
        print(f"  • Peak Violence Prob     : {peak_v * 100:.2f}%")
        print(f"  • Average Latency        : {avg_lat:.2f} ms")
        verdict = "🚨 VIOLENCE DETECTED" if (violence_alerts > 0 or peak_v >= threshold) else "✅ SAFE / NON-VIOLENT"
        print(f"  • Final Video Verdict    : {verdict}")
    print("=" * 76)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ONNX Real-time Video Violence Detector")
    parser.add_argument("--video", type=str, default=r"..\..\archive\Real Life Violence Dataset\Violence\V_105.mp4", help="Path to video")
    parser.add_argument("--model", type=str, default="model_embedded_simplified.onnx", help="Path to ONNX model")
    parser.add_argument("--threshold", type=float, default=0.5, help="Violence threshold")
    parser.add_argument("--stride", type=int, default=4, help="Frame stride")
    args = parser.parse_args()

    run_onnx_video_demo(
        video_path=args.video,
        model_path=args.model,
        threshold=args.threshold,
        stride=args.stride
    )
