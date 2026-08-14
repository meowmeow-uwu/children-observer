# SafeKid Monitor - MVP Demo Testing Checklist

Tài liệu này hướng dẫn cách kiểm thử toàn bộ luồng chức năng (End-to-End) của ứng dụng SafeKid Monitor để trình diễn (demo) MVP.

> **Yêu cầu môi trường:** Backend FastAPI (`localhost:8007`) và MQTT Broker (`localhost:1883`) và Edge Firmware (`module_edge_firmware/demo_stream/`) phải đang chạy để hoàn thành đầy đủ các mục E2E. Các mục UI/UX có thể kiểm thử độc lập không cần backend.

---

## A. Xác thực & Phân quyền (Authentication)
> Tương ứng: **Frontend Task 1** — Tích hợp Authentication & Authorization

- [x] **Đăng nhập bằng tài khoản thật (Backend đang chạy):**
  - Nhập đúng `email` và `password` vào form đăng nhập → Bấm **Đăng nhập hệ thống**.
  - Gọi `POST /api/auth/login` → nhận `access_token` JWT thật.
  - Sau đó tự động gọi `GET /api/auth/me` để lấy thông tin profile.
  - `access_token` được lưu vào `localStorage["safekid_token"]`.
  - Kiểm tra tab **Network**: mọi request HTTP tiếp theo đều có header `Authorization: Bearer <JWT_TOKEN>`.
- [x] **Đăng nhập demo nhanh (Backend tắt / chạy offline):**
  - Bấm link **"Mở bảng Đăng nhập Demo"** → chọn **Phụ huynh (Admin)**.
  - Hệ thống tạo fake JWT để giữ trải nghiệm demo, không cần server.
- [x] **Liên kết Telegram Chat ID (Profile):**
  - Sau khi đăng nhập, vào phần Profile.
  - Nhập `telegram_chat_id` → Bấm lưu → Gọi `PATCH /api/auth/me`.
  - Toast xác nhận cập nhật thành công.
- [x] **Đăng xuất:**
  - Nhấp Avatar góc trên bên phải → Chọn *Đăng xuất* → Xóa token khỏi `localStorage` → Quay về màn `/login`.

---

## B. Layout & Điều hướng (Navigation)
- [x] **Giao diện Desktop (Sidebar):**
  - Mở ứng dụng, đăng nhập thành công.
  - Sidebar bên trái hiển thị rõ ràng logo SafeKid và 5 mục điều hướng: *Tổng quan, Camera, Cảnh báo, Thiết bị, Cài đặt*.
  - Nhấp qua lại giữa các mục để kiểm tra tính năng chuyển trang tức thời.
- [x] **Giao diện Di động (Mobile Bottom Nav):**
  - Giảm chiều rộng màn hình xuống `< 768px`.
  - Sidebar biến mất, thanh chuyển tab phía dưới (Bottom Nav) màu trắng xuất hiện với 5 biểu tượng sắc nét.
  - Xác nhận không có phần tử nào bị che khuất bởi Bottom Nav ở chân trang.

---

## C. Màn hình Tổng quan (Dashboard)
> Dữ liệu hiển thị là dữ liệu thật từ backend, không phải mock cứng.

- [x] **Bento Cards Stats:**
  - Tổng số Camera (từ `GET /api/cameras/`), thiết bị Hub (từ `GET /api/devices/`), số cảnh báo chưa xử lý (từ `GET /api/alerts/`) hiển thị chính xác.
  - Hộp trạng thái hiển thị *"Hệ thống đang hoạt động bình thường"* (màu xanh lá) hoặc *"Hệ thống ghi nhận sự cố"* (màu đỏ) dựa trên mức độ nguy hiểm của cảnh báo hiện có.
- [x] **Danh sách Cảnh báo gần đây:**
  - Hiển thị danh sách các sự cố chưa xử lý mới nhất (lấy từ backend).
  - Bấm nút nhanh *Đánh dấu đã xử lý* hoặc *Báo nhầm* trên thẻ cảnh báo → Gọi `PATCH /api/alerts/{id}` → Thẻ biến mất tức thời khỏi danh sách và số lượng đếm chưa đọc trên Topbar giảm đi tương ứng.

---

## D. Xem Camera & Kết nối WebRTC
> Tương ứng: **Frontend Task 3** — Kết nối Video Stream WebRTC P2P

- [x] **Danh sách Camera từ Backend:**
  - Vào mục *Camera*. Danh sách camera được tải từ `GET /api/cameras/` kèm trạng thái `status`.
  - Xem các nhãn trạng thái tiếng Việt: *Đang phát trực tiếp (connected)*, *Đang kết nối (connecting)*, *Lỗi kết nối (failed)*, hoặc *Chưa kết nối (idle)*.
