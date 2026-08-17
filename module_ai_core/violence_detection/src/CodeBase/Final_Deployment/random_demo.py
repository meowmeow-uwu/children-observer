# random_demo.py
import os
import sys
import random
import time
import cv2
import torch
import numpy as np
from torchvision import transforms

# Import model loader from model_utils
from model_utils import custome_X3D, load_model

def run_random_demo(archive_dir, num_samples_per_class=5, seed=None):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    print("=" * 78)
    print("       RANDOM VIDEO SELECTION & GENERAL INFERENCE DEMO (PyTorch X3D-M)")
    print("=" * 78)
    print(f"Archive Directory:       {archive_dir}")
    print(f"Random Samples per Class: {num_samples_per_class} (Total: {num_samples_per_class * 2} videos)")

    v_dir = os.path.join(archive_dir, "Violence")
    nv_dir = os.path.join(archive_dir, "NonViolence")

    if not os.path.exists(v_dir) or not os.path.exists(nv_dir):
        # Fallback to search subdirectories
        v_files = []
        nv_files = []
        for root, _, files in os.walk(archive_dir):
            for f in files:
                if f.lower().endswith(('.mp4', '.avi', '.mkv')):
                    full_p = os.path.join(root, f)
                    if '\\violence\\' in full_p.lower() or '/violence/' in full_p.lower():
                        v_files.append(full_p)
                    elif '\\nonviolence\\' in full_p.lower() or '/nonviolence/' in full_p.lower():
                        nv_files.append(full_p)
    else:
        v_files = [os.path.join(v_dir, f) for f in os.listdir(v_dir) if f.lower().endswith(('.mp4', '.avi', '.mkv'))]
        nv_files = [os.path.join(nv_dir, f) for f in os.listdir(nv_dir) if f.lower().endswith(('.mp4', '.avi', '.mkv'))]

    # Deduplicate by basename
    seen_v = set()
    unique_v = []
    for p in v_files:
        bn = os.path.basename(p).lower()
        if bn not in seen_v:
            seen_v.add(bn)
            unique_v.append(p)

    seen_nv = set()
    unique_nv = []
    for p in nv_files:
        bn = os.path.basename(p).lower()
        if bn not in seen_nv:
            seen_nv.add(bn)
            unique_nv.append(p)

    selected_v = random.sample(unique_v, min(num_samples_per_class, len(unique_v)))
    selected_nv = random.sample(unique_nv, min(num_samples_per_class, len(unique_nv)))

    test_samples = []
    for p in selected_v:
        test_samples.append((p, 1, "Violence"))
    for p in selected_nv:
        test_samples.append((p, 0, "NonViolence"))

    random.shuffle(test_samples)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute Device:          {device}")

    # Load Model
    model_path = os.path.join(os.path.dirname(__file__), "model.pth")
    print("\nLoading PyTorch X3D-M model...")
    t0 = time.time()
    model = custome_X3D(num_classes=2)
    model = load_model(model, model_path, device)
    model.eval()
    print(f"Model loaded successfully in {time.time() - t0:.2f}s!")

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Resize((224, 224)),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    print("\nProcessing Random Videos...")
    print("-" * 78)
    print(f"{'#':<3} | {'Filename':<12} | {'True Label':<12} | {'Predicted':<12} | {'Violence %':<12} | {'Latency':<8} | {'Match'}")
    print("-" * 78)

    correct_count = 0
    total_latency = 0.0

    for idx, (video_path, true_label, true_name) in enumerate(test_samples, start=1):
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            print(f"{idx:<3} | {os.path.basename(video_path):<12} | {true_name:<12} | ERROR        | N/A          | N/A      | [ERROR]")
            continue

        selected_indices = set(np.linspace(0, total_frames - 1, 16, dtype=int))
        frames = []
        f_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if f_idx in selected_indices:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(transform(frame_rgb))
            f_idx += 1
        cap.release()

        while len(frames) < 16:
            frames.append(frames[-1])
        frames = frames[:16]

        clip_tensor = torch.stack(frames).permute(1, 0, 2, 3).unsqueeze(0).to(device)

        t_inf_start = time.time()
        with torch.no_grad():
            outputs = model(clip_tensor)
        latency_ms = (time.time() - t_inf_start) * 1000
        total_latency += latency_ms

        probs = outputs.squeeze().cpu().numpy()
        prob_nv = float(probs[0]) # Class 0: NonViolence
        prob_v = float(probs[1])  # Class 1: Violence

        pred_label = 1 if prob_v >= 0.5 else 0
        pred_name = "Violence" if pred_label == 1 else "NonViolence"

        is_match = (pred_label == true_label)
        if is_match:
            correct_count += 1
            match_str = "[OK] MATCH"
        else:
            match_str = "[MISMATCH]"

        filename = os.path.basename(video_path)
        print(f"{idx:<3} | {filename:<12} | {true_name:<12} | {pred_name:<12} | {prob_v * 100:6.2f}%      | {latency_ms:5.1f}ms  | {match_str}")

    print("=" * 78)
    print("                      RANDOM INFERENCE SUMMARY")
    print("=" * 78)
    print(f"Total Random Videos Evaluated: {len(test_samples)}")
    print(f"Correct Predictions:           {correct_count} / {len(test_samples)}")
    acc = (correct_count / len(test_samples)) * 100 if len(test_samples) > 0 else 0
    print(f"Batch Accuracy:                {acc:.2f}%")
    avg_latency = total_latency / len(test_samples) if len(test_samples) > 0 else 0
    print(f"Average Latency per Video:     {avg_latency:.1f} ms")
    print("=" * 78)

if __name__ == "__main__":
    archive_path = r"c:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\archive\Real Life Violence Dataset"
    samples_per_class = 5
    if len(sys.argv) > 1:
        samples_per_class = int(sys.argv[1])
    run_random_demo(archive_path, num_samples_per_class=samples_per_class)
