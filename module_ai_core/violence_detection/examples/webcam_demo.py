"""
Webcam Demo for Real-Time Violence Detection.

Usage:
    python examples/webcam_demo.py [--cam 0] [--threshold 0.4]
"""

from __future__ import annotations

import argparse
import sys
import time
import cv2
from loguru import logger

from violence_detection import ViolenceDetectionConfig, ViolenceDetector, VideoStream


def main():
    parser = argparse.ArgumentParser(description="Webcam Violence Detection Demo")
    parser.add_argument("--cam", type=int, default=0, help="Webcam device index (default: 0)")
    parser.add_argument("--threshold", type=float, default=0.4, help="Violence threshold (default: 0.4)")
    parser.add_argument("--device", type=str, default="auto", help="Device 'auto', 'cuda', 'cpu'")
    args = parser.parse_args()

    config = ViolenceDetectionConfig(
        violence_threshold=args.threshold,
        device=args.device,
    )

    logger.info("Initializing ViolenceDetector for webcam demo...")
    detector = ViolenceDetector(config)

    logger.info(f"Opening webcam device index: {args.cam}")
    stream = VideoStream(source=args.cam)

    fps_display = 0.0
    last_frame_time = time.time()
    last_prediction = None

    try:
        with stream as vs:
            window_frames = []
            frame_counter = 0

            for frame, _ in vs:
                curr_time = time.time()
                dt = curr_time - last_frame_time
                if dt > 0:
                    fps_display = 0.9 * fps_display + 0.1 * (1.0 / dt)
                last_frame_time = curr_time

                window_frames.append(frame)
                if len(window_frames) > config.clip_length:
                    window_frames.pop(0)

                # Run prediction according to frame stride
                if len(window_frames) == config.clip_length:
                    frame_counter += 1
                    if frame_counter % config.frame_stride == 0 or frame_counter == 1:
                        last_prediction = detector.predict_clip(window_frames)

                # Rendering overlay on output frame
                display_frame = frame.copy()
                h, w, _ = display_frame.shape

                # Text annotations
                device_str = f"Device: {detector.device.type.upper()}"
                fps_str = f"FPS: {fps_display:.1f}"

                if last_prediction is None:
                    status_str = "BUFFERING CLIPS..."
                    color = (255, 255, 255)
                    prob_str = "Prob: --"
                else:
                    prob = last_prediction.confidence
                    if last_prediction.violence:
                        status_str = f"VIOLENCE ALERT! ({prob:.2f})"
                        color = (0, 0, 255)  # Red
                    else:
                        status_str = f"Normal ({prob:.2f})"
                        color = (0, 255, 0)  # Green
                    prob_str = f"Prob: {prob:.4f} (raw: {last_prediction.raw_probability:.4f})"

                # Draw overlay bar
                cv2.rectangle(display_frame, (0, 0), (w, 60), (0, 0, 0), -1)

                cv2.putText(
                    display_frame,
                    status_str,
                    (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    color,
                    2,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    display_frame,
                    f"{fps_str} | {device_str} | {prob_str}",
                    (15, 52),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )

                cv2.imshow("SafeSchool AI - Violence Detection (Webcam Demo)", display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):  # ESC or q
                    logger.info("User quit webcam demo.")
                    break

    except Exception as err:
        logger.error(f"Error running webcam demo: {err}")
    finally:
        cv2.destroyAllWindows()
        logger.info("Webcam demo finished.")


if __name__ == "__main__":
    main()
