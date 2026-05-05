# Task AI #3: Fall Detection (P5)

## 🎯 Nhiệm vụ
Sử dụng **YOLO11-Pose** (yolo11n-pose.pt) để trích xuất khung xương (skeleton), sau đó áp dụng logic phát hiện té ngã dựa trên:
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
- [x] Pose estimation chạy ổn định trên video test (≥ 15 FPS trên GPU) - **✅ Đạt 89.24 FPS**
- [x] Logic té ngã phân biệt được: ngã thật vs. ngồi xuống/nằm chơi - **✅ Tested**
- [x] File model đã lưu vào `weights/fall_detection/` - **✅ yolo-pose-best.pt (6.0MB)**
- [x] Cập nhật `registry.json` - **✅ Status: ready**

## 🔧 Tuning Fall Detection Thresholds

Fall detector sử dụng 3 thresholds chính:

### 1. velocity_threshold (default: 50.0 pixels/frame)
- **Cao hơn** = ít nhạy hơn (ít false positives)
- **Thấp hơn** = nhạy hơn (có thể detect ngồi xuống là ngã)

### 2. still_threshold (default: 2.0 seconds)
- Phân biệt injury fall vs playful fall
- **Tăng** = yêu cầu nằm lâu hơn mới coi là injury

### 3. height_ratio_threshold (default: 0.6)
- Tỷ lệ height/width để detect tư thế nằm
- **Thấp hơn** = yêu cầu nằm ngang hơn

### Cách điều chỉnh:
Sửa trong `module_edge_firmware/analysis/risk_assessor.py`:
```python
self.fall_detector = FallDetector(
    velocity_threshold=60.0,      # Ít nhạy hơn
    still_threshold=3.0,           # Yêu cầu nằm lâu hơn
    height_ratio_threshold=0.5     # Yêu cầu nằm ngang hơn
)
```

## 📊 Performance Benchmarks

**Hardware:** NVIDIA GPU (CUDA)
- **GPU (CUDA):** 89.24 FPS ✅
- **Latency:** 11.21ms per frame

**Tests:**
- ✅ Pose loading test: PASSED
- ✅ Fall logic test: PASSED (3/3)
- ✅ MultiTask integration: PASSED
- ✅ FPS benchmark: PASSED (89.24 >= 15)

## 🧪 Running Tests

```bash
# Set PYTHONPATH and encoding
export PYTHONPATH=/c/children-observer
export PYTHONIOENCODING=utf-8

# Run individual tests
python test_pose_loading.py
python test_fall_logic.py
python test_multitask_integration.py

# Run benchmark
python module_ai_core/fall_detection/benchmark.py
```
