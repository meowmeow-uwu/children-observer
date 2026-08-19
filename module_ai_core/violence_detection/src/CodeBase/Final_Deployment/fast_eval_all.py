# fast_eval_all.py
import os
import sys
import time
import json
import argparse
import numpy as np
import cv2
import torch
from torchvision import transforms
from concurrent.futures import ThreadPoolExecutor
from model_utils import custome_X3D, load_model

# Standard ImageNet / Video Preprocessing
transform_pipeline = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize((224, 224), antialias=True),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def extract_video_tensor(item, num_frames=16):
    """
    Decodes video and extracts uniform 16-frame clip tensor (C, T, H, W).
    item: (video_path, label, class_name)
    """
    path, label, cname = item
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None, path, label, cname, False

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return None, path, label, cname, False

    if total_frames <= num_frames:
        target_indices = set(range(total_frames))
    else:
        target_indices = set(np.linspace(0, total_frames - 1, num_frames, dtype=int))

    frames = []
    frame_idx = 0
    while cap.isOpened() and len(frames) < num_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in target_indices:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(transform_pipeline(frame_rgb))
        frame_idx += 1
    cap.release()

    if len(frames) == 0:
        return None, path, label, cname, False

    while len(frames) < num_frames:
        frames.append(frames[-1])
    frames = frames[:num_frames]

    clip_tensor = torch.stack(frames).permute(1, 0, 2, 3).float()  # (C, T, H, W)
    return clip_tensor, path, label, cname, True

def scan_archive(archive_dir):
    """
    Discovers all unique videos in archive.
    """
    v_dict = {}
    nv_dict = {}

    for root, _, files in os.walk(archive_dir):
        for f in files:
            if f.lower().endswith(('.mp4', '.avi', '.mkv')):
                full_p = os.path.join(root, f)
                lower_p = full_p.lower()
                bname = f.lower()

                if '\\violence\\' in lower_p or '/violence/' in lower_p:
                    if bname not in v_dict:
                        v_dict[bname] = full_p
                elif '\\nonviolence\\' in lower_p or '/nonviolence/' in lower_p:
                    if bname not in nv_dict:
                        nv_dict[bname] = full_p

    video_items = []
    # Class 0: NonViolence, Class 1: Violence
    for bname, p in sorted(nv_dict.items()):
        video_items.append((p, 0, "NonViolence"))
    for bname, p in sorted(v_dict.items()):
        video_items.append((p, 1, "Violence"))

    return video_items, len(nv_dict), len(v_dict)

def calculate_auc(y_true, y_scores):
    """
    Calculates Area Under ROC Curve using trapezoidal rule (NumPy 1.x & 2.x compatible).
    """
    desc_score_indices = np.argsort(y_scores, kind="mergesort")[::-1]
    y_true_sorted = y_true[desc_score_indices]
    y_score_sorted = y_scores[desc_score_indices]

    distinct_indices = np.where(np.diff(y_score_sorted))[0]
    threshold_idxs = np.r_[distinct_indices, y_true_sorted.size - 1]

    tps = np.cumsum(y_true_sorted)[threshold_idxs]
    fps = 1 + threshold_idxs - tps

    tps = np.r_[0, tps]
    fps = np.r_[0, fps]

    if fps[-1] <= 0 or tps[-1] <= 0:
        return 0.5

    fpr = fps / fps[-1]
    tpr = tps / tps[-1]
    
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(tpr, fpr))
    elif hasattr(np, "trapz"):
        return float(np.trapz(tpr, fpr))
    else:
        return float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) / 2.0))

