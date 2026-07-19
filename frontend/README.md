# SafeKid Monitor Frontend

Giao diện giám sát thông minh SafeKid Monitor là ứng dụng PWA (Progressive Web App) chạy trên nền tảng web, di động và máy tính độc lập. Hệ thống hỗ trợ đắc lực cho phụ huynh trong việc giám sát an toàn trẻ nhỏ bằng cách kết nối camera biên (Edge Camera), thiết lập các vùng nguy hiểm ROI trực quan và đẩy cảnh báo tức thời.

---

## 1. Tính năng chính
- **Dashboard Tổng quan:** Hiển thị dưới dạng thẻ Bento Grid, trực quan hóa trạng thái camera online/offline, số sự cố ghi nhận trong ngày và danh sách cảnh báo gần đây.
- **Xem Camera trực tuyến (WebRTC):** Thiết lập luồng truyền phát video trực tiếp thời gian thực đầu-cuối độ trễ cực thấp giữa trình duyệt và camera Edge qua giao tiếp Signaling WebSocket.
- **Công cụ vẽ vùng nguy hiểm ROI bằng SVG:** Hỗ trợ tự vẽ ranh giới ảo đa giác (Polygon) hoặc hình chữ nhật (Rectangle) trực quan ngay trên luồng camera. Tọa độ được chuẩn hóa tỉ lệ `[0.0, 1.0]` để tự động co giãn theo responsive mà không bị lệch góc.
- **Trung tâm quản lý Cảnh báo (Alerts List/Detail):** Lọc tìm sự cố theo mức độ nguy hiểm, cập nhật nhanh trạng thái xử lý sự cố hoặc khai báo "Báo nhầm" trực tiếp.
- **SecureImage Loader:** Cơ chế tải ảnh chụp nhanh an toàn bằng Blob URL có kèm token Authorization và cơ chế tự động dọn dẹp bộ nhớ đệm chống rò rỉ.
- **PWA (Progressive Web App):** Cài đặt SafeKid như ứng dụng độc lập trên điện thoại/máy tính, tự động tải app shell khi ngoại tuyến (Offline mode) nhờ Service Worker.
- **Hộp thư thông báo (Notification Center):** Icon chuông thông báo trên Topbar hiển thị badge số lượng tin nhắn chưa đọc và danh sách tin nhắn đẩy thông minh.
- **Còi cảnh báo âm thanh:** Tích hợp bộ phát âm bíp khẩn cấp bằng Web Audio API để cảnh báo tức thời khi có sự cố.

---

## 2. Công nghệ sử dụng
- **Core:** React 18+ (TypeScript), Vite
- **Styling:** Tailwind CSS (Vanilla CSS variables)
- **Routing:** React Router DOM (HashRouter để phục vụ deploy demo tĩnh)
- **State Management:** Zustand
- **PWA Tooling:** vite-plugin-pwa (Workbox)
- **Real-Time Communication:** WebRTC API (RTCPeerConnection), WebSockets
- **Audio synthesis:** Web Audio API

---

## 3. Cấu trúc thư mục
```
frontend/
├── src/
│   ├── components/      # Các UI components tái sử dụng (Toast, StatusBadge, v.v.)
│   │   └── ROI/         # Công cụ vẽ ROI (ROISVGOverlay, ROIToolbar, ROISettingsPanel)
│   ├── context/         # AuthContext lưu thông tin đăng nhập demo
│   ├── hooks/           # Custom React hooks (useCameraStream, useBrowserNotification, useOnlineStatus)
│   ├── layouts/         # Layout bọc ngoài (Sidebar, Topbar, MobileBottomNav, OfflineBanner)
│   ├── routes/          # Cấu hình định tuyến Router
│   ├── services/        # Dịch vụ truyền WebRTC & Signaling socket
│   ├── store/           # Kho lưu trữ Zustand (cameraStore, alertStore, roiStore, v.v.)
│   ├── types/           # Khai báo kiểu dữ liệu TypeScript (index.ts)
│   ├── utils/           # Thuật toán phụ trợ (roiGeometry)
│   └── views/           # Các trang hiển thị chính (Dashboard, CameraDetail, ROIListView, v.v.)
├── public/
│   └── icons/           # Bộ biểu tượng ứng dụng PWA (192x192, 512x512, maskable)
├── docs/                # Tài liệu kiểm thử và kịch bản demo
└── vite.config.ts       # Cấu hình biên dịch Vite và Service Worker caching
```

