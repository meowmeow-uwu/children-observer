# Raspberry Pi 4: triển khai Edge AI end-to-end

Tài liệu này triển khai **một Raspberry Pi cho một camera**. Laptop chạy Docker
Compose cho MQTT, PostgreSQL, FastAPI và frontend; Pi chỉ chạy Edge AI native.
Pi, camera Dahua và laptop phải cùng LAN. Giai đoạn này chưa dùng TURN, vì vậy
browser nghiệm thu chạy trên laptop cùng mạng với Pi.

> Không đưa RTSP URL thật vào Git, tài liệu, shell history hoặc ảnh chụp màn
> hình. Edge che credential trong log, nhưng file `/etc/children-observer/edge.env`
> vẫn là dữ liệu nhạy cảm.

## 1. Khởi động server trên laptop

Kiểm tra IP laptop trước. Giá trị trong template là `192.168.2.67`; phải tạo
DHCP reservation trước khi dùng lâu dài.

```powershell
cd D:\WorkSpace\Project\children-observer
.\scripts\start_server.ps1
```

Script này **không** khởi động `guardian_edge`. Kiểm tra backend và frontend:

```powershell
Invoke-RestMethod http://127.0.0.1:8007/healthz
docker compose ps
```

Từ Pi, cổng MQTT của laptop phải truy cập được. Nếu Windows Firewall chặn,
cho phép inbound TCP 1883 trên mạng Private.

## 2. Chuẩn bị Raspberry Pi

Yêu cầu Raspberry Pi OS Lite 64-bit, Ethernet, SSH, thẻ nhớ còn ít nhất 8 GB
trống và tản nhiệt chủ động. Kiểm tra kiến trúc:

```bash
uname -m
df -h /
```

`uname -m` phải là `aarch64`. Cài các gói hệ thống:

```bash
sudo apt update
sudo apt install -y git curl ffmpeg mosquitto-clients libgl1 libglib2.0-0 \
  libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev libswscale-dev \
  libswresample-dev build-essential avahi-daemon
```

Cài `uv`, Python 3.12 và source. Thay `<REPOSITORY_URL>` bằng URL Git của dự
án và `<DEPLOY_BRANCH>` bằng nhánh đã được nghiệm thu (hiện tại là
`feat/deploy_raspberrypi`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
sudo install -m 0755 "$(command -v uv)" /usr/local/bin/uv
sudo useradd --system --home /opt/children-observer --shell /usr/sbin/nologin children-observer
sudo git clone --branch <DEPLOY_BRANCH> <REPOSITORY_URL> /opt/children-observer
sudo chown -R children-observer:children-observer /opt/children-observer
sudo -u children-observer /usr/local/bin/uv sync --directory /opt/children-observer --extra edge --frozen
```

Nếu source trên laptop có commit chưa push, push commit đó trước khi clone để
Pi và laptop dùng cùng SHA. So sánh `git rev-parse HEAD` ở hai nơi.

## 3. Chuyển model và cấu hình bảo mật

Model ONNX đang bị Git ignore, nên copy riêng từ laptop. Trên laptop:

```powershell
Get-FileHash .\weights\roi_detection\best.onnx -Algorithm SHA256
scp .\weights\roi_detection\best.onnx <PI_USER>@<PI_IP>:/tmp/best.onnx
```

Trên Pi:

```bash
sudo install -D -o children-observer -g children-observer -m 0644 \
  /tmp/best.onnx /opt/children-observer/weights/roi_detection/best.onnx
sha256sum /opt/children-observer/weights/roi_detection/best.onnx
sudo rm /tmp/best.onnx
```

Checksum ở Pi phải khớp laptop. Tạo cấu hình thật từ template:

```bash
sudo install -d -m 0750 /etc/children-observer
sudo cp /opt/children-observer/deploy/raspberry-pi/edge.env.example /etc/children-observer/edge.env
sudo chown root:children-observer /etc/children-observer/edge.env
sudo chmod 0640 /etc/children-observer/edge.env
sudoedit /etc/children-observer/edge.env
```

Giữ `EDGE_CAMERA_ID=camera_living_room_01`. Điền RTSP URL hiện tại vào
`EDGE_RTSP_URL`; mọi ký tự đặc biệt trong password phải URL-encode. Giữ
`OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp` và dùng substream
`subtype=1`.

## 4. Kiểm tra kết nối trước khi chạy AI

```bash
ping -c 3 192.168.2.106
ping -c 3 192.168.2.67
mosquitto_sub -h 192.168.2.67 -p 1883 \
  -t 'devices/camera_living_room_01/roi/update' -C 1 -v
```

Lệnh MQTT phải nhận một retained ROI. Sau đó kiểm tra import runtime:

```bash
cd /opt/children-observer
sudo -u children-observer .venv/bin/python -c "import cv2, onnxruntime, ultralytics, aiortc, av, aiomqtt; print(onnxruntime.get_available_providers())"
```

## 5. Chạy foreground và nghiệm thu alert

Chạy foreground để xem lỗi trực tiếp trước khi cài service:

```bash
cd /opt/children-observer
sudo -u children-observer bash -c 'set -a; . /etc/children-observer/edge.env; set +a; exec /opt/children-observer/.venv/bin/python -m module_edge_firmware.demo_stream'
```

Log cần có: ONNX load thành công, `RTSP stream connected` (không có password),
`MQTT connected`, và `Applied ... ROI zones`. Trên giao diện laptop đăng nhập,
mở camera, vẽ ROI theo khung hình camera thật rồi đưa người/trẻ vào vùng đó.

Kiểm tra alert và snapshot:

```powershell
docker compose logs --tail=100 backend mqtt
docker compose exec db psql -U admin -d child_guardian_db -c "SELECT event_id, camera_id, snapshot_url, created_at FROM alerts ORDER BY created_at DESC LIMIT 10;"
```

Alert phải hiển thị trên UI và snapshot phải mở được qua backend.

## 6. Nghiệm thu video WebRTC

Trên browser của laptop, mở camera. Chuỗi cần thành công là browser offer →
backend MQTT → Pi answer → browser ICE `connected/completed` → remote video
track. Nếu signaling thành công nhưng video không lên, kiểm tra firewall,
client isolation/VLAN và `chrome://webrtc-internals`. Không thêm TURN ở bước
này; TURN chỉ là hạng mục sau khi host candidate cùng LAN thất bại.

## 7. Cài systemd và soak test

Sau khi foreground ổn định:

```bash
sudo cp /opt/children-observer/deploy/raspberry-pi/children-observer-edge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now children-observer-edge
sudo systemctl status children-observer-edge
journalctl -u children-observer-edge -f
```

Reboot Pi rồi xác nhận service, RTSP, MQTT, alert, snapshot và WebRTC đều tự
khôi phục. Chạy tối thiểu hai giờ, theo dõi:

```bash
vcgencmd measure_temp
vcgencmd get_throttled
free -h
top
```

Mục tiêu: inference khoảng 4–5 FPS, không bị throttling, RTSP/MQTT tự
reconnect, snapshot còn sau khi recreate backend. Nếu Pi quá tải, lần lượt
giảm `EDGE_WEBRTC_FPS` xuống 8, `EDGE_DETECTION_FPS` xuống 4, rồi giảm độ phân
giải/bitrate substream camera.
