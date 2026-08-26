# Fall detection runtime trên Raspberry Pi 4

Model nguồn là `weights/fall_detection/best.pt` từ `origin/feat/fall_detection`.
SHA-256: `6E417E27CC6B23EF1615810E870919C2B30ADEACFA01DDB5EE65382624069594`.

Trên Pi chỉ dùng bản ONNX đã export: `best-640.onnx` để đối chiếu và
`best-416.onnx` để chạy thử. Copy model qua SCP, kiểm checksum và không commit
artifact vào Git. `demo_stream` chạy ROI 5 FPS; fall worker tiêu thụ latest frame
2 FPS, mỗi ONNX session tối đa 2 CPU threads. Nếu worker lỗi, ROI vẫn tiếp tục và
worker sẽ thử nạp lại sau 30 giây.

Fall chỉ đánh giá pose ghép với confirmed child track bằng IoU. State được giữ theo
`track_id`: `normal → suspected → confirmed → recovered`; cảnh báo được phát
ngay tại `suspected` khi có chuyển động rơi đo được. `confirmed` sau 1 giây
chỉ là trạng thái theo dõi, không phải điều kiện gửi cảnh báo. Mọi lần
inference được ghi JSONL tại
`/var/lib/children-observer/fall-metrics.jsonl`.

Đợt thử nghiệm phải đặt `TELEGRAM_ALERTS_ENABLED=false` trong môi trường backend:
alert vẫn đi MQTT, được lưu DB và hiển thị UI, nhưng không gọi Telegram.

## Chạy benchmark

1. Export hai ONNX artifact trên laptop từ `best.pt`, kiểm SHA-256 sau khi copy sang Pi.
2. Chạy replay video đã gán nhãn với `EDGE_FALL_FPS=2`, sau đó tính precision,
   recall, F1, false alert/hour và latency p50/p95 từ JSONL.
3. Chạy RTSP foreground rồi soak test tối thiểu 2 giờ. Theo dõi `vcgencmd
   measure_temp`, `vcgencmd get_throttled`, RAM và effective FPS.

Tiêu chí ban đầu: recall ≥ 90%, precision ≥ 80%, fall ≥ 2 FPS, ROI ≥ 4 FPS, p95
fall inference ≤ 450 ms, không throttling và không OOM.

> Lưu ý xác minh: `best.pt` và ONNX 416 đều không trả pose trên frame trẻ đứng của
> `module_edge_firmware/test_video.mp4`. Đây là video ROI, không phải bộ fall test;
> cần dùng video có té ngã đã gán nhãn để kết luận độ chính xác. Nếu model cũng
> không trả pose trong clip fall thật, dừng rollout và yêu cầu lại artifact/model.
