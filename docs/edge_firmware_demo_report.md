# Báo cáo tích hợp Edge Firmware và chạy demo

**Thời điểm kiểm tra:** 17/08/2026  
**Mục tiêu:** Hoàn thiện luồng demo end-to-end cho `module_edge_firmware` trước khi triển khai lên Raspberry Pi 4.

## Kết quả

Pipeline demo đã chạy thành công bằng Docker Compose:

```text
Video demo + ONNX trên Edge
  -> MQTT alert / snapshot
  -> Backend FastAPI + PostgreSQL
  -> WebSocket thông báo cho Frontend

Frontend lưu ROI
  -> Backend API
  -> MQTT retained ROI
  -> Edge nạp ROI vào RAM
```

Edge đã kết nối MQTT, tải model ONNX, nạp 1 vùng ROI, chạy video demo lặp và phát alert/snapshot. Backend nhận được các message, lưu snapshot xuống đĩa và broadcast sự kiện `ALERT_NEW`.

## Các thay đổi đã thực hiện

### Hạ tầng Docker

- Bổ sung Mosquitto MQTT broker trong `docker-compose.yml`.
- Bổ sung PostgreSQL health check.
- Thêm service `migrate` chạy Alembic trước backend.
- Thêm service `seed` tạo dữ liệu demo một cách idempotent.
- Thiết lập phụ thuộc khởi động: migration -> seed/backend -> frontend/edge.
- Thêm cấu hình Mosquitto tại `configs/mosquitto.conf`.

### Backend

- Thêm Alembic initial migration cho users, devices, cameras, ROI zones và alerts.
- Thêm endpoint `GET /healthz`.
- Sửa import để backend chạy được cả từ package root lẫn Docker container.
- Thêm các trường hợp đồng frontend cần: `full_name`, `alerts_paused`, ROI `type`, `sensitivity`, `enabled`, `rules`.
- Bổ sung API đọc camera/ROI và API pause alert.
- Đồng bộ alert với `event_id`; snapshot dùng tên `{event_id}.jpg` để liên kết alert và ảnh.
- Backend subscribe MQTT các topic:

  - `devices/+/alerts`
  - `devices/+/snapshots/#`
  - `devices/+/webrtc/answer`

### Edge firmware

- Thêm MQTT client lâu dài cho Edge.
- Edge subscribe:

  - `devices/{camera_id}/roi/update`
  - `devices/{camera_id}/webrtc/offer`

- Edge publish:

  - `devices/{camera_id}/webrtc/answer`
  - `devices/{camera_id}/alerts`
  - `devices/{camera_id}/snapshots/{event_id}`

- Thêm `RtspVideoSource`; demo hiện dùng MP4, còn thiết bị thật có thể đặt `EDGE_RTSP_URL`.
- Bổ sung xử lý WebRTC offer thông qua MQTT.
- Sửa hợp đồng ROI: backend phải gửi `id` của zone. Nếu thiếu ID, Edge sẽ bỏ zone để tránh trạng thái ROI không xác định.

### Dữ liệu demo và giao diện

- Seed tài khoản: `demo@childrenobserver.org` / `demo12345`.
- Seed camera: `camera_living_room_01`.
- Seed tự publish retained ROI để Edge mới khởi động đã nhận được vùng giám sát.
- Frontend đăng nhập nhanh bằng tài khoản demo thật và dùng API pause alert thật.

### Scripts và kiểm thử

- Cập nhật `scripts/start_demo.ps1` để build/chạy Docker stack và chờ backend healthy.
- Cập nhật `scripts/stop_demo.ps1` để dừng stack mà giữ PostgreSQL volume.
- Thay `scripts/e2e_check.py` bằng smoke test cho kiến trúc MQTT hiện tại.
- Script E2E có xử lý Windows Selector event loop vì `aiomqtt` không tương thích Windows Proactor loop.

## Kết quả xác minh

| Hạng mục | Kết quả |
| --- | --- |
| Python compile check | Pass |
| MQTT unit tests | `3 passed` |
| Docker Compose config | Pass |
| Migration Alembic trên PostgreSQL Docker | Pass |
| Seed demo | Pass |
| Backend health check | Pass |
| E2E JWT + Camera/ROI API | Pass |
| API publish retained ROI qua MQTT | Pass |
| Edge nhận và nạp ROI | Pass (`ROI engine: 1 zones`) |
| Edge chạy ONNX/video demo | Pass |
| Edge publish alert/snapshot | Pass |
| Backend lưu alert/snapshot | Pass |

Lệnh E2E đã chạy thành công:

```powershell
uv run python scripts/e2e_check.py
```

Kết quả:

```text
E2E PASS: auth, camera/ROI API, retained ROI MQTT, alert and snapshot MQTT
```

## Trạng thái chạy demo

Các service Docker đã được xác nhận hoạt động:

| Service | Địa chỉ / trạng thái |
| --- | --- |
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8007 (healthy) |
| MQTT broker | `localhost:1883` |
| PostgreSQL | `localhost:5432` (healthy) |
| Edge demo | đang chạy pipeline ONNX/video |

## Cách chạy lại

```powershell
.\scripts\start_demo.ps1
uv run python scripts/e2e_check.py
```

Đăng nhập frontend bằng:

```text
Email: demo@childrenobserver.org
Password: demo12345
```

Dừng môi trường:

```powershell
.\scripts\stop_demo.ps1
```

## Phạm vi chưa kiểm chứng

- Chưa chạy trên Raspberry Pi 4 phần cứng thật.
- Chưa xác minh RTSP từ IP Camera thật; cần đặt `EDGE_RTSP_URL` trên Pi.
- Chưa kiểm thử luồng WebRTC media trực tiếp bằng trình duyệt thật, mặc dù signaling MQTT offer/answer đã được tích hợp.
- MQTT hiện dùng anonymous local broker để phục vụ demo. Khi triển khai thực tế phải bật xác thực, TLS và quản lý secret.
