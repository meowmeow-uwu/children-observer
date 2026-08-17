# Module Edge Firmware - Xử lý tại biên

Module này là trái tim của hệ thống chạy trực tiếp trên Camera hoặc thiết bị Edge (Jetson, Rockchip), thực hiện phân tích thời gian thực và đưa ra cảnh báo.

## 🔄 Quy trình xử lý (Pipeline)
1. **Ingestion**: Thu nhận luồng RTSP và tiền xử lý khung hình.
2. **Multi-Task AI**: Chạy song song Detection, Pose và Action Recognition.
3. **Risk Analysis**: Đánh giá rủi ro dựa trên vùng ROI và hành vi.
4. **Buffering**: Lưu trữ 10-15 giây video vào bộ đệm vòng.
5. **Alerting**: Gửi cảnh báo (Snapshot + Clip) kèm mã hóa E2EE.

## 📂 Thành phần chính
- `ingestion/`: Quản lý kết nối RTSP và tự động kết nối lại.
- `inference/`: Bộ chạy AI đa nhiệm tối ưu hóa độ trễ < 2ms.
- `analysis/`: Logic kiểm tra xâm nhập vùng (ROI) và phát hiện té ngã.
- `buffer/`: Quản lý Circular Buffer để trích xuất video sự cố.
- `alert/`: Quản lý thông báo và tạo ảnh Snapshot/Crop.

## 🛠 Cách chạy Edge Pipeline

Chạy toàn bộ hệ thống giám sát:
```bash
python main.py --mode edge
```

Hoặc sử dụng code:
```python
from module_edge_firmware.pipeline import EdgePipeline

pipeline = EdgePipeline()
pipeline.start()
```

## ⚙️ Biến môi trường quan trọng (.env)
- `RTSP_URL`: Địa chỉ luồng camera.
- `ROI_CONFIG_PATH`: Đường dẫn file cấu hình vùng an toàn.
- `ALERT_COOLDOWN_SECONDS`: Thời gian nghỉ giữa 2 cảnh báo để tránh spam.
- `ALERT_BUFFER_SECONDS`: Độ dài video lưu trữ trong bộ đệm.
- `MOBILE_GATEWAY_HOST` / `MOBILE_GATEWAY_PORT`: TCP gateway để mobile gửi ROI, nhận alert và gửi feedback.

## 🚀 Chạy trên phần cứng (MQTT + RTSP)

Entrypoint production là pipeline `demo_stream` (tên cũ, nhưng hiện hỗ trợ cả
RTSP). Nó nhận ROI/WebRTC offer qua MQTT và gửi SDP answer, alert JSON và JPEG
binary lại broker.

```bash
EDGE_CAMERA_ID=camera_living_room_01 \
EDGE_RTSP_URL='rtsp://user:password@camera/stream1' \
MQTT_BROKER_HOST=school-server.local \
MQTT_BROKER_PORT=1883 \
EDGE_MQTT_ENABLED=true \
python -m module_edge_firmware.demo_stream
```

Topics theo `docs/tasks/task_edge_firmware_integration.md`:

- Subscribe: `devices/{device_id}/roi/update`, `devices/{device_id}/webrtc/offer`
- Publish: `devices/{device_id}/webrtc/answer`, `devices/{device_id}/alerts`, `devices/{device_id}/snapshots`

Đặt `EDGE_MQTT_ENABLED=false` và `EDGE_REST_SYNC_ENABLED=true` chỉ khi cần chạy
luồng REST/WebSocket demo cũ. Docker Compose đã kèm Mosquitto cho môi trường local.

## 📡 Mobile Gateway Protocol

Gateway dùng newline-delimited JSON qua TCP. Mặc định lắng nghe tại `0.0.0.0:8765`.

Mobile gửi:
```json
{"type":"ping"}
{"type":"status"}
{"type":"get_alerts","limit":20}
{"type":"update_roi","zones":[{"zone_id":"kitchen","label":"danger","vertices":[[0.1,0.1],[0.4,0.1],[0.4,0.4],[0.1,0.4]]}]}
{"type":"feedback","alert_id":"alert_000001","is_correct":false,"correct_label":"normal","notes":"false alarm"}
```

Edge broadcast alert tới các client đang kết nối:
```json
{"type":"alert","ok":true,"payload":{"alert_id":"alert_000001","risk_level":"high","reasons":["..."]}}
```
