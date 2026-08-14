# 📋 Tài Liệu Chi Tiết API Endpoints, MQTT Topics & Data Payloads
**Hệ thống:** AI Child Guardian (Children Observer)  

---

## 📑 Mục Lục
1. [Tổng Quan Kiến Trúc Communication](#1-tổng-quan-kiến-trúc-communication)
2. [REST API Endpoints](#2-rest-api-endpoints)
   - [Authentication Domain (`/api/auth`)](#auth-domain)
   - [Devices Domain (`/api/devices`)](#devices-domain)
   - [Cameras Domain (`/api/cameras`)](#cameras-domain)
   - [Alerts Domain (`/api/alerts`)](#alerts-domain)
   - [WebRTC Signaling Domain (`/api/webrtc`)](#webrtc-domain)
3. [WebSocket Signaling Interface](#3-websocket-signaling-interface)
4. [MQTT Topics & Payloads (Edge AI ↔ Backend)](#4-mqtt-topics--payloads)

---

## 1. Tổng Quan Kiến Trúc Communication

Hệ thống giao tiếp qua 3 thức chính:
- **RESTful API (HTTP JSON)**: Quản lý Authentication, Thiết bị, Camera, Vùng cấm (ROI) và Tra cứu Cảnh báo.
- **WebSocket (WS JSON)**: Truyền tải tín hiệu WebRTC (Signaling) thời gian thực và Broadcast Cảnh báo tức thời tới Web Frontend.
- **MQTT (Pub/Sub JSON & Binary)**: Giao tiếp hai chiều giữa Backend Server và các thiết bị Raspberry Pi ở tầng Edge (Phát hiện nguy hiểm, truyền ảnh snapshot, cấu hình ROI, WebRTC Offer/Answer).

---

## 2. REST API Endpoints

Tất cả các Request cần Bảo mật đều phải đính kèm Header:
`Authorization: Bearer <JWT_TOKEN>`

---

### <a id="auth-domain"></a>🔑 Authentication Domain (`/api/auth`)

#### 1. Đăng ký Tài khoản Phụ huynh
- **Method / Path:** `POST /api/auth/register`
- **Auth Required:** No
- **Request Body (JSON):**
  ```json
  {
    "email": "parent@gmail.com",
    "password": "strongpassword123",
    "full_name": "Nguyen Van A",
    "phone": "0912345678"
  }
  ```
- **Response 200 (JSON):**
  ```json
  {
    "id": 1,
    "email": "parent@gmail.com",
    "full_name": "Nguyen Van A",
    "phone": "0912345678",
    "telegram_chat_id": null,
    "created_at": "2026-08-14T04:00:00Z"
  }
  ```
- **Response 400 (JSON):** `{"detail": "Email này đã được đăng ký."}`

---

#### 2. Đăng nhập
- **Method / Path:** `POST /api/auth/login`
- **Auth Required:** No
- **Request Body (JSON):**
  ```json
  {
    "email": "parent@gmail.com",
    "password": "strongpassword123"
  }
  ```
- **Response 200 (JSON):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Response 401 (JSON):** `{"detail": "Email hoặc mật khẩu không chính xác"}`

---

#### 3. Lấy Thông tin Profile Hiện tại
- **Method / Path:** `GET /api/auth/me`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response 200 (JSON):**
  ```json
  {
    "id": 1,
    "email": "parent@gmail.com",
    "full_name": "Nguyen Van A",
    "phone": "0912345678",
    "telegram_chat_id": 123456789
  }
  ```

---

#### 4. Cập nhật Profile (Liên kết Telegram Chat ID)
- **Method / Path:** `PATCH /api/auth/me`
- **Auth Required:** Yes (`Bearer <token>`)
- **Request Body (JSON):**
  ```json
  {
    "full_name": "Nguyen Van A Updated",
    "telegram_chat_id": 987654321
  }
  ```
- **Response 200 (JSON):** *(Trả về User Profile đã cập nhật)*
- **Response 400 (JSON):** `{"detail": "Telegram Chat ID đã được liên kết với một tài khoản khác."}`

---

### <a id="devices-domain"></a>📱 Devices Domain (`/api/devices`)

#### 1. Lấy Danh sách Thiết bị (Raspberry Pi)
- **Method / Path:** `GET /api/devices/`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response 200 (JSON):**
  ```json
  [
    {
      "id": 1,
      "mac_address": "B8:27:EB:00:00:01",
      "name": "Pi Phòng Khách",
      "status": "online",
      "created_at": "2026-08-14T04:00:00Z"
    }
  ]
  ```

---

#### 2. Đăng ký Thiết bị Raspberry Pi Mới
- **Method / Path:** `POST /api/devices/`
- **Auth Required:** Yes (`Bearer <token>`)
- **Request Body (JSON):**
  ```json
  {
    "mac_address": "B8:27:EB:00:00:01",
    "name": "Pi Phòng Khách",
    "device_secret_key": "secret123"
  }
  ```
- **Response 200 (JSON):** *(Trả về thông tin Device đã đăng ký)*

---

#### 3. Xóa Thiết bị
- **Method / Path:** `DELETE /api/devices/{device_id}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response 200 (JSON):**
  ```json
  {
    "detail": "Xóa thiết bị và các dữ liệu liên quan thành công."
  }
  ```

---

#### 4. Chia sẻ Quyền Giám sát Thiết bị
- **Method / Path:** `POST /api/devices/{device_id}/share`
- **Auth Required:** Yes (`Bearer <token>`)
- **Request Body (JSON):**
  ```json
  {
    "email": "grandma@gmail.com",
    "role": "VIEWER"
  }
  ```
- **Response 200 (JSON):** `{"detail": "Chia sẻ thiết bị thành công cho grandma@gmail.com"}`
- **Response 403 (JSON):** `{"detail": "Bạn không có quyền quản lý thiết bị này."}`
- **Response 404 (JSON):** `{"detail": "Không tìm thấy người dùng với email này."}`

---

#### 5. Thu hồi Quyền Chia sẻ Thiết bị
- **Method / Path:** `DELETE /api/devices/{device_id}/share/{email}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response 200 (JSON):** `{"detail": "Đã thu hồi quyền truy cập của grandma@gmail.com."}`

---

### <a id="cameras-domain"></a>📹 Cameras Domain (`/api/cameras`)

#### 1. Lấy Danh sách Camera & Vùng Cấm (ROI)
- **Method / Path:** `GET /api/cameras/`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response 200 (JSON):**
  ```json
  [
    {
      "id": 1,
      "camera_id_string": "cam_living_room_01",
      "device_id": 1,
      "name": "Camera Ban Công",
      "location": "Ban công tầng 2",
      "rtsp_url": "rtsp://192.168.1.100:554/stream1",
      "status": "online",
      "is_active": true,
      "roi_zones": [
        {
          "id": 10,
          "name": "Vùng Nguy Hiểm Lan Can",
          "sensitivity": "high",
          "enabled": true,
          "points": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.5, "y": 0.1},
            {"x": 0.5, "y": 0.8},
            {"x": 0.1, "y": 0.8}
          ]
        }
      ]
    }
  ]
  ```

---

#### 2. Thêm Camera Mới
- **Method / Path:** `POST /api/cameras/`
- **Auth Required:** Yes (`Bearer <token>`)
- **Request Body (JSON):**
  ```json
  {
    "camera_id_string": "cam_living_room_01",
    "device_id": 1,
    "name": "Camera Ban Công",
    "location": "Ban công tầng 2",
    "rtsp_url": "rtsp://192.168.1.100:554/stream1"
  }
  ```
- **Response 200 (JSON):** *(Trả về CameraResponse)*
- **Response 400 (JSON):** `{"detail": "Camera ID 'cam_living_room_01' đã tồn tại."}`

---

#### 3. Cấu hình / Cập nhật Vùng Cấm (ROI Zones)
- **Method / Path:** `POST /api/cameras/{camera_id_string}/roi`
- **Auth Required:** Yes (`Bearer <token>`)
- **Request Body (JSON):**
  ```json
  [
    {
      "name": "Ban công nguy hiểm",
      "sensitivity": "high",
      "enabled": true,
      "points": [
        {"x": 0.12, "y": 0.15},
        {"x": 0.65, "y": 0.15},
        {"x": 0.65, "y": 0.85},
        {"x": 0.12, "y": 0.85}
      ]
    }
  ]
  ```
- **Response 200 (JSON):** *(Danh sách ROIZoneResponse)*

---

#### 4. Xóa Camera
- **Method / Path:** `DELETE /api/cameras/{camera_id_string}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response 200 (JSON):** `{"detail": "Xóa Camera thành công."}`

---

### <a id="alerts-domain"></a>🚨 Alerts Domain (`/api/alerts`)

#### 1. Lấy Danh sách Cảnh báo (Có Filter)
- **Method / Path:** `GET /api/alerts/`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters:**
  - `camera_id`: (string, optional) VD: `cam_living_room_01`
  - `start_date`: (ISO 8601 datetime, optional) VD: `2026-08-14T00:00:00Z`
  - `end_date`: (ISO 8601 datetime, optional)
  - `limit`: (int, default=50)
- **Response 200 (JSON):**
  ```json
  [
    {
      "id": 101,
      "camera_id": 1,
      "title": "Trẻ trèo lan can ban công",
      "severity": "danger",
      "snapshot_url": "data/snapshots/cam_01_1786675200.jpg",
      "roi_name": "Ban công nguy hiểm",
      "created_at": "2026-08-14T04:15:30Z"
    }
  ]
  ```

---

#### 2. Kích hoạt Cảnh báo Mới (AI Engine / External HTTP Call)
- **Method / Path:** `POST /api/alerts/`
- **Auth Required:** No (Internal Service Key / Service Call)
- **Request Body (JSON):**
  ```json
  {
    "camera_id": "cam_living_room_01",
    "title": "Trẻ ngã té cầu thang",
    "severity": "danger",
    "snapshot_url": "snapshot_1786675200.jpg",
    "roi_name": "Khu vực Cầu Thang"
  }
  ```
- **Response 200 (JSON):** *(Trả về thông tin Alert Record đã tạo)*

---

### <a id="webrtc-domain"></a>📡 WebRTC Signaling Domain (`/api/webrtc`)

#### 1. Gửi SDP Offer
- **Method / Path:** `POST /api/webrtc/offer`
- **Request Body (JSON):**
  ```json
  {
    "sdp": "v=0\r\no=- 4529865...",
    "type": "offer",
    "camera_id": "cam_living_room_01"
  }
  ```
- **Response 200 (JSON):** `{"status": "Offer sent via MQTT"}`

---

#### 2. Tráo đổi ICE Candidate
- **Method / Path:** `POST /api/webrtc/ice-candidate`
- **Request Body (JSON):**
  ```json
  {
    "candidate": "candidate:842163045...",
    "sdpMid": "0",
    "sdpMLineIndex": 0,
    "camera_id": "cam_living_room_01"
  }
  ```
- **Response 200 (JSON):** `{"status": "ICE Candidate forwarded"}`

---

## 3. WebSocket Signaling Interface

- **WebSocket URL:** `ws://localhost:8000/ws/signaling/{client_id}?token={JWT_TOKEN}`
  - `{client_id}` cho Web App: `web_parent_01`
  - `{client_id}` cho Edge Camera: `camera_01`

### 📤 1. Request Tín hiệu WebRTC SDP Offer (Parent -> Camera)
Gửi từ Web Browser lên WebSocket server:
```json
{
  "target": "camera_01",
  "type": "offer",
  "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1..."
}
```
*(Server sẽ tự động bọc thêm `"sender": "web_parent_01"` và chuyển tiếp xuống MQTT topic `devices/camera_01/webrtc/offer`)*

### 📥 2. Alert Broadcast Notification (Server -> Web App)
Khi AI Edge phát hiện nguy hiểm, Backend gửi tin nhắn Broadcast tới mọi kết nối WebSocket đang mở:
```json
{
  "type": "ALERT_NEW",
  "data": {
    "id": 102,
    "camera_id": 1,
    "title": "Trẻ đi vào vùng nước sâu",
    "severity": "danger",
    "snapshot_url": "data/snapshots/cam_01_1786675200.jpg",
    "roi_name": "Hồ bơi",
    "created_at": "2026-08-14T04:20:00Z"
  }
  ```

---

## 4. MQTT Topics & Payloads (Edge AI ↔ Backend)

MQTT Broker Port mặc định: `1883`

```
  ┌─────────────────┐        MQTT Pub/Sub        ┌─────────────────┐
  │ Raspberry Pi    │ ─────────────────────────> │ Backend Server  │
  │ (Edge AI Node)  │ <───────────────────────── │ (FastAPI System)│
  └─────────────────┘                            └─────────────────┘
```

### 🔼 Direction A: Edge AI -> Backend Server (Edge Pub -> Server Sub)

#### Topic 1: `devices/{device_id}/alerts`
- **Format:** JSON
- **Mục đích:** Gửi sự kiện AI phát hiện hành vi nguy hiểm của trẻ.
- **Payload Schema:**
  ```json
  {
    "camera_id": "cam_living_room_01",
    "title": "Phát hiện trẻ trèo ban công",
    "severity": "danger",
    "snapshot_url": "cam_living_room_01_1786675200.jpg",
    "roi_name": "Lan can ban công"
  }
  ```

#### Topic 2: `devices/{device_id}/snapshots`
- **Format:** Binary (Raw JPEG Image Bytes)
- **Mục đích:** Gửi ảnh chụp bằng chứng từ Camera khi có sự kiện cảnh báo.
- **Payload Schema:** Raw Binary Data (Image JPEG bytes)
- **Xử lý Backend:** Server tự động lưu byte dữ liệu này thành file ảnh tĩnh tại đường dẫn `data/snapshots/{device_id}_{timestamp}.jpg`.

#### Topic 3: `devices/{device_id}/webrtc/answer`
- **Format:** JSON
- **Mục đích:** Edge Camera gửi kết quả WebRTC Answer SDP phản hồi lời mời xem video stream từ Phụ huynh.
- **Payload Schema:**
  ```json
  {
    "target": "web_parent_01",
    "type": "answer",
    "sdp": "v=0\r\no=- 987654321 2 IN IP4 192.168.1.50..."
  }
  ```

---

### 🔽 Direction B: Backend Server -> Edge AI (Server Pub -> Edge Sub)

#### Topic 4: `devices/{camera_id}/webrtc/offer`
- **Format:** JSON
- **Mục đích:** Backend đẩy yêu cầu SDP Offer kết nối xem camera từ Phụ huynh xuống Raspberry Pi.
- **Payload Schema:**
  ```json
  {
    "sender": "web_parent_01",
    "target": "camera_01",
    "type": "offer",
    "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1..."
  }
  ```

#### Topic 5: `devices/{device_id}/roi/update`
- **Format:** JSON
- **Mục đích:** Backend hạ lệnh cập nhật danh sách tọa độ Vùng cấm (ROI Zones) mới nhất xuống cho Edge AI Engine trên Raspberry Pi nạp lại cấu hình.
- **Payload Schema:**
  ```json
  {
    "camera_id_string": "cam_living_room_01",
    "zones": [
      {
        "name": "Khu vực Hồ bơi",
        "sensitivity": "high",
        "enabled": true,
        "points": [
          {"x": 0.1, "y": 0.1},
          {"x": 0.8, "y": 0.1},
          {"x": 0.8, "y": 0.9},
          {"x": 0.1, "y": 0.9}
        ]
      }
    ]
  }
  ```

---
*Tài liệu được cập nhật tự động đồng bộ với mã nguồn hệ thống.*
