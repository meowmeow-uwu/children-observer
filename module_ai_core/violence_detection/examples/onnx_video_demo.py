"""
ONNX Runtime Video Demo for Violence Detection (Edge / Lightweight Deployment).
Runs inference without requiring PyTorch at runtime.
"""

from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path
import cv2
import numpy as np
from loguru import logger

# Add root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.preprocessing.video import preprocess_frames
from violence_detection.inference.smoothing import TemporalSmoother
from violence_detection.stream.capture import VideoStream


def softmax(x: np.ndarray) -> np.ndarray:
    """Compute softmax values for logits array."""
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / e_x.sum(axis=-1, keepdims=True)


def run_onnx_demo(
    onnx_path: str,
    video_source: str | int,
    threshold: float = 0.4,
    no_display: bool = False,
):
    try:
        import onnxruntime as ort
    except ImportError:
        logger.error("Package 'onnxruntime' is required to run ONNX demo. Install via: pip install onnxruntime")
        sys.exit(1)

    onnx_file = Path(onnx_path)
    if not onnx_file.exists():
        logger.error(f"ONNX model file not found at: {onnx_file}. Please run scripts/export_onnx.py first.")
        sys.exit(1)

    logger.info(f"Loading ONNX model session: {onnx_file}...")
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    session = ort.InferenceSession(str(onnx_file), providers=providers)
    logger.info(f"Active ONNX Execution Provider: {session.get_providers()[0]}")

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    config = ViolenceDetectionConfig(violence_threshold=threshold)
    smoother = TemporalSmoother(
        window_size=config.smoothing_window,
        method=config.smoothing_method,
        min_consecutive=config.alert_min_consecutive,
        threshold=config.violence_threshold,
    )

    logger.info(f"Opening video source: {video_source}")
    window_frames: list[np.ndarray] = []
    frame_counter = 0

    with VideoStream(video_source) as stream:
        for frame, _ in stream:
            window_frames.append(frame)

            if len(window_frames) > config.clip_length:
                window_frames.pop(0)

            smoothed_prob = 0.0
            is_alert = False
            elapsed_ms = 0.0

            if len(window_frames) == config.clip_length:
                frame_counter += 1
                if frame_counter % config.frame_stride == 0 or frame_counter == 1:
                    start_t = time.perf_counter()

                    # Preprocess frames (returns torch Tensor, convert to numpy float32)
                    clip_tensor = preprocess_frames(
                        frames=window_frames,
                        expected_clip_length=config.clip_length,
                        spatial_size=config.spatial_size,
                        mean=config.mean,
                        std=config.std,
                    )
                    input_data = clip_tensor.numpy().astype(np.float32)

                    # ONNX Inference
                    raw_logits = session.run([output_name], {input_name: input_data})[0]
                    probs = softmax(raw_logits)
                    raw_prob = float(probs[0, 1])

                    elapsed_ms = (time.perf_counter() - start_t) * 1000.0
                    smoothed_prob, is_alert = smoother.update(raw_prob)

                    logger.debug(
                        f"ONNX Clip: raw_prob={raw_prob:.4f}, smoothed_prob={smoothed_prob:.4f}, "
                        f"alert={is_alert}, latency={elapsed_ms:.2f}ms"
                    )

            if not no_display:
                display_frame = frame.copy()
                color = (0, 0, 255) if is_alert else (0, 255, 0)
                label = f"VIOLENCE ALERT! ({smoothed_prob:.2f})" if is_alert else f"Normal ({smoothed_prob:.2f})"

                cv2.putText(display_frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                cv2.putText(
                    display_frame,
                    f"Engine: ONNX | Latency: {elapsed_ms:.1f}ms",
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                )

                cv2.imshow("ONNX Violence Detection Demo", display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    logger.info("User interrupted video display. Exiting...")
                    break

    if not no_display:
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="ONNX Runtime Video Demo for Violence Detection")
    parser.add_argument(
        "--model",
        type=str,
        default="weights/x3d_violence.onnx",
        help="Path to exported .onnx model file (default: weights/x3d_violence.onnx)",
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Path to input video file or webcam index (default: webcam 0)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help="Violence threshold (default: 0.4)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable video display window",
    )

    args = parser.parse_args()
    source = int(args.video) if args.video and args.video.isdigit() else (args.video or 0)
    run_onnx_demo(
        onnx_path=args.model,
        video_source=source,
        threshold=args.threshold,
        no_display=args.no_display,
    )


if __name__ == "__main__":
    main()
