# rpi_detector.py
"""
Raspberry Pi Real-time Violence Detector Engine
Optimized for Raspberry Pi 4 / 5 (ARM64) with ONNX Runtime & OpenCV.
Zero PyTorch dependency.
"""

import os
import sys
import time
import threading
from collections import deque
import cv2
import numpy as np
import onnxruntime as ort

class RaspberryPiViolenceDetector:
    def __init__(
        self,
        model_path="model_embedded_simplified.onnx",
        threshold=0.5,
        clip_length=16,
        frame_stride=4,
        spatial_size=224,
        num_threads=4,
        alert_callback=None
    ):
        """
        Initialize Violence Detector for Raspberry Pi.
        
        :param model_path: Path to .onnx model file (model_embedded_simplified.onnx or model_embedded_int8.onnx)
        :param threshold: Classification probability threshold for violence alert (0.0 to 1.0)
        :param clip_length: Number of frames per temporal window (default: 16)
        :param frame_stride: Interval between sampled frames (e.g. 4 frames = sample every 4th frame)
        :param spatial_size: Image height and width (default: 224)
        :param num_threads: Number of CPU threads for ONNX Runtime (default: 4 for RPi quad-core)
        :param alert_callback: Optional callable func(result_dict) triggered when violence is detected
        """
        self.model_path = model_path
        self.threshold = threshold
        self.clip_length = clip_length
        self.frame_stride = frame_stride
        self.spatial_size = spatial_size
        self.alert_callback = alert_callback
        
        # ImageNet normalization constants (Precomputed for speed)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
        
        # Ring buffer for strided sliding window
        self.max_ring_len = self.clip_length * self.frame_stride
        self.frame_ring = deque(maxlen=self.max_ring_len)
        
        # Setup ONNX Runtime Session optimized for ARM NEON
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = num_threads
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        providers = ["CPUExecutionProvider"]
        if "TensorrtExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "TensorrtExecutionProvider")
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")
            
        self.session = ort.InferenceSession(self.model_path, opts, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        self.is_running = False
        print(f"[RPi Violence Detector] Loaded model '{os.path.basename(model_path)}' successfully!")

    def preprocess_frame(self, frame_bgr):
        """
        Fast frame preprocessing: Resize -> BGR2RGB -> Normalize -> HWC to CHW
        """
        resized = cv2.resize(frame_bgr, (self.spatial_size, self.spatial_size), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        # Transpose HWC (224, 224, 3) -> CHW (3, 224, 224)
        chw = np.transpose(rgb, (2, 0, 1))
        # Vectorized ImageNet Normalization
        return (chw - self.mean) / self.std

    def process_frame(self, frame_bgr):
        """
        Push a single camera frame into detector.
        Returns inference dict if a clip inference was triggered, otherwise None.
        """
        chw_frame = self.preprocess_frame(frame_bgr)
        self.frame_ring.append(chw_frame)
        
        if len(self.frame_ring) < self.max_ring_len:
            return None
        
        # Extract 16 frames spaced by frame_stride
        ring_list = list(self.frame_ring)
        strided_frames = [ring_list[i * self.frame_stride] for i in range(self.clip_length)]
        
        # Stack into (1, 3, 16, 224, 224)
        clip_t = np.stack(strided_frames, axis=1) # (3, 16, 224, 224)
        clip_input = np.expand_dims(clip_t, axis=0).astype(np.float32)
        
        t0 = time.time()
        outputs = self.session.run([self.output_name], {self.input_name: clip_input})[0]
        latency_ms = (time.time() - t0) * 1000.0
        
        prob_non_violence = float(outputs[0][0])
        prob_violence = float(outputs[0][1])
        is_violence = prob_violence >= self.threshold
        
        result = {
            "is_violence": is_violence,
            "confidence": prob_violence if is_violence else prob_non_violence,
            "prob_violence": prob_violence,
            "prob_non_violence": prob_non_violence,
            "latency_ms": round(latency_ms, 2),
            "timestamp": time.time()
        }
        
        if is_violence and self.alert_callback:
            try:
                self.alert_callback(result, frame_bgr)
            except Exception as e:
                print(f"[Warning] Alert callback error: {e}")
                
        return result

    def start_camera_stream(self, camera_source=0, display=True, infer_every_n_frames=4):
        """
        Run continuous live camera loop (Webcam, CSI camera, or RTSP stream).
        """
        cap = cv2.VideoCapture(camera_source)
        if not cap.isOpened():
            print(f"[ERROR] Could not open camera source: {camera_source}")
            return
            
        print(f"[RPi Violence Detector] Started camera stream: {camera_source}")
        self.is_running = True
        frame_idx = 0
        last_result = None
        
        try:
            while self.is_running and cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                frame_idx += 1
                
                # Check for sliding window prediction every N frames
                if frame_idx % infer_every_n_frames == 0:
                    res = self.process_frame(frame)
                    if res is not None:
                        last_result = res
                        status_str = "🚨 VIOLENCE" if res["is_violence"] else "✅ SAFE"
                        print(f"[{time.strftime('%H:%M:%S')}] {status_str} | Violence: {res['prob_violence']*100:.1f}% | Latency: {res['latency_ms']} ms")
                else:
                    self.frame_ring.append(self.preprocess_frame(frame))
                    
                if display:
                    # Draw UI overlay
                    disp_frame = frame.copy()
                    if last_result is not None:
                        color = (0, 0, 255) if last_result["is_violence"] else (0, 255, 0)
                        lbl = f"{'VIOLENCE' if last_result['is_violence'] else 'NORMAL'}: {last_result['confidence']*100:.1f}% ({last_result['latency_ms']:.0f}ms)"
                        cv2.putText(disp_frame, lbl, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                    cv2.imshow("Raspberry Pi Violence Monitor", disp_frame)
                    if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                        break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.is_running = False
            print("[RPi Violence Detector] Camera stream stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Raspberry Pi Violence Detection Stream Runner")
    parser.add_argument("--model", type=str, default="model_embedded_simplified.onnx", help="Path to ONNX model")
    parser.add_argument("--source", default=0, help="Camera index (0, 1), video file, or RTSP URL")
    parser.add_argument("--threshold", type=float, default=0.5, help="Alert threshold")
    parser.add_argument("--no-display", action="store_true", help="Run in headless mode (no GUI window)")
    args = parser.parse_args()

    # If source is digit string, convert to int (e.g. '0' -> 0)
    src = int(args.source) if isinstance(args.source, str) and args.source.isdigit() else args.source

    def on_violence_alert(result, frame):
        print(f">>> [TRIGGERED ACTION] Violence Alert sent! Confidence: {result['prob_violence']*100:.1f}%")
        # Example: Save screenshot, publish MQTT message, trigger GPIO pin, etc.

    detector = RaspberryPiViolenceDetector(
        model_path=args.model,
        threshold=args.threshold,
        alert_callback=on_violence_alert
    )

    detector.start_camera_stream(
        camera_source=src,
        display=not args.no_display
    )