- [x] **Kiểm thử kết nối WebRTC (Backend & Edge đang chạy):**
  - Vào chi tiết camera *Phòng khách* → Nhấp nút **Bắt đầu xem trực tiếp**.
  - WebSocket kết nối tới `ws://localhost:8007/ws/signaling/web_parent_01?token=<JWT_TOKEN>`.
  - Trình duyệt tạo SDP Offer → Gửi lên WebSocket → Backend chuyển tiếp qua MQTT `devices/{camera_id}/webrtc/offer` → Edge (`aiortc`) phản hồi SDP Answer qua MQTT `devices/{device_id}/webrtc/answer` → Backend relay Answer về WebSocket → Frontend thiết lập kết nối P2P.
  - Video track được nạp vào thẻ `<video>` và hiển thị luồng stream mượt mà (độ trễ < 200ms).
- [x] **Kiểm thử dọn dẹp tài nguyên (Cleanup):**
  - Khi đang xem camera, nhấp nút quay lại hoặc đổi sang camera khác.
  - Kiểm tra tab Network/Console: WebSocket đóng ngay lập tức, RTCPeerConnection ngắt kết nối (`closed`), các luồng camera phần cứng dừng chạy.
- [x] **Kiểm thử khi Backend chưa chạy:**
  - Vào chi tiết camera bất kỳ → Bấm *Bắt đầu xem trực tiếp*.
  - Sau 3 lần tự động kết nối lại (1s → 2s → 4s), giao diện hiển thị `<ErrorState />` màu đỏ ghi nhận lỗi tiếng Việt *"Không thể kết nối tới máy chủ camera"* kèm nút *Thử lại*.
- [x] **Kiểm thử truyền sai Camera ID:**
  - Đi tới link `/cameras/camera_fake_id`.
  - Bấm kết nối → Nhận gói tin lỗi từ signaling → Hết lượt retry → Chuyển trạng thái sang `failed` và hiển thị nút *Thử lại*.

---

## E. Công cụ vẽ vùng nguy hiểm ROI (SVG Drawer) & Đồng bộ Backend
> Tương ứng: **Frontend Task 2** — Quản lý Camera & Cấu hình ROI
> Tương ứng: **Edge Task 1** — Đồng bộ ROI từ MQTT xuống Edge

- [x] **Khởi tạo và lưu đa giác (Polygon) — E2E với Backend:**
  - Vào màn hình *Camera* → Chọn camera Phòng khách → Nhấp **Thiết lập vùng nguy hiểm (ROI)**.
  - Chọn công cụ **Vẽ đa giác**. Click ít nhất 3 điểm trên khung hình để tạo hình đa giác.
  - Nhấp vào điểm đầu tiên hoặc bấm **Hoàn tất vùng**. Nhập tên vùng *"Cầu thang"* và chọn độ nhạy, quy tắc cảnh báo.
  - Nhấp **Lưu thiết lập** → Frontend gọi `POST /api/cameras/{camera_id_string}/roi` với payload chuẩn hóa tọa độ `[0.0 → 1.0]`.
  - Backend lưu DB → Publish MQTT topic `devices/{device_id}/roi/update` → Edge nhận và cập nhật Mask Polygon trên RAM.
  - Toast báo thành công xuất hiện.
  - Xác nhận vùng *"Cầu thang"* vừa vẽ hiển thị trong danh sách ROI và phủ đè chính xác trên trang chi tiết camera.
- [x] **Vẽ hình chữ nhật (Rectangle):**
  - Chọn công cụ **Vẽ hình chữ nhật**. Kéo thả chuột chéo góc để tạo hình nhanh chóng.
- [x] **Chế độ chỉnh sửa (Edit Mode):**
  - Nhấp nút **Chỉnh sửa** → Kéo thả các neo tròn màu đỏ để thay đổi hình dạng. Nhấp đúp vào neo để xóa bớt góc.
- [x] **Tính năng co giãn (Responsive Scale):**
  - Co giãn kích thước trình duyệt hoặc xoay ngang/dọc điện thoại.
  - Xác nhận vùng vẽ ROI không bị trôi lệch, luôn bám sát theo vị trí tĩnh tương đối trên khung hình camera.
  - Tọa độ lưu dưới dạng chuẩn hóa `[0.0 → 1.0]` — Edge quy đổi sang pixel theo công thức `X_pixel = point.x × W_frame`.

---

## F. Cảnh báo Real-time từ Edge AI
> Tương ứng: **Frontend Task 4** — Xử lý Cảnh báo Real-time & Snapshot Viewer
> Tương ứng: **Edge Task 4** — Bắn Alert JSON & Binary Snapshot qua MQTT

