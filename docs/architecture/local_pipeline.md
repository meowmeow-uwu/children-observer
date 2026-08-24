# Luồng local: Camera, Raspberry Pi Edge, Backend, MQTT và Frontend

Tài liệu này mô tả đúng cấu hình demo/local đã chạy: **laptop** chạy PostgreSQL, MQTT Broker, FastAPI và Frontend bằng Docker Compose; **Raspberry Pi 4** chạy Edge AI; **camera Dahua** cung cấp RTSP. Ba thiết bị cần ở cùng mạng LAN để xem video WebRTC trực tiếp ổn định.

## 1. Vai trò của từng thành phần

| Thành phần | Chạy ở đâu | Nhiệm vụ chính | Không làm gì |
|---|---|---|---|
| IP Camera | Camera Dahua | Phát luồng RTSP video | Không chạy AI, không biết ROI |
| Raspberry Pi / Edge | Raspberry Pi 4 | Đọc RTSP, chạy ONNX + ByteTrack + ROI, gửi trạng thái/cảnh báo/snapshot, trả lời WebRTC | Không lưu DB, không phục vụ giao diện |
| MQTT Broker | Laptop, container `guardian_mqtt` | Kênh pub/sub trung gian tin nhắn giữa Edge và Backend | Không xử lý AI, không lưu alert vào PostgreSQL |
| Backend FastAPI | Laptop, container `guardian_fastapi` | API cho Frontend, lưu PostgreSQL, đồng bộ ROI, nhận alert/snapshot/status MQTT, cấp luồng signaling | Không đọc RTSP, không chạy ONNX |
| PostgreSQL | Laptop, container `guardian_postgres` | Lưu camera, ROI, alert và dữ liệu nghiệp vụ | Không nhận MQTT trực tiếp |
| Frontend | Browser, tải từ containezr `guardian_frontend` | Cho người dùng đăng nhập, vẽ ROI, xem cảnh báo và yêu cầu xem camera | Không kết nối RTSP đến camera, không chạy AI |

## 2. Sơ đồ kiến trúc và các kiểu giao tiếp

```mermaid
flowchart LR
    CAM["IP Camera Dahua\nRTSP substream"]

    subgraph PI["Raspberry Pi 4 – Edge AI"]
      RTSP["RTSP source\nOpenCV/FFmpeg TCP"]
      AI["ONNX detector + ByteTrack\nROI engine"]
      EDGE["MQTT client + WebRTC peer"]
      RTSP --> AI --> EDGE
    end

    subgraph LAPTOP["Laptop local – Docker Compose"]
      MQTT[("Mosquitto MQTT\n:1883")]
      API["FastAPI backend\npublic :8007 → container :8000"]
      DB[("PostgreSQL\n:5432")]
      API <--> DB
      API <--> MQTT
    end

    WEB["Browser / Frontend\nhttp://localhost:5173"]

    CAM -- "RTSP/TCP video" --> RTSP
    EDGE <--> |"MQTT TCP :1883\nROI, status, offer/answer, alert, snapshot"| MQTT
    WEB <-->|"HTTPS/HTTP API + WebSocket signaling"| API
    WEB <-->|"WebRTC media\nP2P trên LAN"| EDGE
```

Điểm cần nhớ: video AI đi theo đường **Camera → Pi**, còn video xem trên giao diện đi theo đường **Pi → Browser bằng WebRTC**. MQTT/Backend chỉ điều phối (ROI, signaling, alert, snapshot, status); chúng **không chuyển tiếp từng frame video** trong luồng local này.

## 3. Luồng khởi động hệ thống

