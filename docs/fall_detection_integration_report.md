# Báo cáo tích hợp Fall Detection vào hệ thống hiện tại

**Nhánh tích hợp:** `integration/fall-detection`

**Nguồn model:** `feat/fall_detection`

**Cập nhật:** 2026-08-26
**Trạng thái:** Tích hợp runtime hoàn thành; chưa đạt điều kiện nghiệm thu độ chính xác/hiệu năng trên Raspberry Pi.

## 1. Mục tiêu và phạm vi

Tích hợp pose-based Fall Detection vào edge pipeline hiện có mà không làm gián đoạn các chức năng:

- Nhận frame RTSP hoặc video demo duy nhất.
- ROI detection, ByteTrack, MQTT, WebRTC DataChannel và backend alert.
- Lưu alert/snapshot trên backend và hiển thị trạng thái trên frontend.

Phạm vi này chỉ bao gồm Fall Detection. Violence Detection không được merge hoặc chạy cùng đợt thử nghiệm. Telegram bị tắt trong giai đoạn đánh giá nhưng alert vẫn được MQTT, backend và UI xử lý.

## 2. Artifact model và provenance

Model nguồn là `weights/fall_detection/best.pt` từ nhánh Fall Detection.

| Artifact | Vai trò | SHA-256 |
|---|---|---|
| `best.pt` | Checkpoint PyTorch nguồn, YOLO11m-Pose | `6E417E27CC6B23EF1615810E870919C2B30ADEACFA01DDB5EE65382624069594` |
| `best-640.onnx` | Bản ONNX tham chiếu chất lượng | `A0EED31FD572C522F1E3699276E5075B97828E57A794CD12756C345E234C0D85` |
| `best-416.onnx` | Bản ONNX tối ưu để benchmark Raspberry Pi 4 | `EFD717A138A9D61E54039FC92C0E712DF95E2030ED9A231433534A531F676CEA` |

Hai file ONNX được export static, batch 1, FP32, opset 17 từ `best.pt` bằng `scripts/export_fall_model.py`. Weights bị `.gitignore`; model phải được copy riêng sang Pi và kiểm SHA-256 trước khi chạy.

> Lưu ý so sánh: `module_ai_core/fall_detection/predict_video.py` với tham số `--weights weights/fall_detection/best.pt` dùng đúng checkpoint nguồn. Script `test_fall_detection_video.py` cũ của nhánh Fall lại nạp `yolo-pose-best.pt`; không dùng output của hai script này để so sánh lẫn nhau nếu chưa xác minh checkpoint.

## 3. Kiến trúc runtime sau tích hợp

```text
RTSP / Demo video
  └─ FrameStore: chỉ giữ latest frame
       ├─ ROI ONNX + ByteTrack (mặc định 5 FPS trên Pi)
       │    └─ confirmed child tracks
       └─ FallWorker (mặc định 2 FPS, queue maxsize=1)
            ├─ YOLO11m-Pose ONNX Runtime CPU
            ├─ ghép pose với child track theo IoU
            ├─ FallStateEngine theo từng track_id
            ├─ metrics JSONL
            └─ FallAlert → MQTT/snapshot hoặc REST fallback
```

Fall worker không mở camera/RTSP riêng. Nếu inference chậm, frame cũ bị bỏ thay vì tạo backlog; ROI và WebRTC tiếp tục chạy. Nếu load/inference Fall lỗi, worker chuyển `degraded`, retry sau 30 giây và không làm ROI dừng.

## 4. ONNX inference và các sửa đổi tương đương PT

`module_edge_firmware/demo_stream/fall.py` cung cấp `FallPoseEstimator` với ONNX Runtime CPU và 2 threads mặc định.

Các điểm đã được điều chỉnh để giảm khác biệt với đường PyTorch/Ultralytics:

