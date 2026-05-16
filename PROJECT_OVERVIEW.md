# 🏛️ Tổng Quan Kiến Trúc Dự Án: AI Child Guardian (Children Observer)

Tài liệu này cung cấp cái nhìn tổng quan về kiến trúc phần mềm, các module chính, luồng dữ liệu và công nghệ được sử dụng trong dự án AI Child Guardian.

## 📂 1. Tổng Quan Cấu Trúc Thư Mục
Dự án được thiết kế theo kiến trúc **Modular Monolith** kết hợp **Edge-Cloud Computing** (Tính toán tại biên và Đám mây), tập trung mạnh vào quá trình xử lý AI realtime và bảo mật.

- `configs/`: Chứa các cấu hình toàn cục (Logging, Settings) cho toàn hệ thống.
- `module_ai_core/`: Trái tim của dự án, chứa toàn bộ code huấn luyện, định nghĩa mô hình (PyTorch, Ultralytics) và xử lý dữ liệu AI.
- `module_backend_infra/`: Hạ tầng server tĩnh, phục vụ Federated Learning, Active Learning và xác thực.
- `module_edge_firmware/`: Hệ thống chạy trên thiết bị biên (Edge Device - ví dụ: Camera AI, Jetson Nano). Bao gồm toàn bộ luồng thu nhận hình ảnh, chạy inference và cảnh báo.
- `module_mobile_app/`: Chứa mã nguồn cho ứng dụng di động dành cho phụ huynh/người giám sát.
- `module_security/`: Đảm bảo tính riêng tư (Masking), mã hóa luồng stream và tuân thủ các quy định (Compliance).
- `scripts/`: Chứa các script tiện ích chuẩn bị môi trường, convert model (sang ONNX/TensorRT).
- `tests/`: Bộ Unit Test kiểm thử các module (ai_core, edge, security).

## 🧩 2. Danh Sách Các Module Chính

### 🧠 Module AI Core (`module_ai_core`)
- **Chức năng:** Nghiên cứu, thiết kế, huấn luyện các model nhận diện và hành vi trẻ em (Ngã, Bạo lực, Vào vùng cấm). 
- **Tương tác:** Đóng gói model (ONNX/TensorRT) và cung cấp cho thư mục `inference` của Edge Device. Backend kéo dữ liệu về để retrain (Active Learning).
- **File quan trọng:** `model_registry.py` (Quản lý và đăng ký các version của model).

### 📹 Module Edge Firmware (`module_edge_firmware`)
- **Chức năng:** Là não bộ xử lý thời gian thực tại biên. Chụp ảnh từ camera, phân tích qua AI, đánh giá rủi ro và ra quyết định gửi cảnh báo.
- **Tương tác:** Gọi sang `module_security` để che mờ khuôn mặt nếu cần, sử dụng models từ `module_ai_core` để nhận diện, gửi cảnh báo lên `module_backend_infra`.
- **File quan trọng:** `pipeline.py` (Chứa luồng thực thi tổng thể nối từ lúc Capture -> Inference -> Analysis -> Alert).

### ☁️ Module Backend Infra (`module_backend_infra`)
- **Chức năng:** Đóng vai trò làm Server trung tâm hỗ trợ thiết bị edge. Quản lý phân quyền, và quá trình huấn luyện phân tán (Federated Learning).
- **Tương tác:** Nhận model updates từ Edge qua thư mục `federated_server.py`, đồng bộ cấu hình bảo mật.
- **File quan trọng:** `federated_server.py` (Xử lý hợp nhất model từ nhiều thiết bị Edge) / `active_learning.py`.

### 🛡️ Module Security (`module_security`)
- **Chức năng:** Cung cấp tiêu chuẩn cực kỳ cao về bảo vệ quyền riêng tư hình ảnh trẻ nhỏ.
- **Tương tác:** Được plugin vào luồng Edge Firmware để lọc hình ảnh trước khi lưu hoặc gửi đi.
- **File quan trọng:** `privacy_masking.py` (Thuật toán làm mờ/ẩn khuôn mặt trẻ em hoặc các vùng nhạy cảm).

