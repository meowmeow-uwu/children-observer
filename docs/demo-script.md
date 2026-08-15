# Kịch bản Thuyết trình & Trình diễn MVP (Demo Script)

Kịch bản này được thiết kế để hỗ trợ người trình bày thuyết minh và thực hiện thao tác demo trực quan SafeKid Monitor trước khách hàng, hội đồng giám khảo hoặc các nhà đầu tư.

> **Chuẩn bị trước buổi demo:** Chạy lệnh `.\scripts\start_demo.ps1` để khởi động đầy đủ Backend (`localhost:8007`), MQTT Broker (`localhost:1883`) và Edge Firmware demo stream. Tài khoản demo: `parent@safekid.local` / `demo1234`.

---

## 1. Mở đầu: Giới thiệu dự án & Đăng nhập thật

- **Slide/Màn hình hiển thị:** Màn hình đăng nhập (`/login`).
- **Nội dung thuyết minh:**
  > "Chào quý vị, SafeKid Monitor là giải pháp giám sát an toàn thông minh dành riêng cho gia đình có con nhỏ thông qua hệ thống camera Edge tích hợp trí tuệ nhân tạo. 
  > Khác biệt lớn nhất của SafeKid Monitor so với camera thông thường là cho phép phụ huynh tự định nghĩa ranh giới nguy hiểm (ROI) của riêng nhà mình (như lan can, bếp, cầu thang) bằng công cụ vẽ trực quan, từ đó hệ thống sẽ cảnh báo đa kênh tức thời kèm ảnh chụp sự cố ngay khi phát hiện trẻ tiếp cận vùng nguy hiểm."
- **Thao tác:**
  - Nhập email và mật khẩu tài khoản demo → Bấm **Đăng nhập hệ thống**.
  - *(Hậu trường)*: Frontend gọi `POST /api/auth/login` → nhận JWT `access_token` thật → gọi `GET /api/auth/me` → lấy profile phụ huynh.
  - Kiểm tra nhanh tab **Network** → chỉ ra header `Authorization: Bearer <token>` xuất hiện trên mọi request.

---

## 2. Trình diễn 1: Dashboard Tổng quan — Dữ liệu thật từ Backend

- **Slide/Màn hình hiển thị:** Trang tổng quan (`/dashboard`).
- **Nội dung thuyết minh:**
  > "Sau khi đăng nhập, phụ huynh sẽ được tiếp cận ngay với bảng điều khiển Bento Grid trực quan. 
  > Tại đây, chúng ta có thể thấy ngay trạng thái tổng quát: Hệ thống đang hoạt động bình thường, số lượng camera đang trực tuyến, các thiết bị Edge Gateway hoạt động tốt, và đặc biệt là danh sách sự cố khẩn cấp chưa xử lý — toàn bộ đều là dữ liệu thật được đọc từ server."
- **Thao tác:**
  - Chỉ vào các thẻ Bento chỉ số (Cameras Online, ROI Zones active) — dữ liệu lấy từ `GET /api/cameras/` và `GET /api/alerts/`.
  - Di chuột qua danh sách cảnh báo gần đây ở phía dưới.

---

## 3. Trình diễn 2: Danh sách Camera & Luồng phát WebRTC

- **Slide/Màn hình hiển thị:** Danh sách camera (`/cameras`) → Bấm chọn một camera → Màn hình chi tiết camera (`/cameras/:id`).
- **Nội dung thuyết minh:**
  > "Mục 'Camera' quản lý danh sách toàn bộ luồng quay trong nhà. Danh sách được tải từ backend API, mỗi camera hiển thị trạng thái kết nối tiếng Việt rõ ràng. 
  > Khi đi vào chi tiết một camera như Phòng khách, chúng ta có thể kết nối luồng stream trực tiếp độ trễ thấp thông qua công nghệ WebRTC đầu-cuối an toàn bằng cách bấm nút 'Bắt đầu xem trực tiếp'. 
  > Kể cả khi máy chủ camera gặp sự cố ngoại tuyến, giao diện vẫn hiển thị lỗi có kiểm soát thay vì bị crash ứng dụng."
