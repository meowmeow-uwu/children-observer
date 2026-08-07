# Violence Detection Module (X3D-M Pretrained on RWF-2000)

Hệ thống nhận diện hành vi bạo lực (Violence / Non-violence) từ video stream thời gian thực sử dụng pretrained **X3D-M fine-tuned trên tập dữ liệu RWF-2000** (`visionlab-ai/school-violence-detection-models`).

---

## 1. Tính năng chính

- **Pretrained Weights**: Tự động tải weights từ Hugging Face Hub (`final/final_x3d_realtime.pt`).
- **Realtime & Lightweight**: Kiến trúc X3D-M tối ưu hóa cho độ trễ thấp và tài nguyên nhỏ.
- **Sliding Window Processing**: Xử lý 16 khung hình liên tiếp với bước nhảy (frame stride) tùy chỉnh (mặc định: 8 frames).
- **Temporal Smoothing**: Bộ lọc làm mượt thời gian (Moving Average / Median) giảm thiểu tối đa cảnh báo giả (false alarm).
- **Đa dạng nguồn vào**: Hỗ trợ Webcam, file video (`.mp4`, `.avi`, ...), và luồng trực tiếp RTSP (`rtsp://...`).
- **CPU & CUDA Auto Fallback**: Tự động phát hiện GPU CUDA, fallback an toàn sang CPU khi không tìm thấy GPU.

---

## 2. Cài đặt

### Bước 1: Tạo môi trường ảo Python 3.11+

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 2: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

Hoặc cài từ thư mục gốc dự án:
```bash
pip install torch torchvision pytorchvideo opencv-python numpy huggingface_hub pydantic loguru pytest
```

---

## 3. Hướng dẫn chạy Demo

### A. Demo Webcam
Chạy nhận diện thời gian thực từ camera máy tính:
```bash
python examples/webcam_demo.py --cam 0 --threshold 0.4
```
*Bấm `q` hoặc `ESC` trên cửa sổ OpenCV để thoát.*

### B. Demo Video File
Chạy kiểm tra nhận diện trên file video:
```bash
python examples/video_demo.py --video path/to/sample.mp4 --threshold 0.4
```
Chạy không hiển thị màn hình (headless mode):
```bash
python examples/video_demo.py --video path/to/sample.mp4 --no-display
```

### C. Demo RTSP Stream
Chạy trên luồng camera giám sát qua RTSP:
```bash
python examples/rtsp_demo.py --source "rtsp://admin:password@192.168.1.100:554/live"
```
*Lưu ý: Mọi thông tin tài khoản đăng nhập RTSP trong log sẽ tự động được ẩn mã hóa để đảm bảo an toàn bảo mật.*

---

## 4. Tích hợp Python Interface (API)

```python
import cv2
from violence_detection import (
    ViolenceDetectionConfig,
    ViolenceDetector,
    VideoStream,
)

# 1. Khởi tạo cấu hình
config = ViolenceDetectionConfig(
    violence_threshold=0.4,
    clip_length=16,
    frame_stride=8,
    smoothing_window=5,
    alert_min_consecutive=2,
    device="auto",
)

# 2. Khởi tạo Detector (load checkpoint 1 lần duy nhất)
detector = ViolenceDetector(config)

# 3. Dự đoán trên clip 16 khung hình OpenCV (BGR)
frames = [cv2.imread(f"frame_{i}.jpg") for i in range(16)]
result = detector.predict_clip(frames)

print(f"Is Violence Alert: {result.violence}")
print(f"Confidence (Smoothed): {result.confidence:.4f}")
print(f"Raw Probability: {result.raw_probability:.4f}")
print(f"Inference Latency: {result.inference_ms:.2f} ms")

# 4. Dự đoán trực tiếp từ VideoStream
for result in detector.process_stream(source="sample.mp4"):
    if result.violence:
        print(f"[ALERT] Violence detected at {result.timestamp:.2f}s (prob: {result.confidence:.2f})")
```

---

## 5. Giải thích các tham số cấu hình chính

| Tham số | Giá trị mặc định | Giải thích |
|---|---|---|
| `clip_length` | `16` | Số khung hình liên tiếp cho 1 clip đầu vào model X3D |
| `frame_stride` | `8` | Khoảng cách khung hình trượt giữa các lần inference (bước nhảy) |
| `spatial_size` | `224` | Kích thước ảnh đầu vào `(224x224)` |
| `violence_threshold` | `0.4` | Ngưỡng xác suất để phân loại bạo lực |
| `smoothing_window` | `5` | Độ dài cửa sổ mượt thời gian (Temporal Smoothing Window) |
| `alert_min_consecutive` | `2` | Số lượng clip liên tiếp vượt ngưỡng để phát cảnh báo chính thức |
| `device` | `"auto"` | Thiết bị chạy (`"auto"`, `"cuda"`, `"cpu"`) |

---

## 6. Chạy Unit Tests

Chạy kiểm thử cho các thành phần Preprocessing, Temporal Smoothing và Inference Core:

```bash
pytest tests/
```

---

## 7. Limitations & Recommendations

- **RWF-2000 Fine-tuned**: Model được fine-tune trên tập dữ liệu RWF-2000 (chủ yếu là video giám sát chất lượng trung bình/thấp).
- **Domain Shift**: Khi triển khai ở môi trường thực tế (camera góc rộng, ánh sáng yếu, góc quay camera gia đình), có thể xuất hiện độ lệch phân phối dữ liệu (domain shift).
- **False Positives**: Các hành vi nô đùa (play fighting), tập võ, cử động nhanh có thể làm tăng xác suất dự đoán bạo lực.
- **Xác suất tương đối**: Kết quả đầu ra là xác suất bạo lực tương đối từ mô hình AI, không phải là chỉ số nguy hiểm tuyệt đối.
- **Khuyến nghị**: Module phù hợp cho tích hợp MVP/Demo hoặc hệ thống hỗ trợ giám sát. Khi đưa vào vận hành sản phẩm chính thức, khuyến nghị thu thập dữ liệu thực tế tại môi trường triển khai để thẩm định hoặc fine-tune bổ sung.
