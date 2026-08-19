"""
Inference Script cho Model YOLOv11m-Pose Phát Hiện Té Ngã trên Video.

Tính năng:
1. Tự động load weights YOLOv11m-Pose mới nhất (weights/fall_detection/best.pt).
2. Dự đoán và vẽ khung xương (17 keypoints) + Bounding Box lên video.
3. Phân tích tư thế ngã bằng góc nghiêng khung xương / aspect ratio.
4. Tự động xuất video kết quả ra thư mục output.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
from loguru import logger
from ultralytics import YOLO


def is_falling_pose(kpts: np.ndarray, bbox: list[float]) -> tuple[bool, str]:
    """
    Phân tích heuristic tư thế ngã dựa vào 17 keypoints Pose COCO.
    COCO Keypoints:
    0: Nose, 5: L_Shoulder, 6: R_Shoulder, 11: L_Hip, 12: R_Hip, 15: L_Ankle, 16: R_Ankle
    """
    if kpts is None or len(kpts) < 17:
        return False, "NO_KEYPOINTS"

    # Lấy tọa độ vai và hông
    l_shoulder, r_shoulder = kpts[5], kpts[6]
    l_hip, r_hip = kpts[11], kpts[12]

    # Tính tâm vai và tâm hông
    shoulder_center_y = (l_shoulder[1] + r_shoulder[1]) / 2.0
    hip_center_y = (l_hip[1] + r_hip[1]) / 2.0
    shoulder_center_x = (l_shoulder[0] + r_shoulder[0]) / 2.0
    hip_center_x = (l_hip[0] + r_hip[0]) / 2.0

    # 1. Aspect Ratio Bounding Box: Khi ngã, chiều rộng w > chiều cao h (hoặc w/h > 1.1)
    if len(bbox) >= 4:
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        if bh > 0 and (bw / bh) > 1.1:
            return True, f"FALL_ASPECT_RATIO (w/h={bw/bh:.2f})"

    # 2. Thân người nằm ngang: Khoảng cách dọc y giữa Vai và Hông nhỏ hơn khoảng cách ngang x
    dx = abs(shoulder_center_x - hip_center_x)
    dy = abs(shoulder_center_y - hip_center_y)

    if dy < 0.15 * (bw if 'bw' in locals() else 1.0) or (dy < dx and dx > 0.05):
        return True, "FALL_HORIZONTAL_BODY"

    return False, "NORMAL"


def predict_video(
    video_path: str,
    weights_path: str,
    output_path: str = "runs/fall_detection/predict_output.mp4",
    conf_thresh: float = 0.3,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    
    # 1. Xác định file weights
    weights = Path(weights_path)
    if not weights.exists():
        fallback_weights = project_root / "runs" / "pose" / "runs" / "fall_detection" / "exp_pose_max" / "weights" / "best.pt"
        if fallback_weights.exists():
            weights = fallback_weights
        else:
            fallback_root = project_root / "weights" / "fall_detection" / "best.pt"
            weights = fallback_root

    logger.info(f"📂 Nạp mô hình từ: {weights}")
    model = YOLO(str(weights))

    # 2. Xác định file video đầu vào
    vid_file = Path(video_path)
    if not vid_file.exists():
        fallback_vid = project_root / "falls_annotated.mp4"
        if fallback_vid.exists():
            vid_file = fallback_vid
        else:
            raise FileNotFoundError(f"Không tìm thấy file video tại: {video_path}")

    logger.info(f"🎥 Đang xử lý video: {vid_file}")

    cap = cv2.VideoCapture(str(vid_file))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Output video writer
    out_file = project_root / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    frame_idx = 0
    fall_alerts = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        results = model.predict(frame, conf=conf_thresh, verbose=False)

        for res in results:
            annotated_frame = res.plot()  # Vẽ bounding box & skeleton mặc định của YOLOv11

            if res.keypoints is not None and res.boxes is not None:
                boxes_data = res.boxes.xyxy.cpu().numpy()
                kpts_data = res.keypoints.xyn.cpu().numpy()  # Normalized keypoints [N, 17, 2]

                for i, (box, kpt) in enumerate(zip(boxes_data, kpts_data)):
                    is_fall, reason = is_falling_pose(kpt, box.tolist())
                    if is_fall:
                        fall_alerts += 1
                        # Highlight cảnh báo NGÃ màu đỏ nổi bật
                        cv2.rectangle(
                            annotated_frame,
                            (int(box[0]), int(box[1])),
                            (int(box[2]), int(box[3])),
                            (0, 0, 255),
                            3,
                        )
                        cv2.putText(
                            annotated_frame,
                            f"⚠️ CANH BAO NGA! [{reason}]",
                            (int(box[0]), max(30, int(box[1]) - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),
                            2,
                        )

        out.write(annotated_frame)

        if frame_idx % 30 == 0 or frame_idx == total_frames:
            logger.info(f"   ├─ Tiến độ: {frame_idx}/{total_frames} frames ({frame_idx/total_frames*100:.1f}%)")

    cap.release()
    out.release()

    logger.info(f"✅ Hoàn tất! Video kết quả đã được lưu tại: {out_file}")
    logger.info(f"📊 Tổng số frame phát hiện cảnh báo ngã: {fall_alerts}/{total_frames}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inference YOLOv11m-Pose Fall Detection on Video")
    parser.add_argument("--video", type=str, default="falls_annotated.mp4", help="Đường dẫn file video test")
    parser.add_argument("--weights", type=str, default="weights/fall_detection/best.pt", help="Đường dẫn file weights best.pt")
    parser.add_argument("--output", type=str, default="runs/fall_detection/predict_output.mp4", help="File video kết quả")
    parser.add_argument("--conf", type=float, default=0.35, help="Confidence threshold (mặc định: 0.35)")
    args = parser.parse_args()

    predict_video(
        video_path=args.video,
        weights_path=args.weights,
        output_path=args.output,
        conf_thresh=args.conf,
    )
