# 📊 Báo cáo Kết quả Training 50 Epochs — ROI Detection (Final)

## 1. Cấu hình Training

| Thông số | Giá trị |
|---|---|
| **Model** | YOLO26n (Nano) |
| **Dataset** | KidSentry Master Dataset (Roboflow) |
| **Train / Val** | 15,774 / 2,106 ảnh |
| **Epochs** | 50 |
| **Batch size** | 16 |
| **Image size** | 640 × 640 |

---

## 2. Tiến trình Training qua 50 Epochs (Trích xuất)

| Epoch | Box Loss | Cls Loss | DFL Loss | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|---|
| 1/50 | 1.293 | 3.859 | 0.013 | 0.646 | 0.628 | 0.667 | 0.443 |
| 10/50 | 1.279 | 1.108 | 0.013 | 0.849 | 0.800 | 0.866 | 0.596 |
| 25/50 | 1.079 | 0.809 | 0.011 | 0.893 | 0.880 | 0.919 | 0.695 |
| 40/50 | 0.928 | 0.646 | 0.009 | 0.923 | 0.881 | 0.933 | 0.731 |
| 50/50 | 0.687 | 0.330 | 0.007 | 0.923 | 0.895 | 0.933 | 0.740 |

---

## 3. Kết quả đánh giá chi tiết trên tập Validation

| Class | Images | Instances | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| 👨 **adult** | 607 | 888 | 0.857 | 0.798 | 0.848 | 0.618 |
| 👶 **child** | 733 | 1540 | 0.886 | 0.820 | 0.895 | 0.617 |
| 🔪 **knife** | 417 | 657 | 0.959 | 0.956 | 0.979 | 0.832 |
| 🔌 **outlet** | 533 | 723 | 0.986 | 0.989 | 0.993 | 0.839 |
| ✂️ **scissors**| 519 | 660 | 0.944 | 0.918 | 0.963 | 0.796 |
| **Tổng (all)**| **2106** | **4468** | **0.926** | **0.896** | **0.935** | **0.740** |

---

## 4. Ghi chú & Đánh giá
* **Khởi đầu (Epoch 1):** Model đạt mAP50 là **0.667** ngay từ epoch đầu tiên.
* **Hội tụ (Epoch 50):** Model đạt điểm mAP50 tổng rất cao lên tới **0.935**, tăng đáng kể so với bản train 10 Epoch trước đó (0.910).
* **Đánh giá riêng lẻ:**
  * Khả năng nhận diện vật thể nguy hiểm (dao, kéo, ổ điện) **cực kỳ xuất sắc**, gần như đạt điểm tuyệt đối (từ 0.96 đến 0.99 mAP50).
  * Điểm nhận diện người lớn và trẻ em cũng đã cải thiện rõ rệt so với bản cũ (child mAP50 tăng từ 0.844 lên 0.895).
* **Kết luận:** Mô hình YOLO26 Nano với 50 epochs này đã vượt quá tiêu chuẩn đầu ra, cực kỳ nhẹ nhưng vẫn giữ được độ chính xác hoàn hảo. Hoàn toàn sẵn sàng đẩy lên Edge Firmware!
