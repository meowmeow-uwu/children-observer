# 🔍 Phân tích chuyên sâu: Sub-Module `roi_detection` (Task 1)

Sub-module `roi_detection` là hạt nhân đầu tiên và quan trọng nhất trong khối AI Core của dự án Children Observer. Mục tiêu cốt lõi của nó là **nhận diện được Trẻ em và các Khu vực nguy hiểm (ROI)** xung quanh trẻ như ổ điện, dao, kéo, phích nước... từ đó làm cơ sở dữ liệu để cảnh báo an toàn.

Tài liệu này sẽ mổ xẻ chi tiết từng ngóc ngách về luồng dữ liệu, thuật toán, cơ chế huấn luyện và quá trình hậu xử lý (post-processing) của sub-module này.

---

## 1. Phân tích Luồng Dữ liệu (Data Pipeline)

Thay vì trực tiếp xử lý file ảnh thủ công, `roi_detection` sử dụng cơ chế Data Loader tập trung thông qua `datasets/childsun_loader.py` kết nối với chuẩn của Ultralytics.

*   **Dataset:** Sử dụng tập dữ liệu **KidSentry Master Dataset** (hơn 15,000 ảnh).
*   **Class Mapping:** Phân tích ra 5 đối tượng tĩnh và động:
    1.  `adult` (Người lớn) - Đối tượng tham chiếu.
    2.  `child` (Trẻ em) - Đối tượng cần bảo vệ chính.
    3.  `knife` (Dao) - Vật thể nguy hiểm sắc nhọn.
    4.  `outlet` (Ổ điện) - Vật thể nguy hiểm cố định.
    5.  `scissors` (Kéo) - Vật thể nguy hiểm sắc nhọn.
*   **Tiền xử lý & Augmentation:** Trước khi đưa vào mạng nơ-ron, ảnh được tự động scale về kích thước ma trận vuông (`640x640` hoặc `1024x1024` nếu cấu hình) và đi qua các bộ lọc tăng cường như Mosaic, MixUp để tăng tính tổng quát hóa, chống overfitting.

---

## 2. Phân tích Thuật toán và Model Wrapper (`ObjectDetector`)

Trái tim của `roi_detection` nằm ở class `ObjectDetector` (`module_ai_core/models/object_detector.py`). Class này bọc toàn bộ sự phức tạp của model AI nguyên thủy lại thành các API cực kỳ đơn giản (Load, Train, Predict, Export).

### 2.1. Cấu trúc mạng (YOLO Architecture)
*   Sử dụng kiến trúc thuộc họ **YOLOv8/v10 (đặt tên local là YOLO26)**. Kiến trúc này thuộc dòng Single-Stage Detector (quét 1 lần ra kết quả), loại bỏ hoàn toàn cơ chế Anchor-Box chậm chạp cũ, mang lại tốc độ (Inference) cực cao.
*   Được thiết kế linh hoạt cho phép chuyển đổi nóng giữa **Nano (`yolo26n`)** (nhẹ, tốc độ 400FPS) và **Small (`yolo26s`)** (nặng hơn, cân bằng độ chính xác). Khả năng Fallback thông minh giúp hệ thống tự lên mạng tải file weights gốc nếu máy cục bộ bị thiếu.

### 2.2. Kỹ thuật Hậu xử lý (Post-Processing & ONNX Parsing)
Điểm tinh tế nhất của module này nằm ở hàm `_parse_engine_output` khi đọc đầu ra của Edge Tensor:
1.  **Xử lý Đa định dạng (Multi-format Parsing):** 
    *   Hỗ trợ ma trận kiểu cũ `[1, 84, 8400]` của YOLOv8 (đòi hỏi xử lý ma trận chuyển vị Transpose, giải mã toạ độ `[cx, cy, w, h]` và lọc `cv2.dnn.NMSBoxes`).
    *   Hỗ trợ ma trận End-to-End kiểu mới `[1, 300, 6]` của YOLOv10/NMS-embedded. Nó đọc thẳng toạ độ `[x1, y1, x2, y2, score, class_id]` mà không cần qua nhiều vòng lặp, giúp giảm tối đa độ trễ.
2.  **Đồng bộ Scale (Rescaling):** Do ảnh trước khi đưa vào AI bị bóp méo (Resize/Padding) về 640x640, hàm sẽ tự động dùng thông số `pad_x`, `pad_y` và `scale` từ `FramePreprocessor` để phóng to toạ độ Bounding Box về lại đúng pixel của ảnh thật ban đầu.

---

## 3. Phân tích Luồng Huấn luyện tự động (`train.py`)

Kịch bản `train.py` không chỉ đơn thuần là gõ lệnh gọi thư viện, nó là một chu trình CI/CD mini thu nhỏ:

1.  **Nhận diện tham số (Argparse):** Cho phép ghi đè mọi cấu hình thông qua Terminal (vd: `--batch 8 --model yolo26s.pt --epochs 50`).
2.  **Huấn luyện (Training):** Khởi chạy bộ tối ưu hóa (AdamW) ép Loss function nhỏ dần. Tích hợp sẵn cơ chế Early Stopping (nếu 20 epochs liên tiếp mAP không tăng sẽ tự động ngắt để tiết kiệm điện/GPU).
3.  **Tự động so sánh (Auto Model Registry):**
    *   Sau khi ra kết quả, script sẽ lôi điểm `mAP50` của model cũ từ `weights/registry.json` ra đối chiếu.
    *   Nếu model mới KHÔNG tốt bằng model cũ -> Huỷ kết quả, giữ nguyên model cũ.
    *   Nếu model mới TỐT HƠN -> Nó thực hiện chuỗi hành động: **Copy file `best.pt`** -> **Gọi hàm Export sang `best.onnx`** -> **Ghi đè điểm số mới vào Registry**. 
    *   Điều này giúp Firmware ở nhánh Edge (Module 2) chỉ việc "nhắm mắt" đọc file mà luôn đảm bảo đang dùng phiên bản xịn nhất.

---

## 4. Phân tích Hiệu suất và Đánh giá (Metrics Evaluation)

Sau đợt huấn luyện cuối cùng (50 Epochs, Model Small), module đã đạt các chỉ số cực kỳ thuyết phục (ghi nhận tại `train_50epoc_report.md`):

*   **Đỉnh cao với Vật thể tĩnh:** Dao (`0.979`), Ổ điện (`0.993`) đạt điểm gần tuyệt đối. Vì chúng có hình thù cố định, góc cạnh rõ ràng, AI dễ dàng học được các đặc trưng (features) của chúng.
*   **Vượt trội với Con người:** Trẻ em (`0.895`) và Người lớn (`0.848`). Con người là vật thể "động" (lúc đứng, lúc ngồi, lúc bị che khuất, lúc mặc quần áo màu khác nhau), nhưng mAP50 trên 85% chứng minh AI đã học được "bản chất hình thể" thay vì học vẹt màu sắc quần áo.
*   **Tốc độ rẽ nhánh (Speed):** Tốn chưa tới `2.5ms` cho một khung hình trên GPU laptop. Đảm bảo Firmware nhúng có thể quét luồng RTSP camera 30FPS mà CPU không bị quá tải.

---

## 5. Tổng kết
Sub-module `roi_detection` hiện tại là tác vụ **hoàn thiện nhất và trưởng thành nhất** trong toàn bộ hệ thống. Với cơ chế Train tự động, cơ chế đọc ONNX thông minh và hiệu năng cao, nó đã hoàn toàn sẵn sàng đảm đương vai trò "Mắt thần" cảnh báo sớm cho dự án Children Observer.
