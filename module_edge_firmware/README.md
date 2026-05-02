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