```mermaid
sequenceDiagram
    participant DB as PostgreSQL
    participant BE as FastAPI Backend
    participant MQ as MQTT Broker
    participant Pi as Raspberry Pi Edge
    participant Cam as IP Camera
    participant UI as Frontend/Browser

    BE->>DB: Đọc camera, ROI, người dùng
    BE->>MQ: Kết nối và subscribe topic Edge
    Pi->>MQ: Kết nối MQTT
    Pi->>MQ: Subscribe retained ROI
    MQ-->>Pi: ROI hiện tại của camera
    Pi->>Cam: Mở RTSP substream qua TCP
    Cam-->>Pi: Frame video liên tục
    Pi->>MQ: Publish retained status online
    MQ-->>BE: Camera status
    BE->>DB: Cập nhật trạng thái camera
    UI->>BE: Lấy cameras/ROI/status qua API
    BE-->>UI: Dữ liệu hiển thị
```

Nếu Pi được khởi động sau khi ROI đã được vẽ, retained message giúp Pi nhận ROI ngay, không phải chờ người dùng lưu lại ROI lần nữa.

## 4. Luồng thiết lập ROI

```mermaid
sequenceDiagram
    participant UI as Frontend/Browser
    participant BE as FastAPI Backend
    participant DB as PostgreSQL
    participant MQ as MQTT Broker
    participant Pi as Raspberry Pi Edge

    UI->>BE: PUT/POST ROI (tọa độ chuẩn hóa 0..1, rules)
    BE->>DB: Lưu ROI và rules
    BE->>MQ: Publish retained devices/{camera_id}/roi/update
    MQ-->>Pi: ROI update
    Pi->>Pi: Cập nhật ROI engine trong RAM
    Pi-->>UI: Overlay ROI xuất hiện trong video WebRTC kế tiếp
```

ROI được lưu hai nơi với hai mục đích khác nhau:

- **PostgreSQL** là nguồn dữ liệu bền vững, phục vụ API/giao diện.
- **RAM trên Pi** là bản đang được AI dùng ngay cho từng frame.
- MQTT retained là cầu nối để Pi nhận lại cấu hình sau restart hoặc reconnect.

## 5. Luồng AI, cảnh báo và snapshot

```mermaid
sequenceDiagram
    participant Cam as Camera
    participant Pi as Raspberry Pi Edge
    participant MQ as MQTT Broker
    participant BE as FastAPI Backend
    participant DB as PostgreSQL
    participant UI as Frontend/Browser

    loop Theo EDGE_DETECTION_FPS
      Cam-->>Pi: RTSP frame
      Pi->>Pi: ONNX phát hiện object
      Pi->>Pi: ByteTrack ổn định track
      Pi->>Pi: Kiểm tra track/rules với ROI
    end
    Pi->>Pi: Vi phạm được xác nhận và qua cooldown
    Pi->>MQ: Publish JSON alert
    Pi->>MQ: Publish JPEG snapshot
    MQ-->>BE: Alert + snapshot
    BE->>DB: Tạo event_id, lưu alert/snapshot
    UI->>BE: Lấy lịch sử hoặc nhận cập nhật UI
    BE-->>UI: Hiển thị cảnh báo và ảnh
```

AI chỉ tạo alert khi object/track thỏa rules của ROI. `EDGE_ALERT_COOLDOWN_SECONDS` chống việc cùng một tình huống sinh quá nhiều alert liên tiếp.

## 6. Luồng xem video trực tiếp (WebRTC)

```mermaid
sequenceDiagram
    participant UI as Frontend/Browser
    participant BE as FastAPI Backend
    participant MQ as MQTT Broker
    participant Pi as Raspberry Pi Edge

    UI->>BE: Yêu cầu mở camera / tạo SDP offer
    BE->>MQ: Publish devices/{camera_id}/webrtc/offer
    MQ-->>Pi: SDP offer
    Pi->>Pi: Tạo WebRTC PeerConnection + video track
    Pi->>MQ: Publish devices/{camera_id}/webrtc/answer
    MQ-->>BE: SDP answer
    BE-->>UI: Trả SDP answer
    UI<<->>Pi: ICE + WebRTC media trực tiếp trên LAN
```

