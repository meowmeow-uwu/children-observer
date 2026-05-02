# Task AI #3: Fall Detection (P5)

## 🎯 Nhiệm vụ
Sử dụng **YOLO26-Pose** để trích xuất khung xương (skeleton), sau đó áp dụng logic phát hiện té ngã dựa trên:
1. **Tỉ lệ chiều cao/chiều rộng** bộ xương (bbox aspect ratio).
2. **Tốc độ thay đổi trọng tâm** theo trục Y (velocity).
3. **Thời gian bất động** sau khi ngã (duration still).

## 📂 File làm việc
- `module_ai_core/models/pose_estimator.py` — YOLO-Pose wrapper.
- `module_edge_firmware/analysis/fall_detector.py` — Logic phát hiện té ngã (đã có khung).
- `train.py` — Script huấn luyện/tinh chỉnh pose model.

## 🚀 Cách chạy
```bash
# Huấn luyện YOLO-Pose (nếu cần fine-tune)
python module_ai_core/fall_detection/train.py

# Hoặc sử dụng pretrained model từ Ultralytics
python module_ai_core/fall_detection/train.py --pretrained
```

## 📤 Output (Giao cho Module 2)
Sau khi hoàn thành, copy model vào:
```
weights/fall_detection/yolo-pose-best.pt
```
Cập nhật `weights/registry.json`:
```json
{
  "fall_detection": {
    "status": "ready",
    "path": "weights/fall_detection/yolo-pose-best.pt"
  }
}
```

## 💡 Ghi chú quan trọng
- Logic té ngã **không cần train riêng** — nó dựa trên **rule-based** (tỉ lệ bbox + velocity).
- Tuy nhiên, model **Pose Estimation** cần hoạt động chính xác để trích xuất skeleton.
- P5 có thể dùng pretrained `yolov8n-pose.pt` từ Ultralytics làm baseline.

## ⚙️ Biến .env liên quan
- `POSE_MODEL_PATH`: Đường dẫn model pose.
- `INFERENCE_DEVICE`: `cuda:0` hoặc `cpu`.

## 📊 Tiêu chí hoàn thành (DoD)
- [ ] Pose estimation chạy ổn định trên video test (≥ 15 FPS trên GPU).
- [ ] Logic té ngã phân biệt được: ngã thật vs. ngồi xuống/nằm chơi.
- [ ] File model đã lưu vào `weights/fall_detection/`.
- [ ] Cập nhật `registry.json`.
