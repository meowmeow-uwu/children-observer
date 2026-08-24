# Báo cáo tích hợp Fall Detection trên Raspberry Pi 4

**Nhánh thực hiện:** `integration/fall-detection`  
**Nguồn model:** `origin/feat/fall_detection`  
**Ngày cập nhật:** 2026-08-24

## 1. Mục tiêu

Tích hợp mô hình phát hiện té ngã vào Edge runtime đang dùng cho camera RTSP,
đồng thời giữ nguyên luồng nhận diện trẻ/ROI, MQTT, WebRTC và backend hiện có.
Giai đoạn đầu gửi cảnh báo đến MQTT, database và giao diện web; Telegram bị tắt
để tránh thông báo thử nghiệm đến người dùng.

## 2. Kiến trúc sau tích hợp

```text
RTSP camera
  └─ FrameStore (latest frame)
       ├─ ROI ONNX + ByteTrack, 5 FPS
       │    └─ confirmed child tracks
       └─ Fall worker ONNX, 2 FPS, queue size = 1
            ├─ YOLO11m-Pose
            ├─ ghép pose với child track bằng IoU
            └─ state theo track: normal → suspected → confirmed → recovered
                 ├─ overlay WebRTC/DataChannel
                 ├─ metrics JSONL
                 └─ MQTT alert + snapshot khi confirmed
```

Fall worker chỉ xử lý frame mới nhất. Khi Raspberry Pi không xử lý kịp, frame cũ
được bỏ thay vì tạo hàng đợi; vì vậy alert không bị trễ so với cảnh thực tế. ROI
tiếp tục chạy ngay cả khi model fall lỗi. Worker fall chuyển trạng thái `degraded`
và thử nạp lại sau 30 giây.

## 3. Model artifact

Chỉ lấy model `weights/fall_detection/best.pt` từ nhánh `feat/fall_detection`.
Không merge Docker Compose, log, video annotated, training outputs hoặc code
violence detection từ nhánh đó.

| Artifact | Mục đích | SHA-256 |
|---|---|---|
| `best.pt` | Weight PyTorch nguồn, YOLO11m-Pose | `6E417E27CC6B23EF1615810E870919C2B30ADEACFA01DDB5EE65382624069594` |
| `best-640.onnx` | Bản ONNX tham chiếu | `A0EED31FD572C522F1E3699276E5075B97828E57A794CD12756C345E234C0D85` |
| `best-416.onnx` | Bản ONNX tối ưu để benchmark trên Pi 4 | `EFD717A138A9D61E54039FC92C0E712DF95E2030ED9A231433534A531F676CEA` |

Weights được Git ignore và phải chuyển riêng sang Pi. Có thể tái tạo bản ONNX:

```bash
uv run python scripts/export_fall_model.py
```

## 4. Thay đổi đã thực hiện

- Thêm `FallPoseEstimator`, `FallStateEngine`, `FallWorker` tại
  `module_edge_firmware/demo_stream/fall.py`.
- Cập nhật `demo_stream/pipeline.py` để chạy ROI và fall song song qua hai worker
  bounded, publish trạng thái fall và đưa dữ liệu fall vào track message.
- Overlay frontend đổi màu đỏ khi confirmed, cam khi suspected; client cũ vẫn tương
  thích vì trường `fall` là tùy chọn.
- Mở rộng MQTT alert với trường `notes`, dùng để lưu `track_id`, confidence và
  loại sự kiện.
- Thêm `TELEGRAM_ALERTS_ENABLED`; khi false, backend vẫn lưu/broadcast alert nhưng
  không gọi Telegram.
- Thêm `StateDirectory=children-observer` cho systemd để service có nơi ghi metrics
  tại `/var/lib/children-observer/fall-metrics.jsonl`.
- Cập nhật `weights/registry.json` thành JSON hợp lệ và tham chiếu model ONNX 416.

## 5. Cấu hình Raspberry Pi

Thêm các biến sau vào `/etc/children-observer/edge.env`:

