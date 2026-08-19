# run_inference.py
import os
import sys
import argparse
import time
import json
import numpy as np
import cv2
import torch
import torch.nn.functional as F
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from collections import OrderedDict

# Import model loader from model_utils
from model_utils import custome_X3D, load_model

class VideoInferenceDataset(Dataset):
    def __init__(self, video_paths, num_frames=16, spatial_size=224):
        self.video_paths = video_paths
        self.num_frames = num_frames
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((spatial_size, spatial_size)),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def __len__(self):
        return len(self.video_paths)

    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        frames, success = self._extract_frames(video_path)
        
        # Determine ground truth label based on path
        lower_path = video_path.lower()
        if '\\violence\\' in lower_path or '/violence/' in lower_path:
            label = 1  # Violence (Class 1 in trained X3D model)
        elif '\\nonviolence\\' in lower_path or '/nonviolence/' in lower_path:
            label = 0  # NonViolence (Class 0 in trained X3D model)
        else:
            label = -1 # Unknown

        if not success or len(frames) == 0:
            # Fallback black frames if reading video failed
            dummy_frame = torch.zeros(3, 224, 224)
            frames = [dummy_frame] * self.num_frames
            valid = False
        else:
            valid = True

        # Stack into tensor (C, T, H, W)
        clip_tensor = torch.stack(frames).permute(1, 0, 2, 3).float()
        return clip_tensor, label, video_path, valid

    def _extract_frames(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return [], False

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return [], False

        if total_frames <= self.num_frames:
            selected_indices = set(range(total_frames))
        else:
            selected_indices = set(np.linspace(0, total_frames - 1, self.num_frames, dtype=int))

        frames = []
        idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if idx in selected_indices:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                tensor_frame = self.transform(frame_rgb)
                frames.append(tensor_frame)
            idx += 1
        cap.release()

        if len(frames) == 0:
            return [], False

        # Pad if needed
        while len(frames) < self.num_frames:
            frames.append(frames[-1])
        frames = frames[:self.num_frames]
        return frames, True

def run_inference(archive_dir, model_path, output_json="inference_results.json", batch_size=8, max_samples=None, threshold=0.5):
    print("=" * 70)
    print("      VIOLENCE DETECTION INFERENCE ENGINE - PyTorch X3D-M")
    print("=" * 70)
    print(f"Archive Directory: {archive_dir}")
    print(f"Model Checkpoint:  {model_path}")
    print(f"Batch Size:        {batch_size}")
    print(f"Threshold:         {threshold}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute Device:    {device}")

    # 1. Discover Video Files
    violence_paths = []
    nonviolence_paths = []
    seen_basenames = set()

    for root, _, files in os.walk(archive_dir):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mkv')):
                basename = file.lower()
                if basename not in seen_basenames:
                    seen_basenames.add(basename)
                    full_path = os.path.join(root, file)
                    lower_path = full_path.lower()
                    if '\\violence\\' in lower_path or '/violence/' in lower_path:
                        violence_paths.append(full_path)
                    elif '\\nonviolence\\' in lower_path or '/nonviolence/' in lower_path:
                        nonviolence_paths.append(full_path)

    print(f"Total Unique Videos Found: {len(violence_paths) + len(nonviolence_paths)} (Violence: {len(violence_paths)}, NonViolence: {len(nonviolence_paths)})")

    if max_samples and max_samples < (len(violence_paths) + len(nonviolence_paths)):
        half = max_samples // 2
        video_paths = violence_paths[:half] + nonviolence_paths[:max_samples - half]
        print(f"Subsampling {len(video_paths)} videos ({len(violence_paths[:half])} Violence, {len(nonviolence_paths[:max_samples - half])} NonViolence) for inference.")
    else:
        video_paths = violence_paths + nonviolence_paths

    if len(video_paths) == 0:
        print("[ERROR] No video files found in archive path!")
        return

    # 2. Load Model
    print("\nLoading model weights...")
    start_load_t = time.time()
    model = custome_X3D(num_classes=2)
    model = load_model(model, model_path, device)
    model.eval()
    print(f"Model loaded successfully in {time.time() - start_load_t:.2f}s!")

    # 3. Create DataLoader
    dataset = VideoInferenceDataset(video_paths, num_frames=16, spatial_size=224)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # 4. Inference Loop
    print("\nStarting video inference...")
    results = []
    y_true = []
    y_pred = []
    y_prob_violence = []

    start_time = time.time()
    processed_count = 0

    # Model output mapping: Class 0 = NonViolence, Class 1 = Violence
    class_names = {0: "NonViolence", 1: "Violence"}

    with torch.no_grad():
        for b_idx, (clips, labels, paths, valids) in enumerate(loader):
            b_start_t = time.time()
            clips = clips.to(device)
            outputs = model(clips) # ResNetBasicHead outputs Softmax probabilities directly

            b_latency = (time.time() - b_start_t) * 1000 # ms
            per_item_latency = b_latency / len(clips)

            probs = outputs.cpu().numpy() # [B, 2]: probs[:, 0] = NonViolence, probs[:, 1] = Violence

            for i in range(len(clips)):
                video_path = paths[i]
                target_label = labels[i].item()
                valid = valids[i].item()

                prob_nv = float(probs[i][0])  # NonViolence prob (class 0)
                prob_v = float(probs[i][1])   # Violence prob (class 1)

                # Prediction logic using threshold for Violence
                pred_label = 1 if prob_v >= threshold else 0
                pred_name = class_names[pred_label]
                target_name = class_names.get(target_label, "Unknown")

                result_entry = {
                    "video_path": video_path,
                    "filename": os.path.basename(video_path),
                    "valid": valid,
                    "target_label": target_label,
                    "target_name": target_name,
                    "predicted_label": pred_label,
                    "predicted_name": pred_name,
                    "prob_violence": round(prob_v, 6),
                    "prob_non_violence": round(prob_nv, 6),
                    "latency_ms": round(per_item_latency, 2)
                }
                results.append(result_entry)

                if target_label in (0, 1) and valid:
                    y_true.append(target_label)
                    y_pred.append(pred_label)
                    y_prob_violence.append(prob_v)

                processed_count += 1

            if (b_idx + 1) % 5 == 0 or (b_idx + 1) == len(loader):
                elapsed = time.time() - start_time
                fps = processed_count / elapsed if elapsed > 0 else 0
                print(f"Processed {processed_count}/{len(video_paths)} videos [{processed_count/len(video_paths)*100:.1f}%] - Speed: {fps:.2f} v/s")

    total_time = time.time() - start_time
    print(f"\nCompleted inference on {processed_count} videos in {total_time:.2f}s ({total_time/processed_count:.2f}s per video).")

    # 5. Calculate Metrics
    metrics = {}
    if len(y_true) > 0:
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        # Label 1 is Violence, Label 0 is NonViolence
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fn = np.sum((y_true == 1) & (y_pred == 0))

        accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics = {
            "total_evaluated": len(y_true),
            "accuracy": round(float(accuracy), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "confusion_matrix": {
                "TP_Violence": int(tp),
                "FP_Violence": int(fp),
                "TN_NonViolence": int(tn),
                "FN_NonViolence": int(fn)
            }
        }

        print("\n" + "=" * 50)
        print("             EVALUATION METRICS SUMMARY")
        print("=" * 50)
        print(f"Total Evaluated Videos : {metrics['total_evaluated']}")
        print(f"Accuracy               : {metrics['accuracy'] * 100:.2f}%")
        print(f"Precision (Violence)   : {metrics['precision'] * 100:.2f}%")
        print(f"Recall (Violence)      : {metrics['recall'] * 100:.2f}%")
        print(f"F1-Score (Violence)    : {metrics['f1_score']:.4f}")
        print("-" * 50)
        print("Confusion Matrix:")
        print(f"  True Violence (TP)     : {tp}")
        print(f"  False Violence (FP)    : {fp}")
        print(f"  True NonViolence (TN)  : {tn}")
        print(f"  False NonViolence (FN) : {fn}")
        print("=" * 50)

    # 6. Save JSON
    output_data = {
        "metadata": {
            "archive_dir": archive_dir,
            "model_path": model_path,
            "threshold": threshold,
            "total_videos": len(results),
            "inference_duration_sec": round(total_time, 2),
            "device": str(device)
        },
        "metrics": metrics,
        "results": results
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\nInference results saved to: {os.path.abspath(output_json)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Violence Detection Inference on Video Archive")
    parser.add_argument("--archive_dir", type=str, default=r"c:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\archive", help="Path to archive directory")
    parser.add_argument("--model_path", type=str, default=r"c:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\src\CodeBase\Final_Deployment\model.pth", help="Path to model.pth")
    parser.add_argument("--output", type=str, default="inference_results.json", help="Path to save output JSON")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size for inference")
    parser.add_argument("--max_samples", type=int, default=None, help="Maximum number of video samples to process")
    parser.add_argument("--threshold", type=float, default=0.5, help="Violence classification probability threshold")

    args = parser.parse_args()
    run_inference(
        archive_dir=args.archive_dir,
        model_path=args.model_path,
        output_json=args.output,
        batch_size=args.batch_size,
        max_samples=args.max_samples,
        threshold=args.threshold
    )
