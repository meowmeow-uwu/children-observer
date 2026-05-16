import cv2
import time
from pathlib import Path
from module_ai_core.models.object_detector import ObjectDetector
from module_ai_core.model_registry import ModelRegistry
from configs.settings import get_settings

def main():
    settings = get_settings()
    registry = ModelRegistry()
    
    print("⏳ Đang load mô hình ROI Detection...")
    # Khởi tạo detector
    model_path = registry.get_model_path("roi_detection") if registry.is_ready("roi_detection") else "weights/roi_detection/best.pt"
    
    detector = ObjectDetector(
        model_path=model_path,
        engine_type="yolo",  # Hoặc 'onnx', 'tensorrt' tùy bạn
        device=settings.inference_device,
        conf_threshold=0.25  # Giảm ngưỡng tin cậy để test camera dễ hơn
    )
    detector.load()
    print("✅ Load mô hình thành công!")

    # Khởi tạo Camera (0 thường là webcam mặc định của laptop)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Không thể mở được Camera.")
        return

    print("🎥 Bắt đầu Inference Camera... Bấm 'q' để thoát.")
    
    # Khởi tạo thông số đếm FPS
    prev_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # 1. Gọi mô hình phân tích
        results = detector.predict(frame)
        
        # 2. Lấy dữ liệu 
        children = results.get_children()
        dangerous_objs = results.get_dangerous_objects()
        
        # 3. Vẽ Bounding Box lên Frame
        for i in range(len(results)):
            box = results.boxes[i]
            x1, y1, x2, y2 = map(int, box)
            label = f"{results.class_names[i]} {results.scores[i]:.2f}"
            
            # Đổi màu box: Trẻ em -> Xanh, Vật nguy hiểm -> Đỏ
            color = (0, 255, 0) if results.class_names[i] == "child" else (0, 0, 255)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Tính toán và hiển thị FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        
        # Hiển thị text trạng thái
        status_text = f"FPS: {fps:.1f} | Children: {len(children)} | Danger: {len(dangerous_objs)}"
        cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # 4. Hiển thị lên màn hình
        cv2.imshow("ROI Detection Test", frame)
        
        # Bấm phím 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