- **Thao tác:**
  - Bấm **Bắt đầu xem trực tiếp**.
  - *(Hậu trường)*: Frontend mở WebSocket `ws://localhost:8007/ws/signaling/web_parent_01?token=<JWT>` → tạo SDP Offer → gửi lên server → Backend forward qua MQTT `devices/camera_01/webrtc/offer` → Edge (`aiortc`) tạo SDP Answer → Backend relay về WebSocket → Frontend thiết lập luồng P2P.
  - Chỉ vào vùng live stream hoặc màn hình báo lỗi/kết nối lại nếu máy chủ camera đang tắt.

---

## 4. Trình diễn 3: Thiết lập vùng nguy hiểm ROI (Core MVP)

- **Slide/Màn hình hiển thị:** Trang vẽ ROI của camera (`/roi/:cameraId`).
- **Nội dung thuyết minh:**
  > "Đây là tính năng cốt lõi của SafeKid Monitor. Phụ huynh không cần bất kỳ kiến thức kỹ thuật nào vẫn có thể tự tay vẽ ranh giới ảo cảnh báo nguy hiểm trực tiếp trên hình ảnh camera. 
  > Chúng tôi hỗ trợ công cụ vẽ Đa giác (Polygon) để vẽ các góc bo phức tạp như khu vực cầu thang, hoặc công cụ vẽ Hình chữ nhật (Rectangle) cực nhanh cho cửa sổ, ban công."
- **Thao tác:**
  - Chọn công cụ **Vẽ đa giác**. Nhấp 4 điểm tạo thành vùng bảo vệ quanh khu vực nguy hiểm.
  - Bấm **Hoàn tất vùng**.
  - Nhập tên vùng: *"Khu vực Lan can"*. Chọn độ nhạy `Cao`.
  - Bật các quy tắc AI: *Cảnh báo khi đi vào vùng* và *Cảnh báo khi đứng trong vùng quá 5 giây*.
  - Bấm **Lưu thiết lập**.
  - *(Hậu trường)*: Frontend gọi `POST /api/cameras/{camera_id_string}/roi` với payload tọa độ chuẩn hóa `[0.0 → 1.0]` → Backend lưu DB → Publish MQTT topic `devices/{device_id}/roi/update` → Edge Raspberry Pi nhận, quy đổi sang pixel `(X = point.x × W_frame)` và nạp lại Mask Polygon trên RAM ngay lập tức.

---

## 5. Trình diễn 4: Đồng bộ vùng ROI lên luồng trực tiếp

- **Slide/Màn hình hiển thị:** Quay lại màn hình chi tiết camera (`/cameras/:id`).
- **Nội dung thuyết minh:**
  > "Sau khi lưu cấu hình, vùng nguy hiểm vừa vẽ lập tức được cập nhật đồng bộ lên luồng xem trực tuyến của camera. 
  > Toàn bộ tọa độ góc vẽ được lưu trữ dưới dạng chuẩn hóa tỉ lệ từ `0.0` đến `1.0`. Nhờ vậy, khi chúng ta thay đổi kích thước trình duyệt hoặc xoay màn hình điện thoại, ranh giới vẽ luôn bám khít chính xác vào vị trí camera mà không bị trôi lệch góc."
- **Thao tác:**
  - Thu nhỏ/Phóng to kích thước cửa sổ trình duyệt để cho thấy vùng đỏ ROI tự động co giãn theo tỷ lệ khung hình video thực tế.
  - Chỉ ra vùng ROI đè lên đúng khu vực nguy hiểm đã vẽ, hiển thị tên vùng và viền vàng nhận diện.

---

## 6. Trình diễn 5: Cảnh báo Real-time từ Edge AI (⭐ Điểm nhấn kỹ thuật)

