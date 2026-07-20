import asyncio
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

class SharedFrameSource:
    """
    Nơi lưu trữ khung hình mới nhất dùng chung cho nhiều kết nối WebRTC.
    """
    def __init__(self):
        self.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def update_frame(self, frame: np.ndarray):
        self.current_frame = frame

class AIVideoTrack(VideoStreamTrack):
    """
    Class này có nhiệm vụ lấy khung hình đã qua xử lý AI (Numpy Array BGR) 
    và đóng gói thành chuẩn WebRTC (YUV/RGB) để truyền đi.
    """
    def __init__(self, frame_source=None):
        super().__init__()
        if frame_source is None:
            self.frame_source = SharedFrameSource()
        else:
            self.frame_source = frame_source

    def update_frame(self, frame: np.ndarray):
        if hasattr(self.frame_source, 'update_frame'):
            self.frame_source.update_frame(frame)
        elif hasattr(self.frame_source, 'current_frame'):
            self.frame_source.current_frame = frame

    async def recv(self) -> VideoFrame:
        """
        Hàm cốt lõi của aiortc. WebRTC sẽ gọi hàm này liên tục để lấy frame đẩy lên mạng.
        """
        pts, time_base = await self.next_timestamp()

        # Lấy frame hiện tại từ frame_source
        if hasattr(self.frame_source, 'current_frame'):
            img = self.frame_source.current_frame.copy()
        else:
            img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Chuyển đổi ma trận Numpy BGR (OpenCV) sang định dạng VideoFrame của PyAV
        frame = VideoFrame.from_ndarray(img, format="bgr24")
        
        # Gắn mốc thời gian
        frame.pts = pts
        frame.time_base = time_base

        return frame