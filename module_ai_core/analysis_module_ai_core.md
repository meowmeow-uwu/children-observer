# 🧠 Phân tích chi tiết: `module_ai_core` (Trái tim Trí tuệ Nhân tạo của Children Observer)

`module_ai_core` đóng vai trò là "Bộ não" của toàn bộ dự án Children Observer. Đây là nơi chứa toàn bộ logic về huấn luyện (training), đánh giá (validation), và quản lý các mô hình Deep Learning trước khi chúng được đóng gói và đưa xuống chạy thực tế trên thiết bị biên (Edge).

Dưới đây là phân tích chi tiết về kiến trúc, luồng hoạt động và trạng thái hiện tại của module này.

---

## 1. Kiến trúc Tổng thể (Modular & Scalable)

Kiến trúc của `module_ai_core` được thiết kế theo hướng **Decoupled (Phân tách lỏng lẻo)**, giúp một nhóm (team) có thể làm việc song song mà không dẫm chân lên nhau. Nó được chia thành 2 nhóm thành phần chính: **Phần dùng chung (Shared Core)** và **Phần tác vụ độc lập (Independent Tasks)**.

### 1.1. Các Tác vụ Độc lập (Independent Tasks)
Module được chia thành 3 bài toán (tasks) hoàn toàn biệt lập, mỗi bài toán do một kỹ sư phụ trách:

*   🎯 **`roi_detection/` (Task 1 - Đã hoàn thiện xuất sắc):** 
    *   **Mục tiêu:** Nhận diện vùng quan tâm (ROI) bao gồm Trẻ em và Vật thể nguy hiểm (Dao, kéo, ổ điện...).
    *   **Công nghệ:** YOLOv8/YOLO26 (Object Detection).
    *   **Thành quả:** Đạt mAP50 lên tới **0.935** (đã test thực tế nhận diện chính xác trẻ em với độ tin cậy >91%).
*   ⚔️ **`violence_detection/` (Task 2):** 
    *   **Mục tiêu:** Nhận diện hành vi bạo lực hoặc đánh nhau.
    *   **Công nghệ:** Dự kiến sử dụng ST-GCN (Spatio-Temporal Graph Convolutional Networks) dựa trên chuỗi khung hình (Video/Action Recognition).
*   ⚠️ **`fall_detection/` (Task 3):** 
    *   **Mục tiêu:** Phát hiện sự cố vấp ngã của trẻ.
    *   **Công nghệ:** YOLO-Pose (Keypoint Detection) kết hợp với thuật toán Heuristic/GCN phân tích bộ xương (skeleton).

### 1.2. Thành phần dùng chung (Shared Core)
Để tránh lặp lại code (DRY - Don't Repeat Yourself), các class nền tảng được trừu tượng hóa và đặt ở thư mục gốc:

*   📦 **`datasets/`:** Chứa các class load dữ liệu chuẩn hóa (`childsun_loader.py`, `violence_loader.py`) và các kỹ thuật tăng cường dữ liệu (Augmentation).
*   🤖 **`models/`:** Chứa các lớp bọc (Wrapper Classes) cho các mô hình AI. Nổi bật nhất là `object_detector.py` vừa được nâng cấp để hỗ trợ đa định dạng (đọc file `.pt` để train, và đọc file `.onnx` xuất ra dạng `[1, 300, 6]` kết hợp NMS cho Edge Inference).
*   ⚙️ **`training/`:** Chứa các hàm hỗ trợ chung cho quá trình Train, Evaluate và Export (chuyển đổi sang ONNX/TensorRT).

---

## 2. Cơ chế Quản lý Thông minh: Model Registry

Một điểm sáng cực lớn trong thiết kế của `module_ai_core` là cơ chế **Model Registry** (`model_registry.py` và file `weights/registry.json`).

*   **Vấn đề:** Làm sao để Module Edge (Firmware) biết mô hình nào đã train xong để load vào RAM, mô hình nào chưa xong để bỏ qua?
*   **Giải pháp:** `registry.json` đóng vai trò như một "Bảng Trạng Thái". 
    *   Mỗi khi script `train.py` của một task chạy xong (ví dụ bài toán ROI), nó sẽ tự động cập nhật mAP50 mới nhất vào file json này và chuyển trạng thái thành `"ready"`.
    *   Hệ thống Edge Pipeline (`MultiTaskRunner`) khi khởi động chỉ cần đọc file này. Nếu thấy task nào có chữ `"ready"`, nó sẽ kích hoạt Engine (ONNX/TensorRT) tương ứng. Nếu đang `"training"` hoặc `"not_started"`, nó sẽ bỏ qua một cách an toàn mà không làm sập (crash) toàn bộ camera.

---

## 3. Luồng Vòng đời của một Mô hình AI (Life-cycle)

Quá trình làm việc chuẩn trong module này được định nghĩa khép kín:

1.  **Chuẩn bị (Data & Init):** Tải dataset về `data/`, khởi tạo `train.py` với cấu hình `--model yolov8s.pt --epochs 50 --img-size 640`.
2.  **Huấn luyện (Training):** Hệ thống sẽ tự tải Base Model từ internet, bắt đầu chu kỳ học và lưu các checkpoint vào `runs/detect/`.
3.  **Cập nhật (Registry Update):** Khi kết thúc, code sẽ tự so sánh điểm mAP mới với điểm mAP cũ trong `registry.json`. Nếu mô hình mới khôn hơn, nó sẽ copy đè lên `weights/roi_detection/best.pt`.
4.  **Chuyển đổi (Export):** Mô hình `.pt` nặng nề của PyTorch sẽ được nén và xuất sang định dạng `.onnx` tối ưu hóa toán học.
5.  **Thực thi (Edge Inference):** Thuật toán giải mã đầu ra (như hàm `_parse_engine_output` vừa được chúng ta khắc phục) sẽ đọc mảng tensor từ ONNX, lọc nhiễu NMS và trả về toạ độ bounding box cực kỳ nhẹ và nhanh (chỉ tốn khoảng ~15ms).

---

## 4. Trạng thái hiện tại và Đề xuất (Next Steps)

### Trạng thái hiện tại
*   ✅ **Luồng kết nối Core-Edge:** Hoàn hảo. Đã fix xong lỗi bất đồng bộ định dạng Array đầu ra của ONNX.
*   ✅ **ROI Detection:** Đã sẵn sàng production. Mô hình YOLO26s (Small) train 50 epochs cực kỳ mạnh mẽ.
*   ⏳ **Fall / Violence Detection:** Đang ở trạng thái `not_started`.

### Đề xuất công việc tiếp theo
1.  **Mở rộng Dataset ROI:** Mô hình thỉnh thoảng vẫn bị "Domain Gap" với các góc chụp thực tế. Cần tiếp tục bổ sung thêm ảnh ổ điện trắng vào tập dataset hiện tại và chạy lại file `train.py`.
2.  **Khởi động Fall Detection (Task 3):** Vì YOLO-Pose khá tương đồng với Object Detection, nhóm có thể bắt tay vào làm Task 3 ngay. Có thể copy luồng code của ROI sang và tinh chỉnh lại hàm giải mã output (từ việc bắt 4 toạ độ box chuyển sang bắt 17 toạ độ keypoints).
3.  **Tối ưu Hậu xử lý (Post-processing):** Di chuyển các hàm tính toán ma trận nặng nề (như việc scale toạ độ và chạy NMS) sang ngôn ngữ C++ dưới tầng Firmware nếu trong tương lai hệ thống bị thắt nút cổ chai về hiệu năng (Bottleneck).
