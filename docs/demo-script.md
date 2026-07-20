# Kịch bản Thuyết trình & Trình diễn MVP (Demo Script)

Kịch bản này được thiết kế để hỗ trợ người trình bày thuyết minh và thực hiện thao tác demo trực quan SafeKid Monitor trước khách hàng, hội đồng giám khảo hoặc các nhà đầu tư.

---

## 1. Mở đầu: Giới thiệu dự án
- **Slide/Màn hình hiển thị:** Màn hình đăng nhập (`/login`).
- **Nội dung thuyết minh:**
  > "Chào quý vị, SafeKid Monitor là giải pháp giám sát an toàn thông minh dành riêng cho gia đình có con nhỏ thông qua hệ thống camera Edge tích hợp trí tuệ nhân tạo. 
  > Khác biệt lớn nhất của SafeKid Monitor so với camera thông thường là cho phép phụ huynh tự định nghĩa ranh giới nguy hiểm (ROI) của riêng nhà mình (như lan can, bếp, cầu thang) bằng công cụ vẽ trực quan, từ đó hệ thống sẽ cảnh báo đa kênh tức thời kèm ảnh chụp sự cố ngay khi phát hiện trẻ tiếp cận vùng nguy hiểm."
- **Thao tác:**
  - Nhập thông tin tài khoản demo. Bấm **Đăng nhập**.

---

## 2. Trình diễn 1: Dashboard Tổng quan
- **Slide/Màn hình hiển thị:** Trang tổng quan (`/dashboard`).
- **Nội dung thuyết minh:**
  > "Sau khi đăng nhập, phụ huynh sẽ được tiếp cận ngay với bảng điều khiển Bento Grid trực quan. 
  > Tại đây, chúng ta có thể thấy ngay trạng thái tổng quát: Hệ thống đang hoạt động bình thường, số lượng camera đang trực tuyến, các thiết bị Edge Gateway hoạt động tốt, và đặc biệt là danh sách sự cố khẩn cấp chưa xử lý."
- **Thao tác:**
  - Chỉ vào các thẻ Bento chỉ số (Cameras Online, ROI Zones active).
  - Di chuột qua danh sách cảnh báo gần đây ở phía dưới.

---

## 3. Trình diễn 2: Danh sách Camera & Luồng phát WebRTC
- **Slide/Màn hình hiển thị:** Danh sách camera (`/cameras`) -> Bấm chọn một camera -> Màn hình chi tiết camera (`/cameras/:id`).
- **Nội dung thuyết minh:**
  > "Mục 'Camera' quản lý danh sách toàn bộ luồng quay trong nhà. Mỗi camera hiển thị trạng thái kết nối tiếng Việt rõ ràng. 
  > Khi đi vào chi tiết một camera như Phòng khách, chúng ta có thể kết nối luồng stream trực tiếp độ trễ thấp thông qua công nghệ WebRTC đầu-cuối an toàn bằng cách bấm nút 'Bắt đầu xem trực tiếp'. 
  > Kể cả khi máy chủ camera gặp sự cố ngoại tuyến, giao diện vẫn hiển thị lỗi có kiểm soát thay vì bị crash ứng dụng."
- **Thao tác:**
  - Bấm **Bắt đầu xem trực tiếp**.
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
  - Nhập tên vùng: *"Khu vực Lan can"*.
  - Bật các quy tắc AI: *Cảnh báo khi đi vào vùng* và *Cảnh báo khi đứng trong vùng quá 5 giây*.
  - Bấm **Lưu thiết lập**.

---

## 5. Trình diễn 4: Đồng bộ vùng ROI lên luồng trực tiếp
- **Slide/Màn hình hiển thị:** Quay lại màn hình chi tiết camera (`/cameras/:id`).
- **Nội dung thuyết minh:**
  > "Sau khi lưu cấu hình, vùng nguy hiểm vừa vẽ lập tức được cập nhật đồng bộ lên luồng xem trực tuyến của camera. 
  > Toàn bộ tọa độ góc vẽ được lưu trữ dưới dạng chuẩn hóa tỉ lệ từ `0.0` đến `1.0`. Nhờ vậy, khi chúng ta thay đổi kích thước trình duyệt hoặc xoay màn hình điện thoại, ranh giới vẽ luôn bám khít chính xác vào vị trí camera mà không bị trôi lệch góc."
- **Thao tác:**
  - Thu nhỏ/Phóng to kích thước cửa sổ trình duyệt để cho thấy vùng đỏ ROI tự động co giãn theo tỷ lệ khung hình video thực tế.

---

## 6. Trình diễn 5: Quản lý và xử lý Cảnh báo an toàn
- **Slide/Màn hình hiển thị:** Trang danh sách cảnh báo (`/alerts`).
- **Nội dung thuyết minh:**
  > "Khi camera biên phát hiện trẻ đi vào vùng ROI nguy hiểm, hệ thống sẽ ghi nhận cảnh báo sự cố khẩn cấp. 
  > Trang 'Cảnh báo' là nơi phụ huynh quản lý và lọc nhanh các sự cố theo mức độ nghiêm trọng hoặc trạng thái. Mỗi cảnh báo đi kèm thông tin chi tiết về thời gian, camera ghi nhận và ảnh snapshot khoanh vùng bé gặp nguy hiểm."
