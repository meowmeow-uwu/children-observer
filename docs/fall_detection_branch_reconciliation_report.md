# Báo cáo đối chiếu nhánh `feat/fall_detection`

**Nhánh tích hợp:** `integration/fall-detection`  
**Nhánh nguồn được đối chiếu:** `origin/feat/fall_detection`  
**Mục tiêu:** tích hợp Fall Detection vào runtime Edge hiện hành mà không đưa các
thay đổi không liên quan hoặc làm lệch kiến trúc triển khai Raspberry Pi.

## 1. Kết luận

Không merge hoặc cherry-pick nguyên nhánh `feat/fall_detection`.

Nhánh nguồn có khoảng 62 file thay đổi, bao gồm model weights, video annotated,
training output, logs, mã training, một implementation violence detection độc lập
và thay đổi Docker Compose. Các phần này không cùng phạm vi với runtime hiện hành
`module_edge_firmware.demo_stream`, vì vậy merge nguyên nhánh có rủi ro conflict,
phình repository, cấu hình mạng không an toàn và đưa code không được service Pi gọi.

Nhánh tích hợp chỉ lấy artifact model cần thiết và tái sử dụng ý tưởng pose +
fall-state; implementation runtime được viết mới để phù hợp pipeline hiện hành.

## 2. Những phần đã lấy từ nhánh nguồn

| Thành phần nguồn | Cách sử dụng trong nhánh tích hợp | Lý do |
|---|---|---|
| `weights/fall_detection/best.pt` | Lấy trực tiếp làm weight nguồn để export ONNX | Đây là model fine-tuned cần benchmark trên Pi. |
| Thông tin kiến trúc YOLO11m-Pose | Ghi nhận trong tài liệu/runtime | Xác định đúng kiểu output: 17 COCO keypoints. |
| Ý tưởng Fall Detection rule-based | Áp dụng lại nguyên tắc: tư thế nằm + chuyển động + thời gian bất động | Phù hợp bài toán phát hiện event, không phải chỉ phát hiện pose từng frame. |
| Các ngưỡng ban đầu của branch | Dùng làm baseline để cấu hình `still_seconds`, lying ratio và velocity | Là điểm bắt đầu cho video gán nhãn; không coi là threshold đã được xác nhận trên Pi. |
| Tài liệu inference ONNX của phần violence | Chỉ dùng để xác nhận violence là model video độc lập | Không được đưa vào scope Fall Detection hiện tại. |

Artifact nguồn đã lấy được xác minh bằng SHA-256:

```text
weights/fall_detection/best.pt
6E417E27CC6B23EF1615810E870919C2B30ADEACFA01DDB5EE65382624069594
```

Từ weight này đã export hai artifact runtime, cả hai bị Git ignore và phải copy
riêng sang Pi:

```text
weights/fall_detection/best-640.onnx  # bản đối chiếu độ chính xác
weights/fall_detection/best-416.onnx  # bản benchmark Raspberry Pi 4
```

## 3. Những phần được triển khai mới trong nhánh tích hợp

Các phần dưới đây **không được copy nguyên văn** từ `feat/fall_detection`; chúng
được thiết kế để khớp runtime đang chạy qua systemd: `python -m
module_edge_firmware.demo_stream`.

### 3.1 Edge inference

- Thêm `module_edge_firmware/demo_stream/fall.py`.
- `FallPoseEstimator` chạy ONNX Runtime trực tiếp, CPU-only, với 2 intra-op
  threads; không cần mở thêm RTSP/camera và không phụ thuộc pipeline cũ.
- `FallWorker` dùng queue size 1. Nếu pose inference chậm, worker xử lý frame mới
  nhất và bỏ frame cũ để tránh alert trễ.
- ROI detector vẫn chạy ở 5 FPS; fall worker chạy mặc định 2 FPS.
- Khi model lỗi/corrupt/mất file, fall worker chuyển `degraded`, retry sau 30 giây;
  ROI/WebRTC/MQTT không bị dừng.

### 3.2 Gắn fall với trẻ đang theo dõi

- Pose được ghép với `confirmed child track` bằng IoU của bounding box.
- State được lưu riêng theo `track_id`, không dùng “person đầu tiên của frame”.
- Velocity dùng keypoint đã chuẩn hóa 0–1 và `source_time_ms`, thay vì pixels/frame;
  vì vậy không phụ thuộc trực tiếp độ phân giải RTSP hoặc FPS camera.
- State machine: `normal → suspected → confirmed → recovered`.
- Chỉ tạo một alert khi chuyển sang `confirmed`; cooldown mặc định 30 giây cho
  từng track.

### 3.3 Alert, metrics và frontend

- Track wire message nhận thêm trường optional `fall`; frontend cũ bỏ qua được nếu
  trường này chưa có.
- `DetectionOverlay` hiển thị cam cho `suspected`, đỏ và nhãn Fall cho `confirmed`.
- MQTT alert truyền `notes` gồm loại event, track ID và confidence; snapshot là frame
  xác nhận event.
- Backend thêm `TELEGRAM_ALERTS_ENABLED`; `false` vẫn lưu DB/broadcast UI nhưng
  không gọi Telegram.
- systemd dùng `StateDirectory=children-observer`; metrics JSONL ghi tại
  `/var/lib/children-observer/fall-metrics.jsonl`.

### 3.4 Tooling và kiểm thử mới

