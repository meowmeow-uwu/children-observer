# Module Backend Infrastructure - Hạ tầng & Học tập

Module này quản lý hạ tầng phía máy chủ, tập trung vào việc cải thiện mô hình AI từ xa và quản lý người dùng.

## 🚀 Tính năng chính
1. **Active Learning**: Thu thập phản hồi "Báo động sai" (False Alarm) từ phụ huynh để đánh dấu dữ liệu và tái huấn luyện mô hình.
2. **Federated Learning Server**: Cơ chế cập nhật trọng số mô hình qua OTA (Over-The-Air) mà không cần truy cập video thô của người dùng.
3. **Auth Service**: Quản lý tài khoản, xác thực 2 lớp (2FA) và cấp phát JWT Token.

## 📂 Thành phần
- `active_learning.py`: Xử lý feedback loop từ Mobile App.
- `federated_server.py`: Quản lý cập nhật trọng số mô hình.
- `auth_service.py`: Xác thực và bảo mật tài khoản.

## ⚙️ Biến môi trường quan trọng (.env)
- `BACKEND_URL`: URL của server backend.
- `FEDERATED_SERVER_URL`: URL server quản lý cập nhật mô hình.
- `AUTH_JWT_SECRET`: Khóa dùng để ký các token xác thực.
