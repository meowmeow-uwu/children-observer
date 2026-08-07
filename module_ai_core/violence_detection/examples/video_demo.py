"""
Video File Demo for Violence Detection.

Usage:
    python examples/video_demo.py --video sample.mp4 [--threshold 0.4] [--no-display]
"""

from __future__ import annotations

import argparse
import sys
import time
import cv2
from loguru import logger

from violence_detection import ViolenceDetectionConfig, ViolenceDetector, VideoStream


def main():
    parser = argparse.ArgumentParser(description="Video File Violence Detection Demo")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--threshold", type=float, default=0.4, help="Violence threshold (default: 0.4)")
    parser.add_argument("--device", type=str, default="auto", help="Device 'auto', 'cuda', 'cpu'")
    parser.add_argument("--no-display", action="store_true", help="Run without rendering OpenCV window")
    args = parser.parse_args()

    config = ViolenceDetectionConfig(
        violence_threshold=args.threshold,
        device=args.device,
    )

    logger.info("Initializing ViolenceDetector...")
    detector = ViolenceDetector(config)

    total_clips = 0
    violent_clips = 0
    max_prob = 0.0
    latencies = []

    logger.info(f"Processing video: {args.video}")
    stream = VideoStream(source=args.video)

    try:
        with stream as vs:
            window_frames = []
            frame_counter = 0

            for frame, timestamp in vs:
                window_frames.append(frame)
                if len(window_frames) > config.clip_length:
                    window_frames.pop(0)

                if len(window_frames) == config.clip_length:
                    frame_counter += 1
                    if frame_counter % config.frame_stride == 0 or frame_counter == 1:
                        pred = detector.predict_clip(window_frames, timestamp=timestamp)

                        total_clips += 1
                        if pred.violence:
                            violent_clips += 1
                        if pred.confidence > max_prob:
                            max_prob = pred.confidence
                        if pred.inference_ms is not None:
                            latencies.append(pred.inference_ms)

                        # Render GUI if not disabled
                        if not args.no_display:
                            display_frame = frame.copy()
                            h, w, _ = display_frame.shape

                            color = (0, 0, 255) if pred.violence else (0, 255, 0)
                            status_text = "VIOLENCE ALERT!" if pred.violence else "Normal"

                            cv2.rectangle(display_frame, (0, 0), (w, 50), (0, 0, 0), -1)
                            cv2.putText(
                                display_frame,
                                f"{status_text} | Prob: {pred.confidence:.4f}",
                                (15, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                color,
                                2,
                            )

                            cv2.imshow("SafeSchool AI - Video Demo", display_frame)
                            key = cv2.waitKey(1) & 0xFF
                            if key in (27, ord("q")):
                                logger.info("Demo cancelled by user.")
                                break

    except Exception as err:
        logger.error(f"Error processing video file: {err}")
    finally:
        if not args.no_display:
            cv2.destroyAllWindows()

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 50)
    print("           VIDEO DETECTION SUMMARY           ")
    print("=" * 50)
    print(f"  Processed clips          : {total_clips}")
    print(f"  Violent clips detected   : {violent_clips}")
    print(f"  Max violence probability : {max_prob:.4f}")
    print(f"  Average inference latency: {avg_latency:.2f} ms")
    print(f"  Device used              : {detector.device.type.upper()}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