- **Slide/Màn hình hiển thị:** Màn hình chi tiết camera (`/cameras/:id`) — đang xem live stream.
- **Nội dung thuyết minh:**
  > "Đây là điểm sáng kỹ thuật cốt lõi nhất của hệ thống. Trong khi chúng ta đang xem, pipeline AI trên thiết bị biên Raspberry Pi liên tục phân tích từng frame video bằng mô hình YOLO, kiểm tra xem trẻ có đang tiếp cận vùng nguy hiểm đã vẽ hay không bằng thuật toán Point-in-Polygon.
  > Khi phát hiện vi phạm, Edge AI lập tức bắn 2 gói tin qua MQTT: một gói JSON mô tả sự cố và một gói ảnh JPEG nhị phân làm bằng chứng. Backend nhận, lưu vào database, rồi broadcast ngay lập tức qua WebSocket tới Frontend của phụ huynh."
- **Thao tác:**
  - Quan sát màn hình — khi trẻ trong video bước vào vùng ROI:
    - 🔊 Còi báo động phát ra.
    - 🔴 Toast đỏ bật lên với nội dung sự cố.
    - 🔔 Badge chuông trên Topbar tăng lên.
  - Kiểm tra tab **Network/Console**: WebSocket nhận message `{"type": "ALERT_NEW", "data": {...}}`.
- **Kết quả kỳ vọng:** Độ trễ từ khi Edge phát hiện đến khi Toast hiện trên Frontend < 500ms.

---

## 7. Trình diễn 6: Quản lý và xử lý Cảnh báo an toàn

- **Slide/Màn hình hiển thị:** Trang danh sách cảnh báo (`/alerts`).
- **Nội dung thuyết minh:**
  > "Trang 'Cảnh báo' là nơi phụ huynh quản lý và lọc nhanh các sự cố theo mức độ nghiêm trọng hoặc trạng thái. Mỗi cảnh báo đi kèm thông tin chi tiết về thời gian, camera ghi nhận và ảnh snapshot khoanh vùng bé gặp nguy hiểm."
- **Thao tác:**
  - Nhấp chọn tab lọc trạng thái *"Chưa xử lý"*.
  - Nhấp nút nhanh **Đánh dấu đã xử lý** trên một thẻ sự cố → Gọi `PATCH /api/alerts/{id}` với `status: "resolved"`, hoặc chọn **Báo nhầm** (False Alarm) với `status: "false_alarm"` để gửi dữ liệu hiệu chỉnh giúp AI tối ưu hóa độ nhạy.

---

## 8. Trình diễn 7: Chi tiết Cảnh báo & SecureImage

- **Slide/Màn hình hiển thị:** Màn chi tiết cảnh báo (`/alerts/:id`).
- **Nội dung thuyết minh:**
  > "Đi vào chi tiết một cảnh báo, phụ huynh sẽ thấy ảnh chụp sự cố kích thước lớn. Ảnh này được tải an toàn từ server Backend tại đường dẫn `/snapshots/{filename}` — chỉ người dùng đã xác thực mới truy cập được. Đây là ảnh bằng chứng thực tế do Edge AI chụp và gửi lên.
  > Từ đây phụ huynh có thể đưa ra quyết định nhanh như gọi điện cho người thân trong nhà hoặc bật xem trực tiếp camera liên quan để kiểm tra tình trạng của con."
- **Thao tác:**
  - Chỉ vào ảnh snapshot có vẽ khung bao quanh vị trí phát hiện đứa trẻ (bounding box từ YOLO).
  - Chỉ vào khu vực lịch sử ghi nhận xử lý sự cố.

---

## 9. Trình diễn 8: Cài đặt Thông báo & Demo cảnh báo đẩy trình duyệt

- **Slide/Màn hình hiển thị:** Màn hình cài đặt thông báo (`/settings/notifications`).
- **Nội dung thuyết minh:**
  > "SafeKid Monitor hỗ trợ gửi cảnh báo đa kênh: thông báo đẩy trình duyệt (Web Push) và Telegram Bot. 
  > Bây giờ, tôi sẽ thực hiện giả lập một sự cố an toàn thực tế."
