# Module Mobile App - ChildrenObserver

Ứng dụng di động giám sát trẻ em thông minh, hỗ trợ Live Stream WebRTC, vẽ vùng ROI (Region of Interest) và hệ thống cảnh báo tích hợp cơ chế HITL (Human-in-the-loop).

## 🛠 Tech Stack & Dependencies
Ứng dụng được xây dựng hoàn toàn bằng **Jetpack Compose** với kiến trúc hiện đại:
- **Core:** Kotlin 2.0, Jetpack Compose Material 3.
- **Navigation:** Navigation Compose cho luồng chuyển cảnh mượt mà.
- **Firebase:** Firebase BOM & Messaging để quản lý thông báo đẩy.
- **Build System:** Gradle Version Catalog (`libs.versions.toml`) giúp quản lý thư viện tập trung.

## ✨ Tính năng & Trải nghiệm người dùng (UX)
1. **Live Stream chính:**
    - Player tỷ lệ 16:9 tối ưu cho camera an ninh.
    - Chức năng chuyển đổi camera linh hoạt qua Dropdown.
    - Các nút nổi (FAB) đàm thoại 2 chiều và ghi hình được thiết kế dễ chạm.
2. **Drawing Mode (Vẽ vùng an toàn):**
    - Hiệu ứng Canvas: Làm tối vùng video để nổi bật vùng đang vẽ.
    - Tương tác thông minh: Chạm để thêm điểm, **kéo thả điểm** để tinh chỉnh.
    - Hỗ trợ lưới (Grid) mờ giúp căn chỉnh chính xác các vật thể như ổ điện, cửa sổ.
3. **Alert Dashboard (HITL):**
    - Thẻ cảnh báo hiển thị ảnh snapshot có khung đỏ (AI detected).
    - Cơ chế phản hồi: Người dùng trực tiếp tham gia vào vòng lặp huấn luyện AI bằng cách xác nhận "Nguy hiểm" hoặc "Báo động sai".
4. **Thông báo đẩy nâng cao:**
    - Hiển thị trực tiếp hình ảnh snapshot trên thanh thông báo.
    - **Hành động nhanh (Quick Actions):** Xem trực tiếp hoặc Kích hoạt báo động ngay trên màn hình khóa.

## 📂 Chi tiết các File triển khai

### Giao diện & Luồng (UI & Flow)
- **`MainActivity.kt`**: Điểm khởi đầu của ứng dụng, quản lý NavHost và xử lý Deep Link từ thông báo.
- **`ui/theme/Theme.kt`**: Style Guide (Deep Navy, Emergency Red) và Typography.
- **`Models.kt`**: Định nghĩa các lớp dữ liệu dùng chung (`Camera`, `Alert`, `RoiPolygon`).
- **`LiveStreamScreen.kt`**: Màn hình xem trực tiếp và điều khiển camera.
- **`AlertDashboardScreen.kt`**: Dashboard quản lý danh sách cảnh báo (HITL).
- **`CameraSettingsScreen.kt`**: Cài đặt camera và lối vào chế độ vẽ.
- **`DrawingModeScreen.kt`**: Công cụ vẽ ROI chuyên sâu trên Canvas.

### Hệ thống & Cấu hình (System & Config)
- **`MyFirebaseMessagingService.kt`**: Xử lý logic nhận tin nhắn và hiển thị Notification.
- **`NotificationActionReceiver.kt`**: Tiếp nhận và xử lý lệnh từ các nút bấm trên thông báo.
- **`AndroidManifest.xml`**: Cấu hình quyền truy cập (Internet, Notification) và khai báo các Service/Activity.
- **`libs.versions.toml` & `app/build.gradle`**: Cấu hình toàn bộ thư viện cần thiết.

## 🚀 Hướng dẫn hoàn thiện Setup
1. **Firebase:** Tải `google-services.json` từ Firebase Console và đặt vào thư mục `app/`.
2. **Assets:** Thêm các icon `ic_notification`, `ic_live_stream`, `ic_speaker_alarm` (Vector drawable) vào `res/drawable`.
3. **Images:** Đặt các ảnh mẫu `placeholder_alert_x.png` vào `res/drawable` để demo danh sách cảnh báo.
4. **WebRTC:** Thay thế các placeholder trong `LiveStreamScreen.kt` bằng logic WebRTC thực tế khi kết nối với module Streaming.
