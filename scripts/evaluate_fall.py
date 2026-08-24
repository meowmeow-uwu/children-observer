"""Replay fall detection with the same ROI/pose/association path used by edge.

Usage:
  uv run python scripts/evaluate_fall.py --video sample.mp4 --ground-truth ground_truth.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

from module_edge_firmware.demo_stream.detector import OnnxDetector
from module_edge_firmware.demo_stream.fall import (
    FallPoseEstimator,
    FallStateEngine,
    associate_child_poses,
)
from module_edge_firmware.demo_stream.tracker import ByteTrackAdapter


def load_events(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    for event in events:
        if not {"start_s", "end_s", "label"} <= event.keys():
            raise ValueError("Each ground-truth event needs start_s, end_s, label")
    return events


def score(predictions: list[float], events: list[dict]) -> dict:
    positives = [event for event in events if event["label"] == "fall"]
    matched: set[int] = set()
    true_positive = 0
    for prediction in predictions:
        candidate = next(
            (
                index for index, event in enumerate(positives)
                if index not in matched and event["start_s"] <= prediction <= event["end_s"] + 5.0
            ),
            None,
        )
        if candidate is not None:
            matched.add(candidate)
            true_positive += 1
    false_positive = len(predictions) - true_positive
    false_negative = len(positives) - true_positive
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--roi-model", default="weights/roi_detection/best.onnx", type=Path)
    parser.add_argument("--fall-model", default="weights/fall_detection/best-416.onnx", type=Path)
    parser.add_argument("--roi-fps", type=float, default=5.0)
    parser.add_argument("--fall-fps", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=Path("reports/fall-evaluation.json"))
    args = parser.parse_args()

    events = load_events(args.ground_truth)
    detector = OnnxDetector(args.roi_model, conf_threshold=0.05)
    detector.load()
    pose = FallPoseEstimator(args.fall_model, 0.5, 416)
    pose.load()
    tracker = ByteTrackAdapter(frame_rate=round(args.roi_fps), classes_to_track=("child",))
    fall = FallStateEngine(still_seconds=2.0, velocity_threshold=0.15, still_velocity_threshold=0.04)

    capture = cv2.VideoCapture(str(args.video))
    source_fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    roi_step = max(1, round(source_fps / args.roi_fps))
    fall_step = max(1, round(source_fps / args.fall_fps))
    frame_id = 0
    predictions: list[float] = []
    latencies: list[float] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_id % roi_step == 0:
            tracks = tracker.update(detector.detect(frame))
        if frame_id % fall_step == 0:
            started = time.perf_counter()
            for track_id, person in associate_child_poses([t for t in tracks if t.get("confirmed")], pose.predict(frame)):
                annotation, emitted = fall.update(track_id, person.keypoints, frame_id / source_fps * 1000.0)
                if emitted and annotation.state == "confirmed":
                    predictions.append(frame_id / source_fps)
            latencies.append((time.perf_counter() - started) * 1000.0)
        frame_id += 1
    capture.release()

    duration_s = frame_id / source_fps
    result = score(predictions, events)
    result.update({
        "video": str(args.video),
        "duration_s": round(duration_s, 2),
        "predicted_fall_times_s": [round(value, 2) for value in predictions],
        "false_alerts_per_hour": round(result["false_positive"] / max(duration_s / 3600.0, 1 / 3600.0), 3),
        "fall_latency_ms_p50": round(float(np.percentile(latencies, 50)), 1) if latencies else None,
        "fall_latency_ms_p95": round(float(np.percentile(latencies, 95)), 1) if latencies else None,
        "effective_fall_fps": round(len(latencies) / max(duration_s, 0.001), 3),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