- **Thao tác:**
  - Nhấp chọn tab lọc trạng thái *"Chưa xử lý"*.
  - Nhấp nút nhanh **Đánh dấu đã xử lý** trên một thẻ sự cố, hoặc chọn **Báo nhầm** (False Alarm) để gửi dữ liệu hiệu chỉnh giúp AI tối ưu hóa độ nhạy.

---

## 7. Trình diễn 6: Chi tiết Cảnh báo & SecureImage
- **Slide/Màn hình hiển thị:** Màn chi tiết cảnh báo (`/alerts/:id`).
- **Nội dung thuyết minh:**
  > "Đi vào chi tiết một cảnh báo, phụ huynh sẽ thấy ảnh chụp sự cố kích thước lớn. Để đảm bảo an toàn tuyệt đối thông tin trẻ em, ảnh chụp này được tải bảo mật qua SecureImage (chỉ hiển thị dưới dạng Blob URL tạm thời được thu hồi ngay khi đóng trang). 
  > Từ đây phụ huynh có thể đưa ra quyết định nhanh như gọi điện cho người thân trong nhà hoặc bật xem trực tiếp camera liên quan để kiểm tra tình trạng của con."
- **Thao tác:**
  - Chỉ vào ảnh snapshot có vẽ khung bao quanh đứa trẻ.
  - Chỉ vào khu vực lịch sử ghi nhận xử lý sự cố.

---

## 8. Trình diễn 7: Cài đặt Thông báo & Demo cảnh báo đẩy trình duyệt
- **Slide/Màn hình hiển thị:** Màn hình cài đặt thông báo (`/settings/notifications`).
- **Nội dung thuyết minh:**
  > "SafeKid Monitor hỗ trợ gửi cảnh báo đa kênh. Trong phần cài đặt thông báo, phụ huynh có thể xin quyền gửi thông báo đẩy trực tiếp trên hệ thống trình duyệt của điện thoại hoặc máy tính. 
  > Bây giờ, tôi sẽ thực hiện giả lập một sự cố an toàn thực tế."
- **Thao tác:**
  - Bấm **Cho phép thông báo** để kích hoạt quyền.
  - Bấm nút **Gửi cảnh báo thử** (Demo Alert).
- **Kết quả hiển thị:**
  - Một tiếng còi báo "Bíp" ngắn phát ra qua loa thiết bị.
  - Một thông báo đẩy native của HĐH xuất hiện ở góc màn hình: *"Cảnh báo vùng nguy hiểm! ⚠️ Bé Vy đang tiếp cận rào chắn Ban công."*
  - Icon chuông báo Topbar tăng số lượng unread badge. Nhấp mở chuông để kiểm tra hộp thư thông báo thông minh.

---

## 9. Trình diễn 8: Quản lý Quyền riêng tư & An toàn dữ liệu
- **Slide/Màn hình hiển thị:** Trang cài đặt riêng tư (`/settings/privacy`).
- **Nội dung thuyết minh:**
  > "Do liên quan đến trẻ nhỏ, quyền riêng tư là ưu tiên cao nhất của dự án. 
  > Ứng dụng PWA của chúng tôi được thiết kế bảo mật tuyệt đối: không cache video trực tiếp hay lưu trữ ảnh chụp sự cố vào bộ nhớ cục bộ của trình duyệt. 
  > Tại trang cài đặt này, phụ huynh có thể cấu hình chu kỳ tự động hủy ảnh sự cố (như tự hủy sau 7 ngày hoặc xóa ngay sau khi xem) và tra cứu lịch sử ghi nhận ai đã truy cập xem camera."
- **Thao tác:**
  - Thay đổi chu kỳ tự hủy ảnh cảnh báo.
  - Cuộn chuột xem bảng lịch sử nhật ký truy cập (Audit logs).
  - Bấm nút *Xóa toàn bộ dữ liệu lưu trữ* -> Xác nhận trên modal cảnh báo.

---

## 10. Trình diễn 9: Đóng gói PWA & Trải nghiệm ngoại tuyến (Offline)
- **Slide/Màn hình hiển thị:** Trình duyệt Chrome/Edge của thiết bị.
- **Nội dung thuyết minh:**
  > "SafeKid Monitor được đóng gói hoàn chỉnh dưới dạng PWA. 
  > Khi phụ huynh mở trang web, hệ thống sẽ đề xuất cài đặt thành ứng dụng độc lập trên màn hình chính của điện thoại. 
  > Kể cả khi mất kết nối mạng internet hoàn toàn, ứng dụng vẫn tải được giao diện nền (App Shell) nhờ Service Worker chạy ngầm, hiển thị banner ngoại tuyến rõ ràng để cha mẹ luôn làm chủ tình trạng kết nối."
- **Thao tác:**
  - Tắt WiFi hoặc giả lập Offline trong tab Network của Chrome DevTools.
  - Chỉ ra banner báo trạng thái ngoại tuyến xuất hiện phía dưới Topbar.

---

## 11. Kết luận buổi thuyết trình
- **Nội dung thuyết minh:**
  > "Như vậy, bản MVP của SafeKid Monitor đã hoàn thiện đầy đủ toàn bộ luồng trải nghiệm của người dùng: từ xem camera trực tiếp WebRTC, tự tay cấu hình ranh giới nguy hiểm ROI ảo, nhận cảnh báo âm thanh đa kênh thời gian thực, xử lý sự cố cho đến quản lý tối đa quyền riêng tư của bé. 
  > Đây là tiền đề vững chắc để dự án tích hợp sâu hơn với hệ thống AI biên trên phần cứng camera thực tế trong tương lai. Xin chân thành cảm ơn!"