MQTT chỉ mang SDP offer/answer rất nhỏ. Video không đi qua MQTT và không đi qua FastAPI. Vì vậy MQTT có thể kết nối bình thường nhưng video vẫn không xem được nếu WebRTC/ICE/Pi mạng lỗi.

## 7. MQTT topic hiện dùng

Mọi topic phụ thuộc vào `EDGE_CAMERA_ID`, hiện là `camera_living_room_01`.

| Topic | Hướng | Dữ liệu | Retained |
|---|---|---|---|
| `devices/{camera_id}/roi/update` | Backend → Pi | Danh sách ROI và rules | Có |
| `devices/{camera_id}/webrtc/offer` | Backend → Pi | SDP offer từ browser | Không |
| `devices/{camera_id}/webrtc/answer` | Pi → Backend | SDP answer từ Pi | Không |
| `devices/{camera_id}/alerts` | Pi → Backend | Metadata cảnh báo | Không |
| `devices/{camera_id}/snapshots` | Pi → Backend | JPEG snapshot dạng binary | Không |
| `devices/{camera_id}/status` | Pi → Backend | `online`, `state`, `reason`, timestamp | Có |

## 8. Khi camera mất kết nối

```mermaid
flowchart TD
    A["Camera ngắt / RTSP không đọc được"] --> B["Pi phát hiện RTSP lỗi"]
    B --> C["Pi publish retained status: offline"]
    C --> D["Backend nhận MQTT status"]
    D --> E["Backend cập nhật trạng thái camera"]
    E --> F["Frontend hiển thị Offline / Mất kết nối"]
    B --> G["Pi tự reconnect RTSP"]
    G --> H{"Camera có lại?"}
    H -- "Có" --> I["Pi publish retained status: online"]
    I --> D
    H -- "Chưa" --> G
```

Trạng thái **online/offline** phản ánh khả năng Pi đọc RTSP camera, không chỉ phản ánh việc browser có đang mở video hay không.

## 9. Cổng và địa chỉ local cần biết

| Dịch vụ | Địa chỉ từ laptop/browser | Địa chỉ từ Pi | Mục đích |
|---|---|---|---|
| Frontend | `http://localhost:5173` | Không cần Pi truy cập | Giao diện |
| Backend API | `http://localhost:8007` | Chỉ cần khi bật REST fallback | API và signaling |
| MQTT Broker | `localhost:1883` | `<IP_LAN_LAPTOP>:1883` | Điều phối Edge/Backend |
| PostgreSQL | `localhost:5432` | Không được Pi truy cập trực tiếp | Dữ liệu backend |
| RTSP Camera | Không cần laptop truy cập | `rtsp://<camera>/...` | Video đầu vào AI |

`MQTT_BROKER_HOST` trong `/etc/children-observer/edge.env` phải là IP LAN của **laptop đang chạy Docker MQTT**, không phải `localhost`. Trên Pi, `localhost` luôn trỏ về chính Pi.

## 10. Checklist xác minh quan hệ giữa các thành phần

1. Camera → Pi: Pi log có `RTSP stream connected`.
2. Pi → MQTT: Pi log có `MQTT connected`.
3. MQTT → Pi: thay đổi ROI trên UI, Pi log có `Applied ... ROI zones from MQTT`.
4. Pi → Backend: broker nhận `devices/camera_living_room_01/status`; UI đổi online/offline đúng.
5. Pi → Backend → DB: trigger alert, alert và snapshot xuất hiện trong UI/DB.
6. Browser ↔ Pi: mở camera, WebRTC ICE connected và video có thời gian thực.

Nếu một bước lỗi, hãy khoanh vùng theo mũi tên trong sơ đồ thay vì khởi động lại toàn bộ hệ thống. Ví dụ: AI vẫn chạy nhưng UI không đổi trạng thái thường là lỗi Pi → MQTT → Backend; UI có status online nhưng không có hình thường là lỗi signaling/ICE WebRTC, không phải RTSP.
