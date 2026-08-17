# demo_detect.py
import os
import sys
import argparse
import time
import cv2
import torch
import numpy as np
from torchvision import transforms
from collections import deque

from model_utils import custome_X3D, load_model

def run_demo(video_path, model_path, threshold=0.5, clip_length=16, frame_stride=8, step=8, sampling="sliding", save_annotated=False):
    print("=" * 70)
    print("       VIOLENCE DETECTION DEMO - REAL-TIME DETECTOR")
    print("=" * 70)
    print(f"Video Source:  {video_path}")
    print(f"Model Path:    {model_path}")
    print(f"Sampling Mode: {sampling.upper()}")
    print(f"Threshold:     {threshold}")
    print(f"Clip Duration: {clip_length} frames (Temporal Frame Stride: {frame_stride})")

    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found at: {video_path}")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute Device:{device}")

    # Load Model
    print("\nLoading PyTorch X3D-M model...")
    t0 = time.time()
    model = custome_X3D(num_classes=2)
    model = load_model(model, model_path, device)
    model.eval()
    print(f"Model ready in {time.time() - t0:.2f}s!")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video file: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0

    print(f"\nVideo Info: {total_frames} frames, {fps:.1f} FPS, Duration: {duration_sec:.2f}s")
    print("-" * 70)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Resize((224, 224)),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    if sampling == "uniform":
        selected_indices = set(np.linspace(0, total_frames - 1, clip_length, dtype=int))
        frames = []
        idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if idx in selected_indices:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(transform(frame_rgb))
            idx += 1
        cap.release()

        while len(frames) < clip_length:
            frames.append(frames[-1])
        frames = frames[:clip_length]

        clip_tensor = torch.stack(frames).permute(1, 0, 2, 3).unsqueeze(0).to(device)
        t_start = time.time()
        with torch.no_grad():
            outputs = model(clip_tensor)
        latency_ms = (time.time() - t_start) * 1000

        probs = outputs.squeeze().cpu().numpy()
        prob_nv = float(probs[0])
        prob_v = float(probs[1])

        status = "[ALERT] VIOLENCE DETECTED" if prob_v >= threshold else "[OK] SAFE / NON-VIOLENT"

        print(f"{'Metric':<25} | {'Value'}")
        print("-" * 70)
        print(f"{'Violence Probability':<25} | {prob_v * 100:.2f}%")
        print(f"{'NonViolence Probability':<25} | {prob_nv * 100:.2f}%")
        print(f"{'Inference Latency':<25} | {latency_ms:.1f} ms")
        print(f"{'Final Detection Status':<25} | {status}")
        print("=" * 70)

    else:
        # Sliding Window Mode with Temporal Subsampling (frame_stride)
        print(f"{'Time (s)':<10} | {'Status':<20} | {'Violence %':<12} | {'NonViolence %':<15} | {'Latency'}")
        print("-" * 70)

        # Ring buffer storing strided frames
        frame_ring = deque(maxlen=clip_length * frame_stride)
        frame_count = 0
        detections = []
        violence_alerts = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            current_sec = frame_count / fps

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tensor_frame = transform(frame_rgb)
            frame_ring.append(tensor_frame)

            # Subsample 16 frames spaced by frame_stride
            if len(frame_ring) >= clip_length * frame_stride and (frame_count % step == 0 or frame_count == total_frames):
                ring_list = list(frame_ring)
                strided_frames = [ring_list[i * frame_stride] for i in range(clip_length)]

                clip_tensor = torch.stack(strided_frames).permute(1, 0, 2, 3).unsqueeze(0).to(device)

                t_inf_start = time.time()
                with torch.no_grad():
                    outputs = model(clip_tensor)
                latency_ms = (time.time() - t_inf_start) * 1000

                probs = outputs.squeeze().cpu().numpy()
                prob_nv = float(probs[0]) # Class 0: NonViolence
                prob_v = float(probs[1])  # Class 1: Violence

                if prob_v >= threshold:
                    status = "[ALERT] VIOLENCE"
                    violence_alerts += 1
                else:
                    status = "[OK] NORMAL"

                print(f"{current_sec:05.2f}s     | {status:<20} | {prob_v * 100:6.2f}%      | {prob_nv * 100:6.2f}%         | {latency_ms:.1f}ms")

                detections.append({
                    "frame": frame_count,
                    "timestamp_sec": round(current_sec, 2),
                    "status": status,
                    "prob_violence": round(prob_v, 4),
                    "prob_non_violence": round(prob_nv, 4),
                    "latency_ms": round(latency_ms, 1)
                })

        cap.release()

        print("=" * 70)
        print("                    DEMO DETECTION SUMMARY")
        print("=" * 70)
        print(f"Total Video Frames Processed: {frame_count}")
        print(f"Total Sliding Window Clips:   {len(detections)}")
        print(f"Violence Alert Clips:         {violence_alerts}")
        if len(detections) > 0:
            max_v = max(d['prob_violence'] for d in detections)
            avg_v = sum(d['prob_violence'] for d in detections) / len(detections)
            print(f"Peak Violence Probability:    {max_v * 100:.2f}%")
            print(f"Average Violence Probability: {avg_v * 100:.2f}%")
            final_verdict = "[ALERT] VIOLENCE DETECTED" if (violence_alerts > 0 or max_v >= threshold) else "[OK] SAFE / NON-VIOLENT"
            print(f"Final Video Classification:   {final_verdict}")
        print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Violence Detection Demo on a Video File")
    parser.add_argument("--video", type=str, default=r"c:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\archive\Real Life Violence Dataset\Violence\V_105.mp4", help="Path to input video")
    parser.add_argument("--model", type=str, default=r"c:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\src\CodeBase\Final_Deployment\model.pth", help="Path to model.pth")
    parser.add_argument("--threshold", type=float, default=0.5, help="Violence probability threshold")
    parser.add_argument("--frame_stride", type=int, default=4, help="Temporal frame stride for 16-frame clip sampling")
    parser.add_argument("--step", type=int, default=8, help="Sliding window step stride")
    parser.add_argument("--sampling", type=str, default="sliding", choices=["uniform", "sliding"], help="Frame sampling strategy")

    args = parser.parse_args()
    run_demo(
        video_path=args.video,
        model_path=args.model,
        threshold=args.threshold,
        clip_length=16,
        frame_stride=args.frame_stride,
        step=args.step,
        sampling=args.sampling
    )