- Frame OpenCV được đổi từ BGR sang RGB trước resize/letterbox.
- NMS nhận bounding box dạng `xywh`, đúng hợp đồng `cv2.dnn.NMSBoxes`; kết quả cuối vẫn dùng `xyxy`.
- Box và 17 keypoint được unletterbox, chuẩn hóa về tọa độ `0–1` theo frame gốc.
- `EDGE_FALL_INPUT_SIZE` phải khớp artifact: `416` cho `best-416.onnx`, `640` cho `best-640.onnx`.

Khác biệt còn lại với video `.pt` không phải chỉ do ONNX:

- `predict_video.py` chạy inference cho từng frame video, với `--conf 0.35` trong thử nghiệm đã thực hiện.
- Runtime Pi mặc định chạy pose 2 FPS và confidence 0.50 để tránh quá tải; skeleton vì vậy cập nhật mỗi 0.5 giây, không mượt bằng video PT xử lý từng frame.
- Preview ONNX dùng renderer Ultralytics `Annotator.kpts()` để có palette keypoint/limb giống `Results.plot()` của PT. Màu box state vẫn do integration quyết định.

## 5. Ghép track và state machine

Pose không tự động chọn người đầu tiên trong frame. Mỗi pose phải được ghép với `child` track confirmed bằng IoU. State được lưu riêng theo `track_id`, tự xóa khi hết TTL và reset khi video/viewer session đổi để không mang cooldown/track state cũ sang luồng mới.

```text
normal
  └─ pose trước đó + chuyển động rơi đủ lớn + tư thế nằm
       → suspected + gửi alert ngay

suspected
  ├─ tiếp tục nằm/bất động ≥ 1 giây → confirmed (trạng thái theo dõi)
  └─ không còn nằm → normal

confirmed
  └─ không còn nằm → recovered → normal
```

Frame đầu tiên đã thấy người nằm không được alert. Alert `suspected` chỉ phát khi có ít nhất hai pose liên tiếp chứng minh chuyển động chuyển sang tư thế nằm. Cooldown là 30 giây theo camera/track.

`confirmed` không còn là điều kiện phát alert. Mục đích của state này là hiển thị, metrics và phân biệt tình huống kéo dài với sự kiện ngắn.

## 6. Message, alert, backend và UI

Track message giữ tương thích client cũ và thêm trường tùy chọn:

```json
{
  "fall": {
    "state": "suspected|confirmed|recovered",
    "confidence": 0.91,
    "latency_ms": 380.4
  }
}
```

Khi Fall alert được phát, nội dung có title `Phát hiện trẻ có dấu hiệu té ngã`, severity `danger`, snapshot từ frame sinh event và notes gồm event type, track ID, confidence, source time.

MQTT là đường alert chính. Nếu MQTT không có, `BackendSync.post_fall_alert()` dùng REST payload riêng, không cố dùng serializer ROI. Backend nhận `TELEGRAM_ALERTS_ENABLED`; khi `false`, alert vẫn lưu DB/broadcast UI nhưng không gọi Telegram.

Frontend parse `fall` như trường optional và đổi nhãn/màu overlay ở trạng thái `suspected` hoặc `confirmed`.

## 7. Cấu hình Pi đề xuất cho thử nghiệm đầu tiên

```text
EDGE_FALL_ENABLED=true
EDGE_FALL_MODEL_PATH=/opt/children-observer/weights/fall_detection/best-416.onnx
EDGE_FALL_INPUT_SIZE=416
EDGE_FALL_FPS=2
EDGE_FALL_CONF_THRESHOLD=0.50
EDGE_FALL_VELOCITY_THRESHOLD=0.15
EDGE_FALL_STILL_VELOCITY_THRESHOLD=0.04
EDGE_FALL_STILL_SECONDS=1.0
EDGE_FALL_ALERT_ON_SUSPECTED=true
EDGE_FALL_COOLDOWN_SECONDS=30
EDGE_FALL_ONNX_INTRA_THREADS=2
EDGE_FALL_PUBLISH_ALERTS=true
EDGE_FALL_METRICS_PATH=/var/lib/children-observer/fall-metrics.jsonl
```

