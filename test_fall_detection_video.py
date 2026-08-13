"""
Test Fall Detection with Real Videos from data/test_videos/

Chạy lệnh:
  PYTHONPATH=. PYTHONIOENCODING=utf-8 uv run python test_fall_detection_video.py [video_file]

Ví dụ:
  PYTHONPATH=. PYTHONIOENCODING=utf-8 uv run python test_fall_detection_video.py data/test_videos/fall.mp4
"""

import sys
import cv2
import numpy as np
from pathlib import Path
import time
from collections import deque

# Direct imports để tránh circular import
sys.path.insert(0, str(Path(__file__).parent))


def load_yolo_pose_model():
    """Load YOLO Pose model cho fall detection."""
    try:
        from ultralytics import YOLO

        weights_path = Path("weights/fall_detection/yolo-pose-best.pt")

        if not weights_path.exists():
            print(f"❌ Model không tồn tại: {weights_path}")
            return None

        print(f"📦 Loading YOLO Pose từ {weights_path}...")
        model = YOLO(str(weights_path))
        print(f"✅ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Lỗi khi load model: {e}")
        return None


def extract_keypoints(results):
    """Extract keypoints từ YOLO Pose results."""
    if not results or len(results) == 0:
        return None

    result = results[0]
    if result.keypoints is None:
        return None

    keypoints = result.keypoints.xy.cpu().numpy()  # Shape: (num_persons, 17, 2)
    conf = (
        result.keypoints.conf.cpu().numpy()
        if result.keypoints.conf is not None
        else None
    )

    return keypoints, conf


def is_lying_pose(keypoints):
    """
    Detect if person is lying down (horizontal pose).
    Compare bbox width vs height.
    """
    if keypoints is None or len(keypoints) == 0:
        return False

    kps = keypoints[0]  # First person

    # Get bounding box from keypoints
    valid_kps = kps[kps[:, 0] > 0]  # Filter invalid keypoints
    if len(valid_kps) < 5:
        return False

    width = valid_kps[:, 0].max() - valid_kps[:, 0].min()
    height = valid_kps[:, 1].max() - valid_kps[:, 1].min()

    # If width > 1.2 * height, likely lying down (lowered from 1.5 for better detection)
    ratio = width / (height + 1e-6)
    return ratio > 1.2


def calculate_motion(keypoints, prev_keypoints):
    """Calculate motion between frames."""
    if keypoints is None or prev_keypoints is None:
        return 0.0

    if len(keypoints) == 0 or len(prev_keypoints) == 0:
        return 0.0

    current_kps = keypoints[0]
    prev_kps = prev_keypoints[0]

    valid_mask = (current_kps[:, 0] > 0) & (prev_kps[:, 0] > 0)
    if not valid_mask.any():
        return 0.0

    # Calculate L2 distance
    diff = current_kps[valid_mask] - prev_kps[valid_mask]
    distances = np.linalg.norm(diff, axis=1)
    motion = np.mean(distances)

    return motion


def process_video(video_path: str, output_path: str = None):
    """
    Process video and detect falls.

    Args:
        video_path: Path to input video
        output_path: Path to save annotated video (optional)
    """
    video_path = Path(video_path)

    if not video_path.exists():
        print(f"❌ Video không tồn tại: {video_path}")
        return

    print(f"\n{'='*60}")
    print(f"🎬 Processing: {video_path.name}")
    print(f"{'='*60}")

    # Load model
    model = load_yolo_pose_model()
    if model is None:
        return

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"📊 FPS: {fps:.1f} | Frames: {frame_count} | Resolution: {width}x{height}")

    # Setup video writer if output requested
    writer = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        print(f"💾 Output: {output_path}")

    # Tracking variables
    fall_detected_frames = []
    lying_frames = deque(maxlen=int(fps * 1))  # Last 1 second (reduced from 2s)
    motion_history = deque(maxlen=5)
    prev_keypoints = None

    frame_idx = 0
    inference_times = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Run YOLO Pose
            t0 = time.perf_counter()
            results = model(frame, verbose=False)
            inference_time = (time.perf_counter() - t0) * 1000
            inference_times.append(inference_time)

            # Extract keypoints
            kps_data = extract_keypoints(results)
            keypoints = kps_data[0] if kps_data else None

            # Detect pose
            is_lying = is_lying_pose(keypoints)
            lying_frames.append(is_lying)

            # Calculate motion
            motion = calculate_motion(keypoints, prev_keypoints)
            motion_history.append(motion)

            # Fall detection logic
            fall_detected = False
            fall_reason = ""

            if is_lying and len(lying_frames) == lying_frames.maxlen:
                # Person lying for ~1 second
                still_count = sum(lying_frames)
                if still_count >= lying_frames.maxlen * 0.6:  # 60% of frames lying (lowered from 80%)
                    fall_detected = True
                    fall_reason = "INJURY FALL (lying + stillness)"
                    fall_detected_frames.append(frame_idx)

            # Quick fall detection (sudden motion + lying)
            if is_lying and len(motion_history) > 1:
                avg_motion = np.mean(list(motion_history))
                if avg_motion > 30:  # Sudden movement (lowered from 50)
                    fall_detected = True
                    fall_reason = "IMPACT DETECTED"

            # Annotate frame
            annotated_frame = results[0].plot()

            # Draw fall status
            if fall_detected:
                cv2.putText(
                    annotated_frame,
                    f"⚠️ {fall_reason}",
                    (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 0, 255),
                    2,
                )
            elif is_lying:
                cv2.putText(
                    annotated_frame,
                    "⬇️ LYING DOWN",
                    (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 165, 255),
                    2,
                )
            else:
                cv2.putText(
                    annotated_frame,
                    "✅ STANDING",
                    (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    2,
                )

            # Draw inference time
            cv2.putText(
                annotated_frame,
                f"Inference: {inference_time:.1f}ms",
                (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (200, 200, 200),
                1,
            )

            # Draw frame number
            cv2.putText(
                annotated_frame,
                f"Frame: {frame_idx}/{frame_count}",
                (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (200, 200, 200),
                1,
            )

            # Save frame
            if writer:
                writer.write(annotated_frame)

            prev_keypoints = keypoints
            frame_idx += 1

            # Progress
            if frame_idx % (fps * 5) == 0:  # Every 5 seconds
                progress = (frame_idx / frame_count) * 100
                print(f"  ⏳ {progress:.1f}% | Frame {frame_idx}/{frame_count}")

    finally:
        cap.release()
        if writer:
            writer.release()

    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 RESULTS")
    print(f"{'='*60}")
    print(f"Total frames: {frame_idx}")
    print(f"Fall detected: {len(fall_detected_frames)} times")
    if fall_detected_frames:
        print(
            f"  Frames: {fall_detected_frames[:10]}{'...' if len(fall_detected_frames) > 10 else ''}"
        )

    avg_inference = np.mean(inference_times)
    print(f"Avg inference: {avg_inference:.2f}ms")
    print(f"FPS: {frame_idx / sum(inference_times) * 1000:.1f}")

    if output_path:
        print(f"✅ Output saved to: {output_path}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        output_file = Path(video_file).stem + "_annotated.mp4"
        process_video(video_file, output_file)
    else:
        # Process all test videos
        test_videos_dir = Path("data/test_videos")
        if not test_videos_dir.exists():
            print("❌ data/test_videos không tồn tại")
            sys.exit(1)

        for video_file in sorted(test_videos_dir.glob("*.mp4")):
            process_video(str(video_file))
    