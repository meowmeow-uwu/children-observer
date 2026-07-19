import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription

async def simulate_web_client():
    # Kết nối vào Backend (đóng vai Web của Phụ huynh)
    uri = "ws://localhost:8007/ws/signaling/web_parent_01"
    
    async with websockets.connect(uri) as websocket:
        print("🌐 [Web Fake] Đã kết nối tới Signaling Server")
        
        # Tạo PeerConnection thực tế để thương lượng đúng chuẩn SDP
        pc = RTCPeerConnection()
        
        # Chỉ nhận video (giả lập Web Client chỉ xem camera)
        pc.addTransceiver("video", direction="recvonly")
        
        # Tạo SDP Offer thực tế
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        # 1. Gửi gói tin SDP Offer thực tế tới Camera
        offer_msg = {
            "type": "offer",
            "target": "camera_living_room_01", # ID của Edge client trong pipeline.py
            "sdp": pc.localDescription.sdp
        }
        
        print(f"🌐 [Web Fake] Đang gửi yêu cầu xem camera tới: {offer_msg['target']}")
        await websocket.send(json.dumps(offer_msg))
        
        # 2. Lắng nghe phản hồi từ Camera
        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"❄️ [Web Fake] Trạng thái ICE: {pc.iceConnectionState}")
            
        @pc.on("track")
        def on_track(track):
            print(f"📺 [Web Fake] Đã nhận được track video: {track.kind}")
            
        while True:
            response_str = await websocket.recv()
            response = json.loads(response_str)
            
            print(f"\n📩 [Web Fake] Nhận được tin nhắn từ: {response.get('sender')}")
            print(f"   Loại tin nhắn (Type): {response.get('type')}")
            
            if response.get('type') == 'answer':
                # Gán SDP Answer từ Camera
                answer = RTCSessionDescription(sdp=response['sdp'], type='answer')
                await pc.setRemoteDescription(answer)
                print("✅ THÀNH CÔNG! Đã nhận được SDP Answer từ Edge. Bắt tay WebRTC hoàn tất!")
                break
        
        # Đợi 5 giây để luồng WebRTC thực hiện kết nối/truyền tải trước khi đóng
        print("⏳ [Web Fake] Đang duy trì kết nối trong 5 giây...")
        await asyncio.sleep(5)
        
        # Đóng PeerConnection sau khi hoàn thành mô phỏng
        print("🔌 [Web Fake] Đang đóng kết nối...")
        await pc.close()

if __name__ == "__main__":
    asyncio.run(simulate_web_client())