```text
EDGE_FALL_ENABLED=true
EDGE_FALL_MODEL_PATH=/opt/children-observer/weights/fall_detection/best-416.onnx
EDGE_FALL_FPS=2
EDGE_FALL_CONF_THRESHOLD=0.50
EDGE_FALL_STILL_SECONDS=2.0
EDGE_FALL_COOLDOWN_SECONDS=30
EDGE_FALL_VELOCITY_THRESHOLD=0.15
EDGE_FALL_STILL_VELOCITY_THRESHOLD=0.04
EDGE_FALL_INPUT_SIZE=416
EDGE_FALL_ONNX_INTRA_THREADS=2
EDGE_FALL_PUBLISH_ALERTS=true
EDGE_FALL_METRICS_PATH=/var/lib/children-observer/fall-metrics.jsonl
```

Đặt `TELEGRAM_ALERTS_ENABLED=false` trong môi trường backend/Docker Compose khi
nghiệm thu. Sau khi copy model, cần kiểm checksum ở Pi trước khi restart service.

## 6. Kiểm thử đã hoàn thành

| Hạng mục | Kết quả |
|---|---|
| Unit tests fall state, IoU, TTL, cooldown, recovery | Pass |
| Tracker tests | Pass |
| Backend alert tests | Pass |
| Tổng kiểm thử | 13 passed |
| TypeScript + Vite production build | Pass |
| ONNX load CPU với 2 threads | Pass |

Có cảnh báo hiện hữu từ FastAPI/Pydantic và JWT key trong test; không do thay đổi
Fall Detection. Frontend có cảnh báo bundle lớn hơn 500 kB nhưng build thành công.

## 7. Đánh giá độ chính xác và hiệu năng

Chưa có số liệu Raspberry Pi hoặc event precision/recall chính thức. Cần thực hiện
trên video có gán nhãn thật, không dùng video ROI demo làm ground truth.

Các script hỗ trợ:

```bash
# So sánh số pose giữa PyTorch và ONNX trên cùng video.
uv run python scripts/compare_fall_exports.py --video <fall-video.mp4>

# Replay cùng đường ROI → ByteTrack → pose → fall và tạo báo cáo JSON.
uv run python scripts/evaluate_fall.py \
  --video <fall-video.mp4> \
  --ground-truth scripts/fall_ground_truth.example.json
```

Kết quả cần theo dõi: event precision, recall, F1, false alerts/hour, alert latency,
latency p50/p95, fall FPS, ROI FPS, CPU/RAM, nhiệt độ và `vcgencmd get_throttled`.

Ngưỡng nghiệm thu ban đầu:

- Fall recall ≥ 90%, precision ≥ 80%.
- False alert ≤ 1 lần/giờ.
- Fall ≥ 2 FPS, ROI ≥ 4 FPS, p95 fall inference ≤ 450 ms.
- Nhiệt độ dưới 80°C, không throttling và không OOM trong soak test 2 giờ.

## 8. Rủi ro và bước tiếp theo

Khi thử trên `module_edge_firmware/test_video.mp4`, cả weight `.pt` và ONNX 416
không trả pose ở frame trẻ đứng. Đây có thể là do model được fine-tune cho tư thế
ngã và video hiện tại chỉ dùng kiểm ROI; chưa phải bằng chứng model hỏng. Cần chạy
trên clip té ngã thật. Nếu model không trả pose trên clip fall đã gán nhãn, dừng
triển khai và yêu cầu lại model/artifact từ nhóm AI.

Các bước tiếp theo:

1. Chuyển `best-416.onnx` sang Pi và xác minh SHA-256.
2. Chạy foreground với RTSP + MQTT, kiểm tra overlay/snapshot/UI.
3. Chạy replay video gán nhãn, lưu báo cáo JSON và điều chỉnh threshold nếu cần.
4. Soak test 2 giờ trên camera thật với tình huống an toàn.
5. Chỉ bật Telegram sau khi đạt ngưỡng nghiệm thu.
