# Task AI #1: ROI & Object Detection (P3)

## 🎯 Nhiệm vụ

Huấn luyện mô hình YOLO26 để phát hiện chính xác **trẻ em** và các **vật thể nguy hiểm** trong khung hình.

> [!IMPORTANT]
> **Phân định trách nhiệm:**
>
> - **Module AI:** Chịu trách nhiệm **Object Detection** (trả về Bounding Box, Label, Confidence, Time Inference).
> - **Module Edge Firmware:** Chịu trách nhiệm **ROI Logic** (kiểm tra va chạm giữa Bounding Box và vùng đa giác/Polygon). Team AI **không** cần code logic kiểm tra vùng nguy hiểm.

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

# Export sang định dạng tối ưu cho Edge (Yêu cầu bởi Team Edge)
python scripts/convert_model.py --model weights/roi_detection/best.pt --format onnx
```

## 📤 Output & Interface (Bàn giao cho Team Edge)

Sau khi train xong, model cần đảm bảo các tiêu chuẩn sau để tích hợp vào `EdgePipeline`:

1. **Định dạng file:**
   - `weights/roi_detection/best.pt` (PyTorch)
   - `weights/roi_detection/best.onnx` (Ưu tiên để chạy TensorRT)
2. **Hệ tọa độ:** Bounding Box phải được trả về dưới dạng **chuẩn hóa (0.0 đến 1.0)** hoặc tọa độ pixel tương ứng với resolution gốc của camera.
3. **Danh sách Labels:** Cần thống nhất tại `configs/labels.json`. Các label bắt buộc:
   - `child`
   - `knife`, `scissors`, `socket`, `lighter`, `stove` (vật thể nguy hiểm)

## 📊 Tiêu chí hoàn thành (DoD)

- [ ] mAP@0.5 ≥ 0.80 trên tập validation cho tất cả các class.
- [ ] Export thành công sang định dạng **ONNX**.
- [ ] Cập nhật `weights/registry.json` với đường dẫn và thông số model mới nhất.
- [ ] Kiểm tra độ trễ (latency) của model trên thiết bị Edge mục tiêu (Target < 50ms/frame).
