# Module AI Core - Bộ não AI

Module này được chia thành **3 sub-module độc lập** để 3 người có thể làm việc song song.

## 📁 Cấu trúc Module
```
module_ai_core/
├── roi_detection/          # 👤 P3 — Phát hiện vật thể & ROI
│   ├── README.md           # Hướng dẫn riêng cho P3
│   └── train.py            # Script train YOLO26
│
├── violence_detection/     # 👤 P4 — Nhận diện bạo lực
│   ├── README.md           # Hướng dẫn riêng cho P4
│   └── train.py            # Script train ST-GCN
│
├── fall_detection/         # 👤 P5 — Phát hiện té ngã
│   ├── README.md           # Hướng dẫn riêng cho P5
│   └── train.py            # Script train YOLO-Pose
│
├── datasets/               # 📦 Code dùng chung — Data Loaders
│   ├── childsun_loader.py
│   ├── violence_loader.py
│   └── augmentation.py
│
├── models/                 # 🧠 Code dùng chung — Model Wrappers
│   ├── object_detector.py
│   ├── pose_estimator.py
│   └── behavior_classifier.py
│
├── training/               # 🔧 Code dùng chung — Training Utilities
│   ├── trainer.py
│   ├── evaluator.py
│   └── export.py
│
└── model_registry.py       # 📋 Theo dõi model nào đã sẵn sàng
```

## 🔄 Quy trình làm việc

### Mỗi người AI làm việc độc lập:
1. Đọc **README.md** trong thư mục của mình (`roi_detection/`, `violence_detection/`, `fall_detection/`).
2. Chuẩn bị dữ liệu và chạy script `train.py` riêng.
3. Sau khi train xong, lưu model vào `weights/<task_name>/`.
4. Cập nhật `weights/registry.json` với trạng thái `"ready"`.

### Module 2 (Edge) tích hợp linh hoạt:
- `MultiTaskRunner` tự động đọc `registry.json` khi khởi động.
- Chỉ load model nào có status `"ready"` và file tồn tại.
- Nếu chỉ có 1 model (ví dụ: ROI xong, Violence chưa xong), pipeline vẫn chạy với task đó.

## 📋 Model Registry (`weights/registry.json`)
```json
{
  "roi_detection":      { "status": "ready",       "path": "weights/roi_detection/best.pt" },
  "violence_detection": { "status": "training",    "path": null },
  "fall_detection":     { "status": "not_started",  "path": null }
}
```
**Trạng thái:**
- `not_started`: Chưa bắt đầu train.
- `training`: Đang train.
- `ready`: Đã train xong, model sẵn sàng cho Module 2.

## 🛠 Chạy nhanh từng task
```bash
# P3: ROI Detection
python module_ai_core/roi_detection/train.py

# P4: Violence Detection
python module_ai_core/violence_detection/train.py

# P5: Fall Detection (dùng pretrained)
python module_ai_core/fall_detection/train.py --pretrained
```
