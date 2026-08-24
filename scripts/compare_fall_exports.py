"""Compare PyTorch YOLO pose output with an exported ONNX artifact on video frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from module_edge_firmware.demo_stream.fall import FallPoseEstimator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--pt", default="weights/fall_detection/best.pt", type=Path)
    parser.add_argument("--onnx", default="weights/fall_detection/best-416.onnx", type=Path)
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("reports/fall-export-parity.json"))
    args = parser.parse_args()

    pytorch = YOLO(str(args.pt))
    onnx = FallPoseEstimator(args.onnx, conf_threshold=0.05, input_size=416)
    onnx.load()
    capture = cv2.VideoCapture(str(args.video))
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = np.linspace(0, max(total - 1, 0), args.frames, dtype=int)
    rows = []
    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = capture.read()
        if not ok:
            continue
        pt_result = pytorch.predict(frame, conf=0.05, verbose=False)[0]
        pt_count = 0 if pt_result.boxes is None else len(pt_result.boxes)
        onnx_people = onnx.predict(frame)
        rows.append({"frame": int(index), "pt_people": pt_count, "onnx_people": len(onnx_people)})
    capture.release()
    result = {
        "pt": str(args.pt),
        "onnx": str(args.onnx),
        "frames": rows,
        "count_match_rate": round(sum(row["pt_people"] == row["onnx_people"] for row in rows) / max(len(rows), 1), 4),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
