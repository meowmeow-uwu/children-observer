# SafeKid Monitor - MVP Demo Testing Checklist

Tài liệu này hướng dẫn cách kiểm thử toàn bộ luồng chức năng (End-to-End) của ứng dụng SafeKid Monitor để trình diễn (demo) MVP.

---

## A. Layout & Điều hướng (Navigation)
- [ ] **Giao diện Desktop (Sidebar):**
  - Mở ứng dụng, đăng nhập thành công.
  - Sidebar bên trái hiển thị rõ ràng logo SafeKid và 5 mục điều hướng: *Tổng quan, Camera, Cảnh báo, Thiết bị, Cài đặt*.
  - Nhấp qua lại giữa các mục để kiểm tra tính năng chuyển trang tức thời.
- [ ] **Giao diện Di động (Mobile Bottom Nav):**
  - Giảm chiều rộng màn hình xuống `< 768px`.
  - Sidebar biến mất, thanh chuyển tab phía dưới (Bottom Nav) màu trắng xuất hiện với 5 biểu tượng sắc nét.
  - Xác nhận không có phần tử nào bị che khuất bởi Bottom Nav ở chân trang.
- [ ] **Đăng xuất:**
  - Nhấp Avatar góc trên bên phải -> Chọn *Đăng xuất* -> Quay về màn `/login`.

---

## B. Màn hình Tổng quan (Dashboard)
- [ ] **Bento Cards Stats:**
  - Tổng số Camera, thiết bị Hub, số cảnh báo chưa xử lý hiển thị chính xác theo mock data.
  - Hộp trạng thái hiển thị *"Hệ thống đang hoạt động bình thường"* (màu xanh lá) hoặc *"Hệ thống ghi nhận sự cố"* (màu đỏ) dựa trên mức độ nguy hiểm của cảnh báo.
- [ ] **Danh sách Cảnh báo gần đây:**
  - Hiển thị danh sách các sự cố chưa xử lý mới nhất.
  - Bấm nút nhanh *Đánh dấu đã xử lý* hoặc *Báo nhầm* trên thẻ cảnh báo -> Thẻ biến mất tức thời khỏi danh sách và số lượng đếm chưa đọc trên Topbar giảm đi tương ứng.

---

## C. Xem Camera & Kết nối WebRTC
- [ ] **Trạng thái camera trong danh sách:**
  - Vào mục *Camera*. Xem các nhãn trạng thái tiếng Việt: *Đang phát trực tiếp (connected)*, *Đang kết nối (connecting)*, *Lỗi kết nối (failed)*, hoặc *Chưa kết nối (idle)*.
- [ ] **Kiểm thử kết nối WebRTC (Backend hoạt động):**
  - Vào chi tiết camera *Phòng khách* -> Nhấp nút **Bắt đầu xem trực tiếp**.
  - WebSocket kết nối tới `ws://localhost:8007/ws/signaling/web_parent_01`.
  - Trình duyệt tạo SDP Offer -> Backend phản hồi SDP Answer -> Video track được nạp vào thẻ `<video>` và hiển thị luồng stream mượt mà.
- [ ] **Kiểm thử dọn dẹp tài nguyên (Cleanup):**
  - Khi đang xem camera, nhấp nút quay lại hoặc đổi sang camera khác.
  - Kiểm tra tab Network/Console: WebSocket đóng ngay lập tức, RTCPeerConnection ngắt kết nối (`closed`), các luồng camera phần cứng dừng chạy.
- [ ] **Kiểm thử khi Backend chưa chạy:**
  - Vào chi tiết camera bất kỳ -> Bấm *Bắt đầu xem trực tiếp*.
  - Sau 3 lần tự động kết nối lại (1s -> 2s -> 4s), giao diện hiển thị `<ErrorState />` màu đỏ ghi nhận lỗi tiếng Việt *"Không thể kết nối tới máy chủ camera"* kèm nút *Thử lại*.
- [ ] **Kiểm thử truyền sai Camera ID:**
  - Đi tới link `/cameras/camera_fake_id`.
  - Bấm kết nối -> Nhận gói tin lỗi từ signaling -> Hết lượt retry -> Chuyển trạng thái sang `failed` và hiển thị nút *Thử lại*.

---

## D. Công cụ vẽ vùng nguy hiểm ROI (SVG Drawer)
- [ ] **Khởi tạo và lưu đa giác (Polygon):**
  - Vào màn hình *Camera* -> Chọn camera Phòng khách -> Nhấp **Thiết lập vùng nguy hiểm (ROI)**.
  - Chọn công cụ **Vẽ đa giác**. Click ít nhất 3 điểm trên khung hình để tạo hình đa giác.
  - Nhấp vào điểm đầu tiên hoặc bấm **Hoàn tất vùng**. Nhập tên vùng *"Cầu thang"* và chọn độ nhạy, quy tắc cảnh báo.
  - Nhấp **Lưu thiết lập** -> Toast báo thành công xuất hiện.
  - Xác nhận vùng *"Cầu thang"* vừa vẽ hiển thị trong danh sách ROI và phủ đè chính xác trên trang chi tiết camera.