- **Thao tác:**
  - Bấm **Cho phép thông báo** để kích hoạt quyền Web Push.
  - Bấm nút **Gửi cảnh báo thử** (Demo Alert).
- **Kết quả hiển thị:**
  - Một tiếng còi báo "Bíp" ngắn phát ra qua loa thiết bị (Web Audio API).
  - Một thông báo đẩy native của HĐH xuất hiện ở góc màn hình: *"Cảnh báo vùng nguy hiểm! ⚠️ Bé Vy đang tiếp cận rào chắn Ban công."*
  - Icon chuông báo Topbar tăng số lượng unread badge. Nhấp mở chuông để kiểm tra hộp thư thông báo thông minh.

---

## 10. Trình diễn 9: Quản lý Quyền riêng tư & An toàn dữ liệu

- **Slide/Màn hình hiển thị:** Trang cài đặt riêng tư (`/settings/privacy`).
- **Nội dung thuyết minh:**
  > "Do liên quan đến trẻ nhỏ, quyền riêng tư là ưu tiên cao nhất của dự án. 
  > Ứng dụng PWA của chúng tôi được thiết kế bảo mật tuyệt đối: không cache video trực tiếp hay lưu trữ ảnh chụp sự cố vào bộ nhớ cục bộ của trình duyệt. Dữ liệu snapshot chỉ được truy cập qua authenticated API endpoint với JWT token hợp lệ.
  > Tại trang cài đặt này, phụ huynh có thể cấu hình chu kỳ tự động hủy ảnh sự cố và tra cứu lịch sử ghi nhận ai đã truy cập xem camera."
- **Thao tác:**
  - Thay đổi chu kỳ tự hủy ảnh cảnh báo.
  - Cuộn chuột xem bảng lịch sử nhật ký truy cập (Audit logs).
  - Bấm nút *Xóa toàn bộ dữ liệu lưu trữ* → Xác nhận trên modal cảnh báo.

---

## 11. Trình diễn 10: Đóng gói PWA & Trải nghiệm ngoại tuyến (Offline)

- **Slide/Màn hình hiển thị:** Trình duyệt Chrome/Edge của thiết bị.
- **Nội dung thuyết minh:**
  > "SafeKid Monitor được đóng gói hoàn chỉnh dưới dạng PWA. 
  > Khi phụ huynh mở trang web, hệ thống sẽ đề xuất cài đặt thành ứng dụng độc lập trên màn hình chính của điện thoại. 
  > Kể cả khi mất kết nối mạng internet hoàn toàn, ứng dụng vẫn tải được giao diện nền (App Shell) nhờ Service Worker chạy ngầm, hiển thị banner ngoại tuyến rõ ràng để cha mẹ luôn làm chủ tình trạng kết nối."
- **Thao tác:**
  - Tắt WiFi hoặc giả lập Offline trong tab Network của Chrome DevTools.
  - Chỉ ra banner báo trạng thái ngoại tuyến xuất hiện phía dưới Topbar.

---

## 12. Kết luận buổi thuyết trình

- **Nội dung thuyết minh:**
  > "Như vậy, bản MVP của SafeKid Monitor đã hoàn thiện đầy đủ toàn bộ luồng trải nghiệm E2E: từ xác thực JWT thật với backend, xem camera trực tiếp WebRTC P2P độ trễ thấp, tự tay cấu hình ranh giới nguy hiểm ROI ảo và đồng bộ tức thời xuống thiết bị biên Edge AI qua MQTT, đến nhận cảnh báo âm thanh đa kênh thời gian thực khi AI phát hiện vi phạm, và xử lý sự cố cho đến quản lý tối đa quyền riêng tư của bé. 
  > Đây là tiền đề vững chắc để dự án tích hợp sâu hơn với hệ thống AI biên trên phần cứng camera thực tế trong tương lai. Xin chân thành cảm ơn!"