| File | Mục đích |
|---|---|
| `scripts/export_fall_model.py` | Export tái lập được `.pt` → ONNX 640/416, in SHA-256. |
| `scripts/compare_fall_exports.py` | So sánh số pose từ PyTorch và ONNX trên cùng video. |
| `scripts/evaluate_fall.py` | Replay ROI → tracker → pose → fall trên video gán nhãn, xuất precision/recall/F1/latency. |
| `scripts/fall_ground_truth.example.json` | Mẫu gán nhãn event fall, lying non-fall, sit down, normal. |
| `tests/test_edge/test_fall.py` | Test IoU, state machine, TTL, cooldown và recovery. |

## 4. Những phần chủ động không lấy

| Phần trên `feat/fall_detection` | Quyết định | Lý do |
|---|---|---|
| Toàn bộ commit/merge history của branch | Không merge/cherry-pick | Branch lệch xa `feat/product`, nguy cơ conflict lớn. |
| `docker-compose.yml` | Không lấy | Có MQTT host được hard-code; không phù hợp LAN hiện tại và không an toàn. |
| `.env.example` thay đổi `POSE_MODEL_PATH` | Không lấy nguyên bản | Edge runtime dùng `EDGE_FALL_*`; không dùng `configs.settings` để boot `demo_stream`. |
| `logs/*.log` | Không lấy | Là runtime artifacts, không thuộc source code. |
| `fall_annotated.mp4`, `falls_annotated.mp4`, `nofall_annotated.mp4` | Không commit vào nhánh tích hợp | Video lớn; nếu dùng để benchmark cần quản lý ngoài Git hoặc storage riêng. |
| `runs/`, train results, `last.pt`, model bản sao | Không lấy | Tránh nhiều bản weight/training artifact trong repo; chỉ giữ artifact đã chọn ngoài Git. |
| `PROJECT_OVERVIEW.md` và báo cáo generated lớn | Không lấy | Không trực tiếp phục vụ Edge runtime. |
| Dataset loader, augmentation và training pipeline | Không lấy vào integration runtime | Thuộc ML training workflow, không cần để chạy inference Pi. Có thể tích hợp sau vào nhánh training riêng. |
| `test_fall_detection_video.py` | Không lấy nguyên bản | Mở video/camera độc lập, lấy người đầu tiên, không dùng ROI/ByteTrack/MQTT hiện hành. |
| `test_fall_logic.py` của branch | Không copy nguyên bản | Dùng synthetic pose theo pixel và `time.sleep`; thay bằng unit test deterministic theo source time chuẩn hóa. |
| `MultiTaskRunner`/pipeline cũ | Không chuyển service sang đó | systemd hiện chạy `demo_stream`; migration toàn pipeline nằm ngoài phạm vi feature này. |
| `module_ai_core/violence_detection/*` | Không lấy | Là X3D-M RGB video classifier riêng; violence detection chưa thuộc scope. |
| Weight violence `model.pth`, ONNX, INT8 | Không lấy | Tăng dung lượng repo và không được runtime fall dùng. |

## 5. Khác biệt quan trọng so với implementation cũ

### Runtime entrypoint

Nhánh nguồn tập trung vào `MultiTaskRunner` và các script chạy độc lập. Service
thật trên Pi lại gọi `module_edge_firmware.demo_stream`. Việc tích hợp trực tiếp
vào `demo_stream` là bắt buộc để feature có hiệu lực khi systemd khởi động.

### Identity của người

Code nguồn thường dùng `poses.get_person_keypoints(0)`, tức người đầu tiên trong
frame. Cách này sai khi camera có người lớn và trẻ cùng xuất hiện. Implementation
mới chỉ xét pose ghép được với confirmed child track.

### Timing và ngưỡng

Code nguồn dùng velocity pixels/frame và `time.time()`. Implementation mới dùng
tọa độ normalized và clock `source_time_ms` của pipeline. Kết quả ổn định hơn khi
đổi độ phân giải camera hoặc thay FPS sampling.

### Hiệu năng Pi

Code nguồn benchmark 89.24 FPS trên GPU CUDA, không đại diện cho Pi 4 CPU-only.
Implementation mới tạo ONNX static 416/640, giới hạn threads và metrics thực tế
để đo p50/p95, effective FPS, CPU/RAM/nhiệt độ/throttling trên Pi.

## 6. Trạng thái xác minh

Đã xác minh trên môi trường development:

- `best-416.onnx` nạp thành công bằng ONNX Runtime CPU với 2 threads.
- 13 tests fall/tracker/backend pass.
- Frontend TypeScript/Vite production build pass.
- Registry JSON hợp lệ.

Chưa được xác minh trên Raspberry Pi thật. Ngoài ra, `best.pt` và ONNX 416 không
trả pose trong frame trẻ đứng của `module_edge_firmware/test_video.mp4`. Video này
là ROI demo chứ không phải fall test; cần benchmark trên clip té ngã đã gán nhãn.
Nếu không có pose ở clip fall thật, cần dừng rollout và yêu cầu nhóm AI cung cấp
model/artifact phù hợp.

## 7. Hạng mục còn lại để nghiệm thu

1. Copy `best-416.onnx` sang Pi, kiểm SHA-256 và restart foreground service.
2. Đặt `TELEGRAM_ALERTS_ENABLED=false` trên backend trước khi bật MQTT trial.
3. Tạo manifest gán nhãn từ `scripts/fall_ground_truth.example.json` cho video thật.
4. Chạy `scripts/compare_fall_exports.py` và `scripts/evaluate_fall.py`.
5. Soak test RTSP tối thiểu hai giờ; kiểm tra metrics JSONL, `vcgencmd measure_temp`
   và `vcgencmd get_throttled`.
6. Chỉ bật Telegram khi đạt recall ≥ 90%, precision ≥ 80%, fall ≥ 2 FPS và không
   throttling/OOM.