- [x] **Nhận cảnh báo tức thì qua WebSocket (ALERT_NEW):**
  - Đảm bảo Backend, Edge Firmware (`demo_stream`) đang chạy và camera đang kết nối WebRTC.
  - Khi trẻ trong video demo bước vào vùng ROI nguy hiểm:
    - Edge chạy YOLO + `cv2.pointPolygonTest` → phát hiện vi phạm.
    - Edge publish JSON lên MQTT `devices/{device_id}/alerts` và Binary JPEG lên `devices/{device_id}/snapshots`.
    - Backend nhận MQTT → lưu DB → Broadcast WebSocket tới mọi client với message `{"type": "ALERT_NEW", "data": {...}}`.
  - Frontend nhận `ALERT_NEW` → kích hoạt:
    - 🔊 Âm thanh còi báo động phát ra.
    - 🔴 Toast đỏ xuất hiện với tên sự cố và tên vùng ROI.
    - 🔔 Số badge thông báo trên Topbar tăng lên.
- [x] **Hiển thị Ảnh Snapshot Bằng Chứng:**
  - Nhấp vào toast hoặc biểu tượng chuông → Mở chi tiết cảnh báo `/alerts/:id`.
  - Ảnh snapshot được tải an toàn từ `http://localhost:8007/snapshots/{snapshot_url}`.
  - Ảnh hiển thị có vẽ khung bao quanh vị trí trẻ gặp nguy hiểm.
- [x] **Tra cứu Lịch sử Cảnh báo:**
  - Vào trang *Cảnh báo* → Tất cả lịch sử được lấy từ `GET /api/alerts/?limit=20`.
  - Bộ lọc trạng thái hoạt động đúng: *Chưa xử lý*, *Đã xử lý*, *Báo nhầm*.
- [x] **Xử lý sự cố:**
  - Bấm *Báo nhầm* hoặc *Đánh dấu đã xử lý* → Gọi `PATCH /api/alerts/{id}` → Trạng thái cập nhật tức thời trên UI.

---

## G. Ứng dụng PWA (Progressive Web App)
- [x] **Cài đặt độc lập (Install Prompt):**
  - Mở ứng dụng trong trình duyệt (Chrome/Edge/Safari). Chrome/Edge hỗ trợ install prompt trực tiếp; Safari/iOS có thể cài qua Add to Home Screen.
  - Đối với Chrome/Edge: Banner nhỏ dưới chân trang hiển thị: *"Cài SafeKid Monitor trên thiết bị của bạn để nhận trải nghiệm nhanh hơn."*, nhấp *Cài ứng dụng* → Hộp thoại cài đặt native của hệ điều hành xuất hiện.
- [x] **Bảo mật và Caching:**
  - Tắt mạng internet (Offline mode). Refresh lại trang.
  - Trang web vẫn tải được bình thường nhờ Service Worker cache lại App shell (HTML, CSS, JS, Fonts).
  - Kiểm tra tab Cache Storage:
    - **Không** lưu trữ bất kỳ hình ảnh snapshot của bé (`/snapshots/*`), dữ liệu API (`/api/*`), hoặc luồng truyền WebRTC để đảm bảo tuyệt đối an toàn thông tin trẻ em.
- [x] **Banner ngoại tuyến (Offline Banner):**
  - Khi ngắt kết nối mạng, một banner màu đỏ nhạt xuất hiện trên đầu trang: *"Bạn đang ngoại tuyến. Một số chức năng như xem camera trực tiếp và nhận cảnh báo sẽ tạm thời không khả dụng."*
  - Khi bật lại mạng, banner biến mất và toast hiện: *"Đã kết nối mạng internet trở lại!"*.

---

## H. Cảnh báo thông minh (Notifications)
- [x] **Cấp quyền thông báo hệ thống:**
  - Vào phần *Cài đặt* → Mục *Thông báo*.
  - Nếu trình duyệt chưa được cấp quyền, hiển thị trạng thái *"Chưa cấp quyền thông báo"* kèm nút **Cho phép thông báo**.
  - Nhấp nút và đồng ý cấp quyền → Trạng thái chuyển sang màu xanh *"Đã cho phép thông báo"*.
  - Nếu chặn quyền, giao diện chuyển sang màu đỏ và hướng dẫn mở lại cài đặt trình duyệt để cấp quyền.
- [x] **Thử nghiệm cảnh báo & Âm thanh đẩy:**
  - Bật toggle **Âm thanh cảnh báo** → Bấm **Gửi cảnh báo thử**.
  - Một âm thanh bíp ngắn phát ra bằng Web Audio API.
  - Một thông báo trình duyệt hiện lên góc màn hình hệ điều hành: *"Cảnh báo vùng nguy hiểm! ⚠️ Bé Vy đang tiếp cận rào chắn Ban công."*
  - Icon chuông báo trên Topbar tăng số lượng unread badge. Nhấp vào chuông → Hộp thư đổ xuống danh sách sự cố khẩn cấp, nhấp vào tin nhắn để nhảy trực tiếp tới màn chi tiết sự cố để xử lý.
