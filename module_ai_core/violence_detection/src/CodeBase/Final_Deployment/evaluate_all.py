# evaluate_all.py
import os
import sys
import time
import json
import argparse
import numpy as np
import cv2
import torch
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from model_utils import custome_X3D, load_model

class FastVideoDataset(Dataset):
    def __init__(self, video_items, num_frames=16, spatial_size=224):
        """
        video_items: list of (video_path, label, class_name)
        label: 0 for NonViolence, 1 for Violence
        """
        self.video_items = video_items
        self.num_frames = num_frames
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((spatial_size, spatial_size)),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def __len__(self):
        return len(self.video_items)

    def _extract_frames(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return None

        if total_frames <= self.num_frames:
            target_indices = set(range(total_frames))
        else:
            target_indices = set(np.linspace(0, total_frames - 1, self.num_frames, dtype=int))

        frames = []
        frame_idx = 0
        while cap.isOpened() and len(frames) < self.num_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in target_indices:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(self.transform(frame_rgb))
            frame_idx += 1
        cap.release()

        if len(frames) == 0:
            return None

        while len(frames) < self.num_frames:
            frames.append(frames[-1])
        frames = frames[:self.num_frames]
        return torch.stack(frames).permute(1, 0, 2, 3).float() # (C, T, H, W)

    def __getitem__(self, idx):
        path, label, cname = self.video_items[idx]
        clip_tensor = self._extract_frames(path)
        if clip_tensor is None:
            clip_tensor = torch.zeros(3, self.num_frames, 224, 224)
            valid = False
        else:
            valid = True
        return clip_tensor, label, path, cname, valid

def scan_dataset(archive_dir):
    """
    Scans the archive folder, identifies unique videos, and categorizes them into Violence and NonViolence.
    """
    v_dict = {}
    nv_dict = {}

    for root, _, files in os.walk(archive_dir):
        for f in files:
            if f.lower().endswith(('.mp4', '.avi', '.mkv')):
                full_path = os.path.join(root, f)
                lower_p = full_path.lower()
                basename = f.lower()

                if '\\violence\\' in lower_p or '/violence/' in lower_p:
                    if basename not in v_dict:
                        v_dict[basename] = full_path
                elif '\\nonviolence\\' in lower_p or '/nonviolence/' in lower_p:
                    if basename not in nv_dict:
                        nv_dict[basename] = full_path

    video_items = []
    # 0 = NonViolence, 1 = Violence
    for bname, p in sorted(nv_dict.items()):
        video_items.append((p, 0, "NonViolence"))
    for bname, p in sorted(v_dict.items()):
        video_items.append((p, 1, "Violence"))

    return video_items, len(nv_dict), len(v_dict)

def evaluate(archive_dir, model_path, output_json="full_evaluation_results.json", batch_size=16, num_workers=0):
    torch.set_num_threads(max(1, os.cpu_count() - 1 if os.cpu_count() else 4))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 80)
    print("      COMPREHENSIVE VIOLENCE DETECTION DATASET INFERENCE & EVALUATION")
    print("=" * 80)
    print(f"Archive Root Directory : {archive_dir}")
    print(f"Model Checkpoint Path  : {model_path}")
    print(f"Inference Device       : {device} (CPU Threads: {torch.get_num_threads()})")
    print(f"Batch Size             : {batch_size}")

    video_items, num_nv, num_v = scan_dataset(archive_dir)
    print(f"\n[Dataset Structure Analysis]")
    print(f"  • Total Unique NonViolence Videos: {num_nv}")
    print(f"  • Total Unique Violence Videos   : {num_v}")
    print(f"  • Total Video Population         : {len(video_items)}")

    if len(video_items) == 0:
        print("[ERROR] No video files found in the specified archive directory!")
        return

    # Load Model
    print(f"\n[Model Loading]")
    t_start_load = time.time()
    model = custome_X3D(num_classes=2)
    model = load_model(model, model_path, device)
    model.eval()
    print(f"  • PyTorch X3D-M loaded in {time.time() - t_start_load:.2f}s")

    # DataLoader
    dataset = FastVideoDataset(video_items, num_frames=16, spatial_size=224)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=False
    )

    print(f"\n[Running Inference Across All {len(video_items)} Videos...]")
    results = []
    y_true = []
    y_prob_v = []
    y_prob_nv = []
    latencies = []

    t_inference_start = time.time()
    processed = 0

    with torch.no_grad():
        for b_idx, (clips, labels, paths, cnames, valids) in enumerate(loader):
            t_b0 = time.time()
            clips = clips.to(device)
            outputs = model(clips)
            t_b1 = time.time()

            b_latency_ms = (t_b1 - t_b0) * 1000.0
            per_item_ms = b_latency_ms / len(clips)

            probs = outputs.cpu().numpy()

            for i in range(len(clips)):
                p = paths[i]
                target_lbl = labels[i].item()
                target_name = cnames[i]
                valid = valids[i].item()

                p_nv = float(probs[i][0])
                p_v = float(probs[i][1])

                results.append({
                    "video_path": p,
                    "filename": os.path.basename(p),
                    "ground_truth_label": target_lbl,
                    "ground_truth_name": target_name,
                    "prob_non_violence": round(p_nv, 6),
                    "prob_violence": round(p_v, 6),
                    "valid_video": valid,
                    "latency_ms": round(per_item_ms, 2)
                })

                if valid:
                    y_true.append(target_lbl)
                    y_prob_v.append(p_v)
                    y_prob_nv.append(p_nv)
                    latencies.append(per_item_ms)

                processed += 1

            if (b_idx + 1) % 5 == 0 or (b_idx + 1) == len(loader):
                elapsed = time.time() - t_inference_start
                vps = processed / elapsed if elapsed > 0 else 0
                eta_s = (len(video_items) - processed) / vps if vps > 0 else 0
                print(f"  [{processed:4d}/{len(video_items)}] ({processed/len(video_items)*100:5.1f}%) | Speed: {vps:5.2f} vids/sec | ETA: {eta_s:5.1f}s")

    total_time = time.time() - t_inference_start
    print(f"\nInference completed in {total_time:.2f} seconds ({total_time/len(video_items):.3f}s / video average).")

    # Comprehensive Metrics Evaluation across thresholds
    y_true = np.array(y_true)
    y_prob_v = np.array(y_prob_v)
    y_prob_nv = np.array(y_prob_nv)

    thresholds_to_test = [0.3, 0.4, 0.5, 0.6, 0.7]
    threshold_evals = {}

    for th in thresholds_to_test:
        y_pred = (y_prob_v >= th).astype(int)

        # Class 1 = Violence, Class 0 = NonViolence
        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        acc = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
        prec_v = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec_v = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_v = 2 * prec_v * rec_v / (prec_v + rec_v) if (prec_v + rec_v) > 0 else 0

        prec_nv = tn / (tn + fn) if (tn + fn) > 0 else 0
        rec_nv = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1_nv = 2 * prec_nv * rec_nv / (prec_nv + rec_nv) if (prec_nv + rec_nv) > 0 else 0

        macro_f1 = (f1_v + f1_nv) / 2

        threshold_evals[str(th)] = {
            "threshold": th,
            "accuracy": round(float(acc), 4),
            "macro_f1": round(float(macro_f1), 4),
            "violence": {
                "precision": round(float(prec_v), 4),
                "recall": round(float(rec_v), 4),
                "f1_score": round(float(f1_v), 4),
                "true_positives": tp,
                "false_negatives": fn
            },
            "non_violence": {
                "precision": round(float(prec_nv), 4),
                "recall": round(float(rec_nv), 4),
                "f1_score": round(float(f1_nv), 4),
                "true_negatives": tn,
                "false_positives": fp
            },
            "confusion_matrix": {
                "TP_Violence": tp,
                "FN_Violence_as_NV": fn,
                "TN_NonViolence": tn,
                "FP_NV_as_Violence": fp
            }
        }

    # Best default metrics at th=0.5
    default_m = threshold_evals["0.5"]

    print("\n" + "=" * 80)
    print("                    FINAL EVALUATION REPORT & METRICS (Threshold = 0.5)")
    print("=" * 80)
    print(f"Total Evaluated Videos       : {len(y_true)}")
    print(f"Overall Dataset Accuracy     : {default_m['accuracy'] * 100:.2f}%")
    print(f"Macro F1-Score               : {default_m['macro_f1']:.4f}")
    print("-" * 80)
    print(f"{'Class':<15} | {'Precision':<12} | {'Recall':<12} | {'F1-Score':<12} | {'Support'}")
    print("-" * 80)
    print(f"{'NonViolence':<15} | {default_m['non_violence']['precision']*100:6.2f}%     | {default_m['non_violence']['recall']*100:6.2f}%     | {default_m['non_violence']['f1_score']:6.4f}     | {num_nv}")
    print(f"{'Violence':<15} | {default_m['violence']['precision']*100:6.2f}%     | {default_m['violence']['recall']*100:6.2f}%     | {default_m['violence']['f1_score']:6.4f}     | {num_v}")
    print("-" * 80)
    print("Confusion Matrix:")
    print(f"  • True Violence (TP)       : {default_m['confusion_matrix']['TP_Violence']}")
    print(f"  • False NonViolence (FN)    : {default_m['confusion_matrix']['FN_Violence_as_NV']}")
    print(f"  • True NonViolence (TN)    : {default_m['confusion_matrix']['TN_NonViolence']}")
    print(f"  • False Violence (FP)      : {default_m['confusion_matrix']['FP_NV_as_Violence']}")
    print("=" * 80)

    print("\nThreshold Sensitivity Analysis:")
    print(f"{'Threshold':<10} | {'Accuracy':<10} | {'Macro F1':<10} | {'Prec (V)':<10} | {'Rec (V)':<10} | {'Prec (NV)':<10} | {'Rec (NV)'}")
    print("-" * 80)
    for th_str, val in threshold_evals.items():
        print(f"{th_str:<10} | {val['accuracy']*100:6.2f}%   | {val['macro_f1']:6.4f}   | {val['violence']['precision']*100:6.2f}%   | {val['violence']['recall']*100:6.2f}%   | {val['non_violence']['precision']*100:6.2f}%   | {val['non_violence']['recall']*100:6.2f}%")
    print("=" * 80)

    output_payload = {
        "metadata": {
            "archive_dir": archive_dir,
            "model_path": model_path,
            "total_unique_videos": len(video_items),
            "num_violence": num_v,
            "num_non_violence": num_nv,
            "total_inference_time_seconds": round(total_time, 2),
            "avg_latency_ms_per_video": round(float(np.mean(latencies)), 2) if latencies else 0,
            "device": str(device)
        },
        "threshold_evaluations": threshold_evals,
        "results": results
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    print(f"\nAll detailed inference logs and metrics saved to: {os.path.abspath(output_json)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=str, default=r"C:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\archive")
    parser.add_argument("--model", type=str, default=r"C:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\src\CodeBase\Final_Deployment\model.pth")
    parser.add_argument("--output", type=str, default=r"C:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\src\CodeBase\Final_Deployment\full_evaluation_results.json")
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--num_workers", type=int, default=0)
    args = parser.parse_args()

    evaluate(
        archive_dir=args.archive,
        model_path=args.model,
        output_json=args.output,
        batch_size=args.batch_size,
        num_workers=args.num_workers
    )