def run_evaluation(archive_dir, model_path, output_json="final_evaluation_report.json", batch_size=32, num_threads=8):
    cpu_count = os.cpu_count() or 4
    torch.set_num_threads(max(1, cpu_count - 1))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 84, flush=True)
    print("        COMPREHENSIVE VIOLENCE DETECTION BENCHMARK & DATASET INFERENCE", flush=True)
    print("=" * 84, flush=True)
    print(f"Archive Directory      : {archive_dir}", flush=True)
    print(f"Model Checkpoint Path  : {model_path}", flush=True)
    print(f"Compute Device         : {device} (PyTorch Threads: {torch.get_num_threads()})", flush=True)
    print(f"Parallel Worker Threads: {num_threads}", flush=True)
    print(f"Inference Batch Size   : {batch_size}", flush=True)

    # 1. Dataset Scan
    video_items, num_nv, num_v = scan_archive(archive_dir)
    total_videos = len(video_items)
    print(f"\n[Dataset Structure]", flush=True)
    print(f"  • Unique NonViolence Videos: {num_nv}", flush=True)
    print(f"  • Unique Violence Videos   : {num_v}", flush=True)
    print(f"  • Total Dataset Size       : {total_videos} videos", flush=True)

    if total_videos == 0:
        print("[ERROR] No video files found in dataset archive!", flush=True)
        return

    # 2. Load Model
    print(f"\n[Loading Model Checkpoint]", flush=True)
    t_load0 = time.time()
    model = custome_X3D(num_classes=2)
    model = load_model(model, model_path, device)
    model.eval()
    print(f"  • Model loaded successfully in {time.time() - t_load0:.2f}s", flush=True)

    checkpoint_file = "inference_checkpoint.json"
    results = []
    y_true_list = []
    y_prob_v_list = []
    y_prob_nv_list = []
    latencies = []

    # Check if checkpoint already exists
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                results = json.load(f)
            print(f"  • Found existing checkpoint with {len(results)} videos!", flush=True)
            for r in results:
                if r.get("valid_video", True):
                    y_true_list.append(r["ground_truth_label"])
                    y_prob_v_list.append(r["prob_violence"])
                    y_prob_nv_list.append(r["prob_non_violence"])
                    latencies.append(r.get("latency_ms", 0.0))
        except Exception as e:
            print(f"  • Could not load checkpoint ({e}), starting fresh.", flush=True)
            results = []

    t_eval_start = time.time()
    num_batches = (total_videos + batch_size - 1) // batch_size
    processed_count = len(results)

    if processed_count < total_videos:
        print(f"\n[Starting Parallel Video Decoding & Batch Inference]", flush=True)
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            for b_i in range(num_batches):
                start_idx = b_i * batch_size
                end_idx = min((b_i + 1) * batch_size, total_videos)
                if end_idx <= len(results):
                    continue

                b_items = video_items[start_idx:end_idx]

                # Extract batch videos in parallel
                t_extract0 = time.time()
                extracted_batch = list(executor.map(extract_video_tensor, b_items))
                t_extract1 = time.time()

                valid_tensors = []
                batch_meta = []
                for tensor, p, label, cname, valid in extracted_batch:
                    if valid and tensor is not None:
                        valid_tensors.append(tensor)
                        batch_meta.append((p, label, cname, valid))
                    else:
                        # dummy tensor for invalid video
                        valid_tensors.append(torch.zeros(3, 16, 224, 224))
                        batch_meta.append((p, label, cname, False))

                stacked_clips = torch.stack(valid_tensors).to(device)

                # Model Forward Pass
                t_inf0 = time.time()
                with torch.no_grad():
                    outputs = model(stacked_clips) # Outputs Softmax [B, 2]
                t_inf1 = time.time()

                per_vid_ms = (t_inf1 - t_extract0) * 1000.0 / len(b_items)
                probs = outputs.cpu().numpy()

                for idx_in_b in range(len(b_items)):
                    p, target_lbl, target_name, valid = batch_meta[idx_in_b]
                    p_nv = float(probs[idx_in_b][0])
                    p_v = float(probs[idx_in_b][1])

                    res_item = {
                        "video_path": p,
                        "filename": os.path.basename(p),
                        "ground_truth_label": target_lbl,
                        "ground_truth_name": target_name,
                        "prob_non_violence": round(p_nv, 6),
                        "prob_violence": round(p_v, 6),
                        "valid_video": valid,
                        "latency_ms": round(per_vid_ms, 2)
                    }
                    results.append(res_item)

                    if valid:
                        y_true_list.append(target_lbl)
                        y_prob_v_list.append(p_v)
                        y_prob_nv_list.append(p_nv)
                        latencies.append(per_vid_ms)

                    processed_count += 1

                elapsed = time.time() - t_eval_start
                vps = (processed_count - len(results) + len(b_items)) / elapsed if elapsed > 0 else 0
                eta = (total_videos - processed_count) / vps if vps > 0 else 0
                pct = (processed_count / total_videos) * 100
                print(f"  • Progress: {processed_count:4d}/{total_videos} ({pct:5.1f}%) | Speed: {vps:5.1f} videos/s | ETA: {eta:5.1f}s | Batch {b_i+1}/{num_batches}", flush=True)

                # Save checkpoint periodically
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(results, f)

    total_eval_duration = time.time() - t_eval_start
    print(f"\n[Completed inference on {processed_count} videos in {total_eval_duration:.2f}s ({total_eval_duration/total_videos:.3f}s per video average)]", flush=True)

    # 4. Detailed Statistical & Metrics Calculation
    y_true = np.array(y_true_list)
    y_prob_v = np.array(y_prob_v_list)
    y_prob_nv = np.array(y_prob_nv_list)

    roc_auc = calculate_auc(y_true, y_prob_v)

    # Threshold sweeps from 0.1 to 0.9
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    eval_by_threshold = {}

    for th in thresholds:
        y_pred = (y_prob_v >= th).astype(int)

        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        acc = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0
        prec_v = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec_v = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_v = 2 * prec_v * rec_v / (prec_v + rec_v) if (prec_v + rec_v) > 0 else 0.0

        prec_nv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        rec_nv = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1_nv = 2 * prec_nv * rec_nv / (prec_nv + rec_nv) if (prec_nv + rec_nv) > 0 else 0.0

        macro_f1 = (f1_v + f1_nv) / 2.0

        eval_by_threshold[f"{th:.2f}"] = {
            "threshold": th,
            "accuracy": round(float(acc), 4),
            "macro_f1": round(float(macro_f1), 4),
            "violence": {
                "precision": round(float(prec_v), 4),
                "recall": round(float(rec_v), 4),
                "f1_score": round(float(f1_v), 4),
                "support": int(np.sum(y_true == 1)),
                "true_positives": tp,
                "false_negatives": fn
            },
            "non_violence": {
                "precision": round(float(prec_nv), 4),
                "recall": round(float(rec_nv), 4),
                "f1_score": round(float(f1_nv), 4),
                "support": int(np.sum(y_true == 0)),
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

    # Distribution statistics
    v_mask = (y_true == 1)
    nv_mask = (y_true == 0)

    v_probs_on_v = y_prob_v[v_mask]
    v_probs_on_nv = y_prob_v[nv_mask]

    dist_stats = {
        "violence_videos": {
            "mean_prob_violence": round(float(np.mean(v_probs_on_v)), 4),
            "median_prob_violence": round(float(np.median(v_probs_on_v)), 4),
            "std_prob_violence": round(float(np.std(v_probs_on_v)), 4),
            "min_prob_violence": round(float(np.min(v_probs_on_v)), 4),
            "max_prob_violence": round(float(np.max(v_probs_on_v)), 4)
        },
        "non_violence_videos": {
            "mean_prob_violence": round(float(np.mean(v_probs_on_nv)), 4),
            "median_prob_violence": round(float(np.median(v_probs_on_nv)), 4),
            "std_prob_violence": round(float(np.std(v_probs_on_nv)), 4),
            "min_prob_violence": round(float(np.min(v_probs_on_nv)), 4),
            "max_prob_violence": round(float(np.max(v_probs_on_nv)), 4)
        }
    }

    # Identify Top Misclassified Samples
    false_positives = [r for r in results if r["ground_truth_label"] == 0 and r["prob_violence"] >= 0.5]
    false_negatives = [r for r in results if r["ground_truth_label"] == 1 and r["prob_violence"] < 0.5]

    false_positives.sort(key=lambda x: x["prob_violence"], reverse=True)
    false_negatives.sort(key=lambda x: x["prob_violence"], reverse=False)

    # Display Report
    m05 = eval_by_threshold["0.50"]
    print("\n" + "=" * 84, flush=True)
    print("                    FINAL EVALUATION SUMMARY (Threshold = 0.50)", flush=True)
    print("=" * 84, flush=True)
    print(f"Total Valid Videos Evaluated : {len(y_true)} (NonViolence: {np.sum(nv_mask)}, Violence: {np.sum(v_mask)})", flush=True)
    print(f"Overall Accuracy             : {m05['accuracy'] * 100:.2f}%", flush=True)
    print(f"Macro F1-Score               : {m05['macro_f1']:.4f}", flush=True)
    print(f"ROC-AUC Score                : {roc_auc:.4f}", flush=True)
    print("-" * 84, flush=True)
    print(f"{'Class':<15} | {'Precision':<12} | {'Recall':<12} | {'F1-Score':<12} | {'Support'}", flush=True)
    print("-" * 84, flush=True)
    print(f"{'NonViolence':<15} | {m05['non_violence']['precision']*100:6.2f}%     | {m05['non_violence']['recall']*100:6.2f}%     | {m05['non_violence']['f1_score']:6.4f}     | {num_nv}", flush=True)
    print(f"{'Violence':<15} | {m05['violence']['precision']*100:6.2f}%     | {m05['violence']['recall']*100:6.2f}%     | {m05['violence']['f1_score']:6.4f}     | {num_v}", flush=True)
    print("-" * 84, flush=True)
    print("Confusion Matrix Breakdown:", flush=True)
    print(f"  • True Positives (Violence correctly detected)       : {m05['confusion_matrix']['TP_Violence']} / {num_v} ({m05['violence']['recall']*100:.1f}%)", flush=True)
    print(f"  • False Negatives (Violence missed as NonViolence)   : {m05['confusion_matrix']['FN_Violence_as_NV']} / {num_v}", flush=True)
    print(f"  • True Negatives (NonViolence correctly identified)  : {m05['confusion_matrix']['TN_NonViolence']} / {num_nv} ({m05['non_violence']['recall']*100:.1f}%)", flush=True)
    print(f"  • False Positives (NonViolence falsely flagged)      : {m05['confusion_matrix']['FP_NV_as_Violence']} / {num_nv}", flush=True)
    print("=" * 84, flush=True)

    print("\n[Threshold Sensitivity Table]", flush=True)
    print(f"{'Thresh':<8} | {'Accuracy':<10} | {'Macro F1':<10} | {'Prec (V)':<10} | {'Rec (V)':<10} | {'Prec (NV)':<10} | {'Rec (NV)'}", flush=True)
    print("-" * 84, flush=True)
    for th_str, v in eval_by_threshold.items():
        print(f"{th_str:<8} | {v['accuracy']*100:6.2f}%   | {v['macro_f1']:6.4f}   | {v['violence']['precision']*100:6.2f}%   | {v['violence']['recall']*100:6.2f}%   | {v['non_violence']['precision']*100:6.2f}%   | {v['non_violence']['recall']*100:6.2f}%", flush=True)
    print("=" * 84, flush=True)

    # Save to JSON
    output_data = {
        "metadata": {
            "archive_dir": archive_dir,
            "model_path": model_path,
            "total_unique_videos": total_videos,
            "num_violence": num_v,
            "num_non_violence": num_nv,
            "total_inference_duration_sec": round(total_eval_duration, 2),
            "avg_latency_ms": round(float(np.mean(latencies)), 2) if latencies else 0,
            "device": str(device),
            "num_threads": num_threads,
            "batch_size": batch_size
        },
        "roc_auc": round(roc_auc, 4),
        "distribution_statistics": dist_stats,
        "evaluations_by_threshold": eval_by_threshold,
        "misclassifications": {
            "total_false_positives": len(false_positives),
            "top_10_false_positives": false_positives[:10],
            "total_false_negatives": len(false_negatives),
            "top_10_false_negatives": false_negatives[:10]
        },
        "results": results
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved comprehensive JSON report to: {os.path.abspath(output_json)}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=str, default=r"C:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\archive")
    parser.add_argument("--model", type=str, default=r"C:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\src\CodeBase\Final_Deployment\model.pth")
    parser.add_argument("--output", type=str, default=r"C:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\src\CodeBase\Final_Deployment\final_evaluation_report.json")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()

    run_evaluation(
        archive_dir=args.archive,
        model_path=args.model,
        output_json=args.output,
        batch_size=args.batch_size,
        num_threads=args.threads
    )