- [ ] **Vẽ hình chữ nhật (Rectangle):**
  - Chọn công cụ **Vẽ hình chữ nhật**. Kéo thả chuột chéo góc để tạo hình nhanh chóng.
- [ ] **Chế độ chỉnh sửa (Edit Mode):**
  - Nhấp nút **Chỉnh sửa** -> Kéo thả các neo tròn màu đỏ để thay đổi hình dạng. Nhấp đúp vào neo để xóa bớt góc.
- [ ] **Tính năng co giãn (Responsive Scale):**
  - Co giãn kích thước trình duyệt hoặc xoay ngang/dọc điện thoại.
  - Xác nhận vùng vẽ ROI không bị trôi lệch, luôn bám sát theo vị trí tĩnh tương đối trên khung hình camera.

---

## E. Quản lý Cảnh báo (Alerts)
- [ ] **Bộ lọc trạng thái:**
  - Vào trang *Cảnh báo*. Lọc theo các tab: *Chưa xử lý*, *Đã xử lý*, *Báo nhầm*.
- [ ] **Màn chi tiết sự cố:**
  - Bấm vào một cảnh báo chưa đọc -> Đi tới màn `/alerts/:id`.
  - Hiển thị ảnh snapshot có kèm viền đỏ xác định vị trí bé gặp nguy hiểm.
  - Bấm *Báo nhầm* hoặc *Đánh dấu đã xử lý* -> Trạng thái cập nhật tức thời trên UI và ghi nhận lịch sử vào sổ nhật ký hệ thống.

---

## F. Ứng dụng PWA (Progressive Web App)
- [ ] **Cài đặt độc lập (Install Prompt):**
  - Mở ứng dụng trong trình duyệt (Chrome/Edge/Safari). Chrome/Edge hỗ trợ install prompt trực tiếp; Safari/iOS có thể cài qua Add to Home Screen.
  - Đối với Chrome/Edge: Banner nhỏ dưới chân trang hiển thị: *"Cài SafeKid Monitor trên thiết bị của bạn để nhận trải nghiệm nhanh hơn."*, nhấp *Cài ứng dụng* -> Hộp thoại cài đặt native của hệ điều hành xuất hiện. Khi chấp nhận, SafeKid Monitor được đưa ra Desktop/Màn hình chính điện thoại dưới dạng Standalone app.
- [ ] **Bảo mật và Caching:**
  - Tắt mạng internet (Offline mode). Refresh lại trang.
  - Trang web vẫn tải được bình thường nhờ Service Worker cache lại App shell (HTML, CSS, JS, Fonts).
  - Kiểm tra tab Cache Storage:
    - **Không** lưu trữ bất kỳ hình ảnh snapshot của bé (`/snapshots/*`), dữ liệu API (`/api/*`), hoặc luồng truyền WebRTC để đảm bảo tuyệt đối an toàn thông tin trẻ em.
- [ ] **Banner ngoại tuyến (Offline Banner):**
  - Khi ngắt kết nối mạng, một banner màu đỏ nhạt xuất hiện trên đầu trang: *"Bạn đang ngoại tuyến. Một số chức năng như xem camera trực tiếp và nhận cảnh báo sẽ tạm thời không khả dụng."*
  - Khi bật lại mạng, banner biến mất và toast hiện: *"Đã kết nối mạng internet trở lại!"*.

---

## G. Cảnh báo thông minh (Notifications)
- [ ] **Cấp quyền thông báo hệ thống:**
  - Vào phần *Cài đặt* -> Mục *Thông báo*.
  - Nếu trình duyệt chưa được cấp quyền, hiển thị trạng thái *"Chưa cấp quyền thông báo"* kèm nút **Cho phép thông báo**.
  - Nhấp nút và đồng ý cấp quyền -> Trạng thái chuyển sang màu xanh *"Đã cho phép thông báo"*.
  - Nếu chặn quyền, giao diện chuyển sang màu đỏ và hướng dẫn mở lại cài đặt trình duyệt để cấp quyền.
- [ ] **Thử nghiệm cảnh báo & Âm thanh đẩy:**
  - Bật toggle **Âm thanh cảnh báo** -> Bấm **Gửi cảnh báo thử**.
  - Một âm thanh bíp ngắn phát ra bằng Web Audio API.
  - Một thông báo trình duyệt hiện lên góc màn hình hệ điều hành: *"Cảnh báo vùng nguy hiểm! ⚠️ Bé Vy đang tiếp cận rào chắn Ban công."*
  - Icon chuông báo trên Topbar tăng số lượng unread badge. Nhấp vào chuông -> Hộp thư đổ xuống danh sách sự cố khẩn cấp, nhấp vào tin nhắn để nhảy trực tiếp tới màn chi tiết sự cố để xử lý.
