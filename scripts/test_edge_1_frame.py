import cv2
import numpy as np
from loguru import logger
import json

# Tắt bớt log không cần thiết để dễ nhìn output
import logging
logging.getLogger("ultralytics").setLevel(logging.WARNING)

from module_edge_firmware.inference.multi_task_runner import MultiTaskRunner

def main():
    print("🚀 1. Khởi tạo Edge MultiTaskRunner (Module 2)...")
    runner = MultiTaskRunner()
    
    # Hàm này sẽ tự động đọc registry.json và load roi_detection
    runner.load_all()
    
    import sys
    
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
        print(f"\n📷 2. Đang đọc ảnh từ: {img_path}...")
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"❌ Lỗi: Không thể đọc ảnh. Vui lòng kiểm tra lại đường dẫn: {img_path}")
            return
    else:
        print("\n📷 2. Lấy 1 khung hình thử nghiệm (Nhiễu ngẫu nhiên)...")
        print("💡 MẸO: Bạn có thể test ảnh thật bằng cách thêm đường dẫn ảnh vào sau lệnh chạy!")
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    
    print("🧠 3. Module Edge đưa khung hình vào xử lý AI...")
    analysis = runner.analyze_frame(frame)
    
    # In ra toàn bộ kết quả trả về của một Frame (đã được Edge đóng gói)
    print("\n" + "="*60)
    print("✅ KẾT QUẢ MODULE 2 (EDGE) TRẢ VỀ CHO 1 KHUNG HÌNH CHÍNH XÁC LÀ:")
    
    # Chuyển đổi sang JSON để dễ đọc
    result_dict = analysis.to_dict()
    print(json.dumps(result_dict, indent=4, ensure_ascii=False))
    print("="*60)

if __name__ == "__main__":
    main()
