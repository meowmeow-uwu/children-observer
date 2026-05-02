# Module Security - Bảo mật & Tuân thủ

Module này đảm bảo hệ thống tuân thủ các tiêu chuẩn bảo mật IoT khắt khe nhất (QCVN 135:2024) và bảo vệ quyền riêng tư người dùng.

## 🔒 Các tính năng bảo mật
1. **End-to-End Encryption (E2EE)**: Mã hóa ảnh và video cảnh báo bằng thuật toán AES-256-GCM trước khi gửi khỏi thiết bị biên.
2. **Privacy Masking**: Tự động phát hiện và làm mờ mặt người lạ (Stranger Face Blurring) để bảo vệ quyền riêng tư.
3. **Compliance Checker**: Bộ công cụ kiểm tra tự động các tiêu chí của tiêu chuẩn QCVN 135 và PSTI.

## 📂 Thành phần
- `encryption.py`: Logic mã hóa/giải mã và xác thực HMAC.
- `privacy_masking.py`: Face detection và Gaussian blur.
- `compliance_checker.py`: Kiểm tra cấu hình hệ thống so với tiêu chuẩn pháp lý.

## 🛠 Cách chạy kiểm tra tuân thủ

Kiểm tra hệ thống có đủ điều kiện an toàn thông tin:
```bash
python main.py --mode compliance
```

## ⚙️ Biến môi trường quan trọng (.env)
- `E2EE_SECRET_KEY`: Khóa bí mật dùng để mã hóa dữ liệu (Cực kỳ quan trọng).
- `PRIVACY_BLUR_STRANGERS`: Bật/Tắt chế độ làm mờ mặt (`true`/`false`).
- `HMAC_SECRET_KEY`: Khóa dùng để xác thực tính toàn vẹn dữ liệu.
