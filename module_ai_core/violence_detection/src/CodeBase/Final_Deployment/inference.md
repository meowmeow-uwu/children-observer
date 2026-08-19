# inference

## 1. Thông số kỹ thuật của Model (Model Specifications)

  • Kiến trúc gốc: X3D-M (Video Action Recognition).
  • Đầu vào (Input):
      • Tên Input Node: "input"
      • Kích thước Tensor (Shape): (1, 3, 16, 224, 224) theo thứ tự [B,C,T,H,W]
          • B = 1: Batch size (1 clip).
          • C = 3: Số kênh màu (RGB).
          • T = 16: Số lượng khung hình liên tiếp trong 1 clip.
          • H = 224,W = 224: Chiều cao và chiều rộng ảnh.
      • Kiểu dữ liệu (Dtype): float32 (hoặc np.float32).
  • Đầu ra (Output):
      • Tên Output Node: "probabilities"
      • Kích thước Output: (1, 2) (Đã bao gồm hàm Softmax xuất trực tiếp xác suất [0.0 → 1.0])
          • Index 0: Xác suất NonViolence (Bình thường / An toàn).
          • Index 1: Xác suất Violence (Bạo lực).

## Quy trình tiền xử lý

1. Kích thước ảnh: Resize khung hình về (224 × 224).
  2. Không gian màu & Scale: Chuyển từ BGR sang RGB → Chia 255.0 để đưa về dải [0.0,1.0].
  3. Chuẩn hóa ImageNet Normalization:

    mean = [0.485,0.456,0.406],  std = [0.229,0.224,0.225]

                  frame\_rgb - mean
    frame\_norm = ─────────────────
                         std

  4. Định dạng & Kích thước Tensor đầu vào:
      • Thứ tự chiều: (B,C,T,H,W) → (1, 3, 16, 224, 224) dạng float32.
      • Model nhận một đoạn clip gồm 16 khung hình liên tiếp (hoặc trích xuất qua sliding window / stride = 4
      frames).
  5. Cài đặt trong code:
      • Hàm rpi_detector.py:73-83 trong rpi_detector.py đã chuẩn hóa toàn bộ các bước trên bằng pure NumPy & OpenCV,
      hoàn toàn không cần PyTorch / Torchvision.
