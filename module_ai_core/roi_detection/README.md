# Task AI #1: ROI & Object Detection (P3)

## 🎯 Nhiệm vụ
Huấn luyện YOLO26 phát hiện **trẻ em** và **vật nguy hiểm** (dao, kéo, ổ điện, bật lửa...).
Kết hợp với logic ROI để cảnh báo khi trẻ tiếp cận vùng nguy hiểm.

## 📂 File làm việc
- `module_ai_core/datasets/childsun_loader.py` — Bộ nạp dữ liệu ChildSUn (~5.350 ảnh).
- `module_ai_core/models/object_detector.py` — YOLO26 wrapper (train/predict/export).
- `module_ai_core/datasets/augmentation.py` — Data augmentation dùng chung.
- `train.py` — Script huấn luyện riêng cho task này.

## 🚀 Cách chạy huấn luyện
```bash
# Chuẩn bị dữ liệu
python scripts/download_dataset.py --dataset childsun

# Huấn luyện
python module_ai_core/roi_detection/train.py

# Export sang ONNX
python scripts/convert_model.py --model weights/roi_detection/best.pt --format onnx
```

## 📤 Output (Giao cho Module 2)
Sau khi train xong, copy file model vào:
```
weights/roi_detection/best.pt      # PyTorch weights
weights/roi_detection/best.onnx    # ONNX (tùy chọn)
```
Sau đó cập nhật `weights/registry.json`:
```json
{
  "roi_detection": {
    "status": "ready",
    "path": "weights/roi_detection/best.pt",
    "mAP50": 0.85
  }
}
```

## ⚙️ Biến .env liên quan
- `YOLO_MODEL_PATH`: Đường dẫn model.
- `INFERENCE_CONF_THRESHOLD`: Ngưỡng tin cậy.
- `INFERENCE_DEVICE`: `cuda:0` hoặc `cpu`.

## 📊 Tiêu chí hoàn thành (DoD)
- [ ] mAP@0.5 ≥ 0.80 trên tập validation.
- [ ] Phát hiện được ít nhất 5 loại vật nguy hiểm.
- [ ] File model đã được lưu vào `weights/roi_detection/`.
- [ ] Cập nhật `registry.json` với trạng thái "ready".
