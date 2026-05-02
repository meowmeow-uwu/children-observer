# Task AI #2: Violence Detection (P4)

## 🎯 Nhiệm vụ
Huấn luyện mô hình **ST-GCN** để nhận diện hành vi bạo lực (đánh, xô, đẩy) từ chuỗi skeleton keypoints.

## 📂 File làm việc
- `module_ai_core/datasets/violence_loader.py` — Bộ nạp dữ liệu skeleton bạo lực.
- `module_ai_core/models/behavior_classifier.py` — ST-GCN wrapper.
- `train.py` — Script huấn luyện riêng cho task này.

## 🚀 Cách chạy huấn luyện
```bash
# Chuẩn bị dữ liệu
python scripts/download_dataset.py --dataset violence

# Huấn luyện
python module_ai_core/violence_detection/train.py

# Huấn luyện tùy chỉnh
python module_ai_core/violence_detection/train.py --epochs 200 --lr 0.001
```

## 📤 Output (Giao cho Module 2)
Sau khi train xong, copy file model vào:
```
weights/violence_detection/stgcn_best.pt
```
Cập nhật `weights/registry.json`:
```json
{
  "violence_detection": {
    "status": "ready",
    "path": "weights/violence_detection/stgcn_best.pt",
    "accuracy": 0.92
  }
}
```

## ⚙️ Biến .env liên quan
- `BEHAVIOR_MODEL_PATH`: Đường dẫn model ST-GCN.
- `INFERENCE_DEVICE`: `cuda:0` hoặc `cpu`.

## 📊 Tiêu chí hoàn thành (DoD)
- [ ] Accuracy ≥ 0.85 trên tập validation.
- [ ] Phân biệt ≥ 4 loại hành vi (normal, slap, push, kick).
- [ ] File model đã lưu vào `weights/violence_detection/`.
- [ ] Cập nhật `registry.json`.
