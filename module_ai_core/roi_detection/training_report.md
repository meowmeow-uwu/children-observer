# 📊 Báo cáo Kết quả Training & Đánh giá — ROI Detection (100 Epochs)

> **Thông tin đợt chạy:**  
> - **Thư mục nguồn (Run directory):** [`runs/detect/runs/roi_detection/childsun_100e_img640_20260818_230730`](file:///home/nguyenhuynh/Documents/children-observer/runs/detect/runs/roi_detection/childsun_100e_img640_20260818_230730)  
> - **Trọng số được lưu chính thức:** [`weights/roi_detection/best.pt`](file:///home/nguyenhuynh/Documents/children-observer/weights/roi_detection/best.pt) và [`weights/roi_detection/best.onnx`](file:///home/nguyenhuynh/Documents/children-observer/weights/roi_detection/best.onnx)  
> - **Model Registry:** [`weights/registry.json`](file:///home/nguyenhuynh/Documents/children-observer/weights/registry.json) (`mAP50`: `0.9484068733432054` ~ **94.84%**)

---

## 1. Cấu hình Huấn luyện (Training Configuration)

| Thông số | Giá trị chi tiết | Ghi chú |
|---|---|---|
| **Model Architecture** | YOLO26n (Nano) | Pretrained từ `yolo26n.pt` |
| **Dataset** | ChildSUn (`./data/childsun/data.yaml`) | ~18,913 ảnh tổng hợp (Train / Val / Test) |
| **Image Size** | `640 × 640` | Tối ưu nhận diện các vật thể nhỏ (dao, kéo, ổ điện) |
| **Epochs** | `100` | Tự động tắt Mosaic ở 15 epoch cuối (`close_mosaic: 15`) |
| **Batch Size** | `32` | Tối ưu hóa bộ nhớ GPU V100 |
| **Optimizer & LR** | AdamW (`lr0 = 0.01`, `lrf = 0.01`, `momentum = 0.937`) | Auto warmup 3 epochs |
| **Data Augmentation** | `hsv_h: 0.01`, `hsv_s: 0.35`, `hsv_v: 0.25`, `degrees: 5.0`, `translate: 0.05`, `scale: 0.25`, `fliplr: 0.5`, `mosaic: 0.5` | Preset dành riêng cho camera trong nhà |
| **Thời gian huấn luyện** | `7,992.09 giây` (~2.22 giờ / ~133 phút) | Thực thi mượt mà trên Tesla V100 |

---

## 2. Kết quả Đánh giá Mô hình `best.pt` trên tập Validation

> [!IMPORTANT]
> Sau khi kết thúc 100 Epochs, Ultralytics tự động chọn mô hình có điểm **Fitness Score cao nhất** (tương ứng với mô hình `best.pt`) và tiến hành đánh giá trên tập Validation. Chỉ số thu được được ghi nhận trực tiếp vào [`weights/registry.json`](file:///home/nguyenhuynh/Documents/children-observer/weights/registry.json).

### 📊 Bảng tổng quan Đánh giá trên tập Validation:

| Chỉ số Metric | Giá trị Validation (`best.pt`) | Tiêu chí Mục tiêu (DoD) | Trạng thái |
|---|---|---|---|
| **Precision (Độ chính xác)** | **0.9498** (94.98%) | — | ✅ Rất cao |
| **Recall (Độ phủ)** | **0.9178** (91.78%) | — | ✅ Rất cao |
| **mAP50 (Chính thức đăng ký Registry)** | **0.9484** (**94.84%**) | **≥ 0.80 (80%)** | ✅ **Vượt tiêu chuẩn** |
| **mAP50-95** | **0.7608** (76.08%) | — | ✅ Định vị BBox rất sát |

---

## 3. Tiến trình Huấn luyện chi tiết qua 100 Epochs

### 📈 Điểm mốc quan trọng trong quá trình huấn luyện:

| Epoch | Train Box Loss | Train Cls Loss | Precision | Recall | mAP50 (Val) | mAP50-95 (Val) | Ghi chú / Trạng thái |
|---|---|---|---|---|---|---|---|
| **1** | 1.2120 | 5.0248 | 0.5535 | 0.5617 | 0.5685 | 0.3413 | Bắt đầu huấn luyện |
| **10** | 1.2939 | 1.0150 | 0.8110 | 0.7766 | 0.8430 | 0.5230 | Đạt mAP50 > 0.80 (Vượt mốc DoD) |
| **25** | 1.1223 | 0.7551 | 0.9169 | 0.8589 | 0.9232 | 0.6456 | Tăng trưởng đều đặn |
| **50** | 0.9746 | 0.5779 | 0.9294 | 0.8995 | 0.9413 | 0.7190 | mAP50 vượt mốc 0.94 |
| **78** | 0.8352 | 0.4645 | 0.9492 | 0.9175 | **0.9511** | 0.7556 | **Đạt đỉnh mAP50 tức thời (Peak)** |
| **85** | 0.7848 | 0.4264 | 0.9524 | 0.9125 | 0.9482 | 0.7598 | Epoch cuối cùng dùng Mosaic |
| **86** | 0.6711 | **0.2390** | 0.9517 | 0.9144 | 0.9481 | 0.7595 | **Close Mosaic**: Loss Cls giảm sâu đột ngột |
| **100** | **0.5972** | **0.2074** | **0.9498** | **0.9178** | **0.9473** | **0.7608** | **Kết thúc 100 Epochs (mAP50-95 đỉnh cao)** |

---

## 4. Phân tích Chi tiết Kết quả

1. **Khả năng hội tụ & Tối ưu Loss:**
   - **Classification Loss (`train/cls_loss`)**: Giảm mạnh từ `5.0248` (Epoch 1) xuống còn `0.2074` (Epoch 100) — giảm hơn 24 lần.
   - **Bounding Box Loss (`train/box_loss`)**: Giảm từ `1.2120` xuống `0.5972` — giảm hơn 50%.
   - **Tác động của `close_mosaic` ở Epoch 85**: Từ Epoch 86, việc tắt Mosaic giúp mô hình tinh chỉnh trên hình ảnh tự nhiên, giúp `cls_loss` giảm ngay từ `0.4264` xuống `0.2390`.

2. **Chỉ số mAP (Mean Average Precision):**
   - **mAP50 đánh giá mô hình `best.pt`:** Đạt **`0.9484` (94.84%)** (đã được ghi nhận vào `registry.json`).
   - **mAP50-95 đỉnh cao:** Đạt **`0.7608` (76.08%)** ở Epoch 100.
   - **Độ ổn định:** Từ Epoch 50 trở đi, `mAP50` luôn duy trì ổn định ở mức `0.94+`, chứng tỏ mô hình không bị overfitting và học rất chắc chắn.

---

## 5. Các File Đồ thị & Artifacts trong Folder Run

Thư mục run [`runs/detect/runs/roi_detection/childsun_100e_img640_20260818_230730/`](file:///home/nguyenhuynh/Documents/children-observer/runs/detect/runs/roi_detection/childsun_100e_img640_20260818_230730) chứa đầy đủ các file artifact đồ thị để kiểm tra:

- 📊 **`results.png`**: Biểu đồ toàn bộ tiến trình Loss & Metrics qua 100 Epochs.
- 🎯 **`confusion_matrix.png` & `confusion_matrix_normalized.png`**: Ma trận nhầm lẫn giữa 5 class (`adult`, `child`, `knife`, `outlet`, `scissors`).
- 📈 **`BoxPR_curve.png`**: Đường cong Precision-Recall cho từng class.
- 📈 **`BoxF1_curve.png` / `BoxP_curve.png` / `BoxR_curve.png`**: Các biểu đồ F1-Score, Precision, Recall theo Confidence Threshold.
- 🖼️ **`val_batch0_pred.jpg`, `val_batch1_pred.jpg`, `val_batch2_pred.jpg`**: Ảnh minh họa kết quả dự đoán trực quan trên tập Validation.
- 💾 **`weights/best.pt` & `weights/last.pt`**: File trọng số 5.4 MB đã được xuất đè sang thư mục chính [`weights/roi_detection/best.pt`](file:///home/nguyenhuynh/Documents/children-observer/weights/roi_detection/best.pt).

---

## 6. Đối chiếu Tiêu chuẩn Hoàn thành (Definition of Done - DoD)

| Tiêu chí DoD | Yêu cầu | Kết quả Validation (`best.pt`) | Trạng thái |
|---|---|---|---|
| **mAP50 tổng** | ≥ 0.80 | **0.9484** (94.84%) | ✅ Đạt xuất sắc |
| **Độ trễ Inference** | < 50ms/frame | **~2.5 ms/frame** (~400 FPS) | ✅ Đạt |
| **Xuất ONNX** | Định dạng ONNX | [`weights/roi_detection/best.onnx`](file:///home/nguyenhuynh/Documents/children-observer/weights/roi_detection/best.onnx) | ✅ Đạt |
| **Registry Update** | Đã cập nhật | [`weights/registry.json`](file:///home/nguyenhuynh/Documents/children-observer/weights/registry.json) (`mAP50`: 0.9484) | ✅ Đạt |

---

> [!NOTE]
> Mô hình từ đợt train 100 epoch này đã hoàn tất việc đóng gói, cập nhật Registry và xuất file ONNX chuẩn. Đã hoàn toàn sẵn sàng cho việc đưa vào pipeline suy luận của Edge Firmware và Triton Server.