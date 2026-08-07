"""
RTSP Stream Demo for Violence Detection.

Usage:
    python examples/rtsp_demo.py --source "rtsp://user:pass@192.168.1.100:554/stream" [--threshold 0.4]
"""

from __future__ import annotations

import argparse
import sys
import cv2
from loguru import logger

from violence_detection import ViolenceDetectionConfig, ViolenceDetector, VideoStream
from violence_detection.stream.capture import redact_rtsp_url


def main():
    parser = argparse.ArgumentParser(description="RTSP Violence Detection Demo")
    parser.add_argument("--source", type=str, required=True, help="RTSP stream URL (rtsp://...)")
    parser.add_argument("--threshold", type=float, default=0.4, help="Violence threshold (default: 0.4)")
    parser.add_argument("--device", type=str, default="auto", help="Device 'auto', 'cuda', 'cpu'")
    parser.add_argument("--no-display", action="store_true", help="Run without rendering OpenCV window")
    args = parser.parse_args()

    config = ViolenceDetectionConfig(
        violence_threshold=args.threshold,
        device=args.device,
    )

    safe_url = redact_rtsp_url(args.source)
    logger.info(f"Starting RTSP Stream Demo on source: {safe_url}")

    logger.info("Initializing ViolenceDetector...")
    detector = ViolenceDetector(config)

    stream = VideoStream(source=args.source)

    try:
        with stream as vs:
            window_frames = []
            frame_counter = 0

            for frame, timestamp in vs:
                window_frames.append(frame)
                if len(window_frames) > config.clip_length:
                    window_frames.pop(0)

                last_pred = None
                if len(window_frames) == config.clip_length:
                    frame_counter += 1
                    if frame_counter % config.frame_stride == 0 or frame_counter == 1:
                        last_pred = detector.predict_clip(window_frames, timestamp=timestamp)

                if last_pred is not None and last_pred.violence:
                    logger.warning(
                        f"RTSP VIOLENCE ALERT! Prob: {last_pred.confidence:.4f} at ts={timestamp:.2f}s"
                    )

                if not args.no_display:
                    display_frame = frame.copy()
                    h, w, _ = display_frame.shape

                    if last_pred is None:
                        status_str = "BUFFERING CLIPS..."
                        color = (255, 255, 255)
                    elif last_pred.violence:
                        status_str = f"VIOLENCE ALERT ({last_pred.confidence:.2f})"
                        color = (0, 0, 255)
                    else:
                        status_str = f"Normal ({last_pred.confidence:.2f})"
                        color = (0, 255, 0)

                    cv2.rectangle(display_frame, (0, 0), (w, 50), (0, 0, 0), -1)
                    cv2.putText(
                        display_frame,
                        f"RTSP Stream: {status_str}",
                        (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        color,
                        2,
                    )

                    cv2.imshow("SafeSchool AI - RTSP Violence Detection", display_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q")):
                        logger.info("RTSP demo exited by user.")
                        break

    except Exception as err:
        logger.error(f"RTSP stream error: {err}")
    finally:
        if not args.no_display:
            cv2.destroyAllWindows()
        logger.info("RTSP demo finished.")


if __name__ == "__main__":
    main()