`best-640.onnx` chỉ dùng trên Pi khi benchmark cho thấy vẫn đạt latency p95 ≤ 450 ms, Fall ≥ 2 FPS, ROI ≥ 4 FPS, không OOM và không throttling. Không chỉ đổi đường dẫn model: phải đồng thời đặt `EDGE_FALL_INPUT_SIZE=640`.

`TELEGRAM_ALERTS_ENABLED=false` phải đặt trong môi trường backend trên laptop/server (root `.env` hoặc Docker Compose), không phải `edge.env` của Pi.

## 8. Kiểm thử đã thực hiện

| Hạng mục | Kết quả |
|---|---|
| Unit: IoU, state normal/suspected/confirmed/recovered, cooldown, reset/TTL | `6 passed` |
| ONNX smoke test sau sửa RGB/NMS | `best-416.onnx` nạp CPU thành công và trả 1 pose ở frame 6 giây |
| ONNX 640 ở video `treemtenga.mp4`, confidence 0.35 | Có 1 pose ở 12 giây (0.423); từ 13–17 giây không đủ pose hợp lệ |
| Frontend/backend/compose checks trước đó | Build/config đã qua; cần chạy lại trước release cuối |
| Pi benchmark, RTSP soak test, precision/recall chính thức | Chưa thực hiện |

Video `treemtenga.mp4` dài 17.97 giây. Model ONNX 640 mất person/pose score sau khoảng 13 giây; hạ confidence xuống 0.01 chỉ thấy candidate rất thấp (ví dụ 0.056 tại 13 giây và 0.037 tại 17 giây). Đây là hạn chế pose của checkpoint ở góc quay/tư thế này, không thể xử lý an toàn chỉ bằng cách giảm threshold.

## 9. Rủi ro và quyết định chưa hoàn tất

1. **Chất lượng pose khi trẻ ngã sát sàn chưa đủ tốt.** Cần bổ sung dữ liệu có trẻ quay lưng, chuyển động nhanh, ở xa, bị che và nằm sát sàn; sau đó fine-tune lại model.
2. **Chưa có parity report hoàn chỉnh PT–ONNX.** Cần dùng cùng `best.pt`, cùng `imgsz`, cùng confidence và cùng frame test; so sánh count, box IoU, sai số keypoint và coverage.
3. **Pose mất thì Fall state không tiến triển.** ROI box + chuyển động có thể là fallback tương lai, nhưng chưa được tích hợp; cần test kỹ `sit_down`, `lying_non_fall` và `normal` trước khi bật alert fallback.
4. **2 FPS là lựa chọn hiệu năng Pi, không phải setting dùng để đánh giá chất lượng pose.** Laptop debug/parity nên dùng FPS cao hơn; Pi chỉ tăng từ 2 lên 4/5 sau benchmark.
5. **Alert ngay tại suspected tăng rủi ro false positive.** Cooldown và điều kiện velocity giảm rủi ro nhưng không thay thế bộ negative test được gán nhãn.

## 10. Checklist trước khi đưa lên Raspberry Pi

1. Chốt checkpoint nguồn và chạy parity `best.pt` ↔ `best-416.onnx`/`best-640.onnx` với cấu hình công bằng.
2. Chuẩn bị ground truth gồm tối thiểu `fall`, `lying_non_fall`, `sit_down`, `normal`.
3. Chạy replay laptop, ghi precision/recall/F1, false alerts/hour, alert latency và pose coverage.
4. Copy ONNX đã chọn sang `/opt/children-observer/weights/fall_detection/`, kiểm SHA-256.
5. Chạy foreground Pi với RTSP, MQTT và Telegram tắt; xác minh UI, snapshot, metrics JSONL.
6. Đo CPU, RSS, nhiệt độ, `vcgencmd get_throttled`, ROI FPS và Fall FPS.
7. Soak test tối thiểu 2 giờ bằng các tình huống an toàn. Chỉ cập nhật systemd/reboot test sau khi đạt tiêu chí nghiệm thu.
