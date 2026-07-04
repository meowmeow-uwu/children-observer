import asyncio
import json
import logging
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

logger = logging.getLogger("EdgeWebRTC")
logging.basicConfig(level=logging.INFO)

class EdgeWebRTCClient:
    def __init__(self, signaling_url: str, client_id: str, video_track):
        self.signaling_url = f"{signaling_url}/{client_id}"
        self.client_id = client_id
        self.video_track = video_track
        self.pc = None # RTCPeerConnection object
        self.websocket = None

    async def create_peer_connection(self):
        # STUN server giúp thiết bị vượt qua router NAT để tìm IP Public
        self.pc = RTCPeerConnection()
        
        # Gắn luồng Video từ AI vào PeerConnection
        self.pc.addTrack(self.video_track)

        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"ICE Connection State: {self.pc.iceConnectionState}")
            if self.pc.iceConnectionState == "failed":
                await self.pc.close()

    async def handle_signaling_message(self, message: dict):
        msg_type = message.get("type")
        sender = message.get("sender") # ID của Web Client (trình duyệt của phụ huynh)

        if msg_type == "offer":
            logger.info(f"Nhận được SDP Offer từ {sender}")
            await self.create_peer_connection()
            
            # Cài đặt SDP Offer của đối tác
            offer = RTCSessionDescription(sdp=message["sdp"], type=message["type"])
            await self.pc.setRemoteDescription(offer)
            
            # Tạo SDP Answer
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            # Gửi Answer ngược lại cho Web Client thông qua Signaling Server
            response = {
                "type": "answer",
                "target": sender,
                "sdp": self.pc.localDescription.sdp
            }
            await self.websocket.send(json.dumps(response))

        elif msg_type == "candidate":
            # Xử lý ICE Candidate (các tuyến đường kết nối mạng)
            candidate_info = message.get("candidate")
            if candidate_info:
                candidate = RTCIceCandidate(
                    sdpMid=candidate_info["sdpMid"],
                    sdpMLineIndex=candidate_info["sdpMLineIndex"],
                    candidate=candidate_info["candidate"]
                )
                await self.pc.addIceCandidate(candidate)

    async def connect(self):
        logger.info(f"Đang kết nối Signaling Server: {self.signaling_url}")
        async for websocket in websockets.connect(self.signaling_url):
            self.websocket = websocket
            logger.info("Đã kết nối Signaling Server thành công. Đang chờ luồng từ Web...")
            try:
                async for message_str in websocket:
                    message = json.loads(message_str)
                    await self.handle_signaling_message(message)
            except websockets.ConnectionClosed:
                logger.warning("Mất kết nối tới Signaling Server. Sẽ thử kết nối lại...")
                continue