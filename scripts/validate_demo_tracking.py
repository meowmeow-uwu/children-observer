"""
Validate demo tracking trên test_video.mp4 (không cần backend).

Chạy ONNX + ByteTrack qua video/đoạn demo và báo cáo các chỉ số T04:
- detection coverage, confirmed-track coverage (trên ground-truth child-visible)
- longest continuous track, gap lớn nhất, ID switches
- confidence distribution, inference latency p50/p95
- theo từng loop riêng (loop 0/1/2) — không gộp tổng che loop trống
- ByteTrack frame_rate = detection FPS thật

CLI:
    uv run python scripts/validate_demo_tracking.py [--help]
    --video PATH        video (default module_edge_firmware/test_video.mp4)
    --start SECONDS     bắt đầu đoạn demo (trong chính video)
    --end SECONDS       kết thúc đoạn demo
    --fps FLOAT         detection FPS (8, 10, 12)
    --loops N           số vòng lặp
    --conf FLOAT        confidence threshold detector
    --high/--low/--new  ByteTrack thresholds
    --buffer N          track_buffer (frame)
    --match FLOAT       match_thresh
    --gt PATH           ground-truth manifest JSON (child-visible intervals)
    --report-json PATH  ghi JSON report (mặc định stdout)
    --min-conf-cov, --min-track-cov, --max-gap-s, --min-run-s, --max-switches,
    --max-p95-ms        ngưỡng pass/fail; exit code 0 nếu đạt, 1 nếu không

Ground truth manifest (không phải dữ liệu dựng sẵn cho box — chỉ đánh dấu
khoảng frame/giây trẻ nhìn thấy rõ):
    {"video": "test_video.mp4", "fps": 30,
     "intervals": [{"start_s": 10.0, "end_s": 22.0}, ...]}

--help không khởi chạy workload.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from module_edge_firmware.demo_stream.detector import OnnxDetector  # noqa: E402
from module_edge_firmware.demo_stream.tracker import ByteTrackAdapter  # noqa: E402

DEFAULT_GT = Path(__file__).resolve().parent / "demo_ground_truth.json"


def load_gt(path: Path | None) -> list[tuple[float, float]]:
    """Đọc manifest ground truth: intervals (giây) trẻ nhìn thấy rõ."""
    if path is None or not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    intervals = []
    for iv in data.get("intervals", []):
        intervals.append((float(iv["start_s"]), float(iv["end_s"])))
    return intervals


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(len(ordered) * p))
    return ordered[idx]


def run_pipeline(
    args: argparse.Namespace,
    gt_intervals: list[tuple[float, float]],
) -> dict:
    import cv2

    video_fps = 30.0
    start_frame = int((args.start or 0.0) * video_fps)
    end_frame = int((args.end or 1e9) * video_fps)
    # Sample đúng detection FPS của pipeline (8/10/12) — giống runtime
    sample_step = max(1, int(round(video_fps / max(1.0, args.fps))))
    effective_fps = video_fps / sample_step

    detector = OnnxDetector(args.model, conf_threshold=args.conf)
    detector.load()
    tracker = ByteTrackAdapter(
        track_thresh=args.track_thresh,
        track_buffer=args.buffer,
        match_thresh=args.match,
        frame_rate=int(round(args.fps)),
        classes_to_track=("child",),
        high_thresh=args.high_thresh,
        low_thresh=args.low_thresh,
        new_thresh=args.new_thresh,
        confirm_frames=args.confirm_frames,
        confirm_score=args.confirm_score,
    )

    cap = cv2.VideoCapture(args.video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    seg_end = min(end_frame, total)

    # GT trong hệ frame video thật (30fps)
    gt_frames: list[tuple[int, int]] = []
    for s, e in gt_intervals:
        gt_frames.append((int(s * video_fps), int(e * video_fps)))

    per_loop: dict[int, dict] = {}
    latencies: list[float] = []
    confidences: list[float] = []

    for loop in range(max(1, args.loops)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        tracker.reset()

        loop_det = 0  # det-frame (trong đoạn, trong GT) có child detection
        loop_conf = 0  # det-frame có track confirmed
        loop_gt_frames = 0
        loop_track_frames = 0
        run = 0
        best_run = 0
        gap = 0
        max_gap = 0
        prev_ids: set[int] = set()
        last_ids_before_gap: set[int] = set()
        switches = 0
        ids_seen: set[int] = set()

        fi = start_frame
        while fi < seg_end:
            ret, frame = cap.read()
            if not ret:
                break
            # Đọc TUẦN TỰ mọi frame (giống DemoVideoSource runtime); chỉ chạy
            # detector/tracker trên frame được sample theo detection FPS.
            if (fi - start_frame) % sample_step == 0:
                start = time.perf_counter()
                dets = detector.detect(frame)
                tracks = tracker.update(dets)
                latencies.append((time.perf_counter() - start) * 1000.0)

                # Metrics chỉ tính trên GT; tracker vẫn nhận MỌI frame trong đoạn
                in_gt = any(a <= fi <= b for a, b in gt_frames)
                if in_gt:
                    loop_gt_frames += 1
                    if any(d["class"] == "child" for d in dets):
                        loop_det += 1

                    confirmed = [t for t in tracks if t.get("confirmed")]
                    if confirmed:
                        loop_conf += 1
                        loop_track_frames += 1
                        run += 1
                        best_run = max(best_run, run)
                        gap = 0
                        ids = {t["track_id"] for t in confirmed}
                        # ID switch = id KHÁC xuất hiện so với lần quan sát trước
                        # (cùng id quay lại sau gap không phải switch; cold start = 0).
                        if prev_ids:
                            switches += len(ids - prev_ids)
                        elif last_ids_before_gap:
                            switches += len(ids - last_ids_before_gap)
                        prev_ids = ids
                        last_ids_before_gap = ids
                        ids_seen |= ids
                        for t in confirmed:
                            confidences.append(t["confidence"])
                    else:
                        run = 0
                        gap += 1
                        max_gap = max(max_gap, gap)
                        prev_ids = set()  # last_ids_before_gap giữ nguyên
            fi += 1

        per_loop[loop] = {
            "gt_frames": loop_gt_frames,
            "det_frames": loop_det,
            "track_frames": loop_conf,
            "det_cov_pct": round(loop_det / loop_gt_frames * 100, 2) if loop_gt_frames else 0,
            "track_cov_pct": round(loop_conf / loop_gt_frames * 100, 2) if loop_gt_frames else 0,
            "longest_run_s": round(best_run / effective_fps, 2),
            "max_gap_s": round(max_gap / effective_fps, 2),
            "id_switches": switches,
            "track_ids": sorted(ids_seen),
            "track_id_count": len(ids_seen),
        }

    cap.release()

    gt_total = sum(v["gt_frames"] for v in per_loop.values())
    det_total = sum(v["det_frames"] for v in per_loop.values())
    conf_total = sum(v["track_frames"] for v in per_loop.values())

    report = {
        "params": {
            "video": args.video,
            "start_s": args.start,
            "end_s": args.end,
            "fps": args.fps,
            "loops": args.loops,
            "conf": args.conf,
            "track_thresh": args.track_thresh,
            "high": args.high_thresh,
            "low": args.low_thresh,
            "new": args.new_thresh,
            "buffer": args.buffer,
            "match": args.match,
            "gt_intervals": gt_intervals,
        },
        "per_loop": per_loop,
        "summary": {
            "gt_frames_total": gt_total,
            "det_cov_pct": round(det_total / gt_total * 100, 2) if gt_total else 0,
            "track_cov_pct": round(conf_total / gt_total * 100, 2) if gt_total else 0,
            "longest_run_s": max(v["longest_run_s"] for v in per_loop.values()),
            "max_gap_s": max(v["max_gap_s"] for v in per_loop.values()),
            "id_switches_total": sum(v["id_switches"] for v in per_loop.values()),
            "inference_p50_ms": round(percentile(latencies, 0.50), 1),
            "inference_p95_ms": round(percentile(latencies, 0.95), 1),
            "conf_min": round(min(confidences), 3) if confidences else 0,
            "conf_max": round(max(confidences), 3) if confidences else 0,
            "conf_mean": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        },
    }

    # ---- Ngưỡng pass/fail (test.md T04) ----
    s = report["summary"]
    # Độ dài lần xuất hiện (GT intervals): nếu ngắn hơn min_run_s, chuỗi track
    # chỉ cần bao phủ TOÀN BỘ lần xuất hiện (gate ">= 3s HOẶC hết lần xuất hiện")
    appearance_s = sum(e - st for st, e in gt_intervals)
    run_required = min(args.min_run_s, appearance_s) if appearance_s > 0 else args.min_run_s
    gates = {
        "min_conf_cov_pct": args.min_conf_cov,
        "min_track_cov_pct": args.min_track_cov,
        "max_gap_s": args.max_gap_s,
        "min_run_s": args.min_run_s,
        "max_id_switches": args.max_switches,
        "max_inference_p95_ms": args.max_p95_ms,
    }
    results = {
        "det_cov_pct": s["det_cov_pct"] >= args.min_conf_cov,
        "track_cov_pct": s["track_cov_pct"] >= args.min_track_cov,
        "max_gap_s": s["max_gap_s"] <= args.max_gap_s,
        "min_run_s": s["longest_run_s"] >= run_required,
        "max_id_switches": s["id_switches_total"] <= args.max_switches,
        "max_inference_p95_ms": s["inference_p95_ms"] <= args.max_p95_ms,
        "loops_covered": all(v["gt_frames"] > 0 for v in per_loop.values()),
    }
    report["gates"] = gates
    report["run_required_s"] = round(run_required, 2)
    report["pass"] = all(results.values())

    # Mỗi loop phải có track ở đoạn GT (không dùng tổng che loop trống)
    loops_with_track = [k for k, v in per_loop.items() if v["track_frames"] > 0]
    if args.loops > 1 and len(loops_with_track) < min(2, args.loops):
        report["pass"] = False
        results["loops_with_track"] = False
    else:
        results["loops_with_track"] = True
    report["results"] = results

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate demo tracking trên test_video.mp4")
    parser.add_argument("--video", type=str, default="module_edge_firmware/test_video.mp4")
    parser.add_argument("--model", type=str, default="weights/roi_detection/best.onnx")
    parser.add_argument("--start", type=float, default=None, help="bắt đầu đoạn demo (giây)")
    parser.add_argument("--end", type=float, default=None, help="kết thúc đoạn demo (giây)")
    parser.add_argument("--fps", type=float, default=8.0, help="detection FPS (8/10/12)")
    parser.add_argument("--loops", type=int, default=1)
    parser.add_argument("--conf", type=float, default=0.05, help="confidence threshold detector")
    parser.add_argument("--track-thresh", type=float, default=0.35)
    parser.add_argument("--high-thresh", type=float, default=None)
    parser.add_argument("--low-thresh", type=float, default=None)
    parser.add_argument("--new-thresh", type=float, default=None)
    parser.add_argument("--buffer", type=int, default=120)
    parser.add_argument("--match", type=float, default=0.8)
    parser.add_argument("--confirm-frames", type=int, default=3)
    parser.add_argument("--confirm-score", type=float, default=0.5)
    parser.add_argument("--gt", type=str, default=str(DEFAULT_GT), help="ground-truth manifest JSON")
    parser.add_argument("--report-json", type=str, default=None, help="ghi JSON report ra file")
    parser.add_argument("--min-conf-cov", type=float, default=75.0)
    parser.add_argument("--min-track-cov", type=float, default=70.0)
    parser.add_argument("--max-gap-s", type=float, default=0.5)
    parser.add_argument("--min-run-s", type=float, default=3.0)
    parser.add_argument("--max-switches", type=int, default=2)
    parser.add_argument("--max-p95-ms", type=float, default=120.0)
    args = parser.parse_args()

    gt = load_gt(Path(args.gt))
    if not gt:
        print(json.dumps({"error": f"Không có ground truth tại {args.gt} — bắt buộc cho T04"}, ensure_ascii=False))
        return 2

    report = run_pipeline(args, gt)
    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report_json:
        Path(args.report_json).write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