---

## 4. Cài đặt và Chạy thử nghiệm

### Khởi tạo dự án:
```bash
npm install
```

### Chạy chế độ phát triển (Development):
```bash
npm run dev
```

### Đóng gói ứng dụng (Build Production):
```bash
npm run build
```

### Chạy thử nghiệm chế độ Production PWA cục bộ:
```bash
npm run preview
```

---

## 5. Biến môi trường (`.env`)
Tạo tệp `.env` tại thư mục gốc của frontend dựa theo mẫu [.env.example](file:///d:/Projects/children-observer/frontend/.env.example):
```env
VITE_SIGNALING_PROTOCOL=ws
VITE_SIGNALING_HOST=localhost:8007
VITE_SIGNALING_PATH=/ws/signaling
VITE_WEBRTC_DEFAULT_USER_ID=web_parent_01
```
*Giải thích:*
- `VITE_SIGNALING_PROTOCOL`: Giao thức WebSocket của máy chủ signaling (`ws` hoặc `wss`).
- `VITE_SIGNALING_HOST`: Tên miền hoặc địa chỉ IP kèm cổng của máy chủ signaling.
- `VITE_SIGNALING_PATH`: Đường dẫn cơ sở kết nối của signaling websocket.
- `VITE_WEBRTC_DEFAULT_USER_ID`: ID người dùng mặc định dùng cho việc bắt tay kết nối của camera.

---

## 6. Hướng dẫn các quy trình kiểm thử MVP (Smoke Tests)

### A. Kiểm thử Truyền phát Video WebRTC:
1. Đảm bảo máy chủ Signaling Server và Edge Camera Client đang chạy ở cổng cấu hình.
2. Mở SafeKid Monitor -> Chọn mục *Camera* -> Mở camera *Phòng khách*.
3. Bấm **Bắt đầu xem trực tiếp**.
4. Kiểm tra mạng: Frontend sẽ gửi gói tin SDP Offer `{ type: "offer", target, sdp }` qua socket và nhận lại SDP Answer từ camera để hiển thị video.
5. Quay lại trang trước để xác nhận cổng kết nối được đóng hoàn toàn.

### B. Kiểm thử Thiết lập vùng nguy hiểm ROI:
1. Vào mục *Camera* -> Nhấp **Thiết lập ROI** dưới camera Phòng khách.
2. Chọn **Vẽ đa giác**, bấm 3-4 điểm trên khung ảnh để tạo ranh giới vùng nguy hiểm xung quanh cầu thang hoặc ban công.
3. Bấm **Hoàn tất vùng**, đặt tên và chọn các quy tắc kích hoạt.
4. Bấm **Lưu thiết lập** -> Quay lại chi tiết camera, xác nhận vùng ROI được phủ chính xác trên video và tự động co giãn không trôi điểm khi thay đổi kích thước cửa sổ.

### C. Kiểm thử Cảnh báo & Notification Demo:
1. Vào mục *Cài đặt* -> Chọn *Thông báo*.
2. Nhấp nút **Cho phép thông báo** và xác nhận đồng ý cấp quyền trên trình duyệt.
3. Bấm **Gửi cảnh báo thử** (Demo Alert) -> Kiểm tra còi báo bíp phát ra và thông báo đẩy hệ thống xuất hiện ở góc màn hình.
4. Mở chuông thông báo trên `Topbar` để kiểm tra danh sách in-app cảnh báo, nhấp để chuyển tới màn hình chi tiết.

### D. Kiểm thử PWA & Offline:
1. Đóng gói và chạy chế độ Preview: `npm run build && npm run preview`.
2. Mở địa chỉ preview trên Chrome/Edge. Chrome/Edge hỗ trợ install prompt trực tiếp; Safari/iOS có thể cài qua Add to Home Screen.
3. Tắt kết nối Internet -> Tải lại trang: App shell vẫn hiển thị mượt mà.
4. Một banner cảnh báo ngoại tuyến màu đỏ nhạt xuất hiện báo hiệu các chức năng camera tạm thời dừng hoạt động.

---

## 7. Quy tắc Quyền riêng tư & Bảo mật dữ liệu trẻ em
- **Không cache video stream, API hoặc ảnh chụp sự cố:** Để bảo vệ tối đa dữ liệu nhạy cảm của bé, Service Worker loại trừ hoàn toàn các đường dẫn `/api/*`, `/snapshots/*`, `/ws/*` khỏi bộ nhớ đệm Cache Storage:
  *“Không cache video, snapshot cảnh báo hoặc API bảo mật vì đây là dữ liệu liên quan đến trẻ em.”*
- **Sử dụng SecureImage:** Ảnh snapshot cảnh báo được tải bất đồng bộ kèm Token Authentication dưới dạng Blob URL tạm thời. URL này được dọn dẹp (revoke) ngay lập tức khi component unmount để tránh rò rỉ bộ nhớ.
- **Tài khoản Demo:** Ứng dụng cung cấp 3 vai trò: *Phụ huynh (Admin)*, *Người giám hộ* và *Người xem* để kiểm thử phân quyền hiển thị nút bấm. *Lưu ý: Các vai trò này chỉ mô phỏng phân quyền UI; bản Production thực tế bắt buộc phải kiểm duyệt xác thực ở tầng Backend.*

---

## 8. Các hạn chế trong bản MVP & Kế hoạch Tích hợp Production
Bản MVP hiện tại sử dụng một số thành phần giả lập (mock/demo) để minh họa quy trình nghiệp vụ:
- Hệ thống gửi tin nhắn SMS, Email và Zalo thật chưa liên kết với nhà mạng.
- Chưa tích hợp Web Push Production (yêu cầu khóa cặp VAPID bảo mật của server đám mây).
- Tài khoản đăng nhập chưa tích hợp OAuth2/JWT thực tế.
- Các chỉ số thiết bị Edge Hub đang đọc từ Zustand Store tĩnh.

### Kế hoạch nâng cấp Production:
- Tích hợp API SMS Brandname, Zalo Official Account và Email Gateway.
- Chuyển đổi toàn bộ mock data sang RESTful API.
- Cấu hình server TURN/STUN riêng (như Coturn) có cơ chế sinh tài khoản tạm thời ngắn hạn cấp phát từ backend.
- Phân quyền đầu cuối bắt buộc thực thi ở tầng API Gateway backend.

---

## 9. Kịch bản Demo nhanh (Walkthrough Flow)
Thực hiện trình diễn toàn bộ hệ thống SafeKid Monitor theo luồng nghiệp vụ liên tục sau:
**Dashboard** (Tổng quan) → **Camera** (Xem trực tiếp WebRTC) → **Vẽ ROI** (SVG canvas) → **Camera có ROI overlay** (Xem live có vùng đỏ) → **Alerts** (Xem và xử lý cảnh báo) → **Notification** (Browser push & Sound test) → **Privacy** (Tự hủy ảnh & Clear log) → **Mobile/PWA** (Cài đặt app standalone & Offline mode).

*(Xem hướng dẫn lời thoại và thao tác chi tiết tại tệp [docs/demo-script.md](file:///d:/Projects/children-observer/docs/demo-script.md))*

