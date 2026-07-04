import asyncio
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

class AIVideoTrack(VideoStreamTrack):
    """
    Class này có nhiệm vụ lấy khung hình đã qua xử lý AI (Numpy Array BGR) 
    và đóng gói thành chuẩn WebRTC (YUV/RGB) để truyền đi.
    """
    def __init__(self):
        super().__init__()
        # Khởi tạo một khung hình đen chờ sẵn
        self.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def update_frame(self, frame: np.ndarray):
        """
        Hàm này sẽ được gọi liên tục bởi module AI inference (engine.py) 
        mỗi khi có khung hình mới được xử lý xong.
        """
        self.current_frame = frame

    async def recv(self) -> VideoFrame:
        """
        Hàm cốt lõi của aiortc. WebRTC sẽ gọi hàm này liên tục để lấy frame đẩy lên mạng.
        """
        # Tính toán timestamp cho frame tiếp theo (bắt buộc trong truyền phát video)
        pts, time_base = await self.next_timestamp()

        # Lấy frame hiện tại (bản sao để tránh xung đột bộ nhớ)
        img = self.current_frame.copy()

        # Chuyển đổi ma trận Numpy BGR (OpenCV) sang định dạng VideoFrame của PyAV
        frame = VideoFrame.from_ndarray(img, format="bgr24")
        
        # Gắn mốc thời gian
        frame.pts = pts
        frame.time_base = time_base

        return frame