## 🌊 3. Luồng Dữ Liệu (Data Flow)
Luồng dữ liệu thời gian thực lúc hệ thống vận hành tại thiết bị biên (Edge Pipeline):

1. **Ingestion (Thu nhận):** `rtsp_capture.py` kéo frame hình ảnh từ Camera/RTSP stream $\rightarrow$ `preprocessor.py`.
2. **Buffer (Đệm):** Frame được đẩy vào `circular_buffer.py` để lưu trữ tạm thời chống mất mát dữ liệu do bottle-neck, cũng như phục vụ chức năng lưu lại khoảnh khắc (snapshot) $\pm$ n giây.
3. **Inference (Suy luận):** Các frame đi qua `multi_task_runner.py` (engine), engine này gọi các mô hình AI (`object_detector`, `pose_estimator`).
4. **Analysis (Phân tích):** Outputs bbox, keypoints được đẩy vào các detectors (`fall_detector.py`, `roi_checker.py`). `risk_assessor.py` đánh giá tổng hợp rủi ro.
5. **Security (Bảo mật):** Nếu phát hiện rủi ro, frame trước khi được chụp lại sẽ chạy qua `privacy_masking.py` để xác định có cần ẩn mặt hay không.
6. **Alert (Cảnh báo):** `alert_manager.py` khởi tạo thông báo, gửi về Mobile App đi kèm snapshot (đã an toàn).

## 🛠️ 4. Công Nghệ Sử Dụng (Tech Stack)
Dựa theo thông tin từ `pyproject.toml`, dự án sử dụng các framework AI & Computer Vision hàng đầu:
- **Ngôn ngữ:** Python $\ge$ 3.12 (có hỗ trợ strict typing với `pydantic-settings`).
- **Computer Vision & AI/ML:**
  - `opencv-python-headless`: Xử lý mảng ma trận ảnh tĩnh & video.
  - `ultralytics` ($\ge$ 8.3) & `torch`: Backbone mô hình YOLO cho Object/Behavior Detection.
  - `mediapipe`: Tối ưu hóa việc trích xuất bộ khung xương người (Pose Estimation) tại Edge, hỗ trợ fall-detection cực tốt.
  - `albumentations`: Data augmentation chuẩn mực để train AI model.
- **Edge Deployment Optimization:** `onnxruntime` (và `tensorrt` optional) để tối ưu/tăng tốc mô hình khi deploy xuống thiết bị yếu.
- **Bảo mật & Utility:** `cryptography` (mã hóa), `loguru` (logging).
- **Kiểm thử & QA:** `pytest`, `pytest-asyncio`, `ruff` (linter).

## 🚀 5. Hướng Dẫn Bắt Đầu (3 Bước Tiếp Cận An Toàn)

1. **Thiết Lập Môi Trường (Setup):**
   Mở terminal và khởi tạo môi trường Python chứa tất cả AI dependencies và công cụ Dev:
   ```bash
   pip install -e .[dev,gpu]
   ```
2. **Nắm Bắt Luồng Khởi Chạy Từ Edge:**
   Hãy đọc file `module_edge_firmware/pipeline.py` và `configs/settings.py`. Đây là nơi sếp sẽ thấy "dòng chảy" tự nhiên nhất của một frame ảnh từ camera cho đến lúc gọi AI engine.
3. **Chạy Unit Test Để Hiểu Component:**
   Chạy lệnh `pytest tests/` để xem logic của các module được kiểm tra như thế nào. Nếu sếp cần sửa logic AI (`fall_detection` hay `behavior_classifier`), hãy chỉnh sửa tại `module_ai_core/models`, viết thêm test case tại `tests/test_ai_core/`, và luôn chạy linter bằng `ruff check .` để giữ chuẩn file.
