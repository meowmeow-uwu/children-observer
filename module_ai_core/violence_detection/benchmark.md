### Báo Cáo Kết Quả Inference & Đánh Giá Toàn Bộ Dataset Phát Hiện Bạo Lực

Quá trình inference toàn diện trên toàn bộ dataset video bằng mô hình model.pth đã hoàn tất thành công 100% (2,000/2,000 video).
──────

### 1. Phân Tích Cấu Trúc Dataset

Thư mục archive chứa tập dữ liệu thực tế Real Life Violence Situations Dataset với định dạng video .mp4:

• Tổng số video: 2,000 video phân bố cân bằng (50/50):
• NonViolence (Phi bạo lực): 1,000 video (NV_1.mp4 → NV_1000.mp4)
• Violence (Bạo lực): 1,000 video (V_1.mp4 → V_1000.mp4)
• Độ dài trung bình clip: 16 frames được trích xuất đều (uniform temporal sampling), resize về 224 × 224 và chuẩn hóa theo phân phối ImageNet.
──────

### 2. Bảng Chỉ Số Đánh Giá Chi Tiết (Tại Ngưỡng Mặc Định Threshold = 0.50)

Chỉ số (Metric) │ Toàn Bộ Dataset │ Lớp NonViolence │ Lớp Violence
────────────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────
Độ chính xác (Accuracy) │ 84.75% │ — │ —
Độ chính xác dự đoán (Precision) │ — │ 89.99% │ 80.73%
Độ bao phủ / Nhạy (Recall) │ — │ 78.20% │ 91.30%
F1-Score │ 0.8468 (Macro) │ 0.8368 │ 0.8569
ROC - AUC Score │ 0.9216 (Khả năng phân tách nhãn cực mạnh) │ — │ —
Số lượng mẫu (Support) │ 2,000 video │ 1,000 video │ 1,000 video
──────

### 3. Ma Trận Nhầm Lẫn (Confusion Matrix)

                                DỰ ĐOÁN (PREDICTED)
                         NonViolence          Violence
    THỰC TẾ  NonViolence    782 (TN)            218 (FP)
    (TRUE)   Violence        87 (FN)            913 (TP)

• True Positives (TP - Bắt đúng bạo lực): 913 / 1,000 video (đạt 91.30%).
• False Negatives (FN - Bỏ sót bạo lực): 87 / 1,000 video (tỷ lệ bỏ sót chỉ 8.70%).
• True Negatives (TN - Nhận diện đúng an toàn): 782 / 1,000 video (78.20%).
• False Positives (FP - Báo động giả): 218 / 1,000 video (21.80% - chủ yếu ở các hành động cử động nhanh, đùa nghịch).
──────

### 4. Phân Bố Xác Suất Dự Đoán (Probability Distribution)

• Video Bạo Lực (Violence Dataset):
• Xác suất trung bình gán nhãn Violence: 𝟖𝟖.𝟗𝟑%
• Trung vị (Median confidence): 𝟗𝟗.𝟓𝟕% (Mô hình nhận diện hành vi đánh đấm, ẩu đả với độ tự tin áp đảo).
• Video Phi Bạo Lực (NonViolence Dataset):
• Xác suất trung bình gán nhãn Violence: 𝟐𝟑.𝟖𝟎%
• Trung vị (Median confidence): 𝟑.𝟗𝟒% (Phần lớn video sinh hoạt bình thường có xác suất bạo lực dưới 5%).

──────

### 5. Khảo Sát Độ Nhạy Theo Ngưỡng Quyết Định (Threshold Sensitivity)

Tùy theo bài toán thực tế triển khai (ưu tiên giảm báo động giả hay ưu tiên tuyệt đối không bỏ sót bạo lực), có thể linh hoạt chọn ngưỡng:

     Ngưỡng (Threshold)    │        Accuracy         │        Macro F1         │  Precision (Violence)  │   Recall (Violence)    │ Precision (NonViolence) │  Recall (NonViolence)

─────────────────────────┼─────────────────────────┼─────────────────────────┼────────────────────────┼────────────────────────┼─────────────────────────┼────────────────────────
0.20 │ 81.65% │ 0.8134 │ 75.18% │ 94.50% │ 92.60% │ 68.80%
0.30 │ 83.10% │ 0.8291 │ 77.36% │ 93.60% │ 91.90% │ 72.60%
0.40 │ 84.05% │ 0.8394 │ 79.28% │ 92.20% │ 90.68% │ 75.90%
0.50 (Default) │ 84.75% │ 0.8468 │ 80.73% │ 91.30% │ 89.99% │ 78.20%
0.60 (Tối ưu Acc) │ 85.35% │ 0.8532 │ 82.46% │ 89.80% │ 88.80% │ 80.90%
0.70 │ 85.20% │ 0.8519 │ 83.46% │ 87.80% │ 87.13% │ 82.60%
0.80 (Giảm False Alarm) │ 84.70% │ 0.8470 │ 85.34% │ 83.80% │ 84.09% │ 85.60%
──────

### 6. File Báo Cáo Chi Tiết

Toàn bộ log inference chi tiết (xác suất của từng video trong số 2,000 video kèm latency) đã được xuất và lưu tại:

• File kết quả đầy đủ: final_evaluation_report.json
• Script đánh giá: fast_eval_all.py
