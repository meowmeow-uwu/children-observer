import asyncio
import json
import logging

import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

from module_edge_firmware.webrtc.video_track import AIVideoTrack, SharedFrameSource

logger = logging.getLogger("EdgeWebRTC")
logging.basicConfig(level=logging.INFO)


class EdgeWebRTCClient:
    """Edge WebRTC client: signaling + trả lời offer + video track + data channel.

    Mỗi PeerConnection tạo một AIVideoTrack mới — track mới giữ frame source,
    FPS, clock start_time và có stream_id/origin riêng (clone không làm mất
    stream origin).
    """

    def __init__(
        self,
        signaling_url: str,
        client_id: str,
        video_track,
        channel_handler=None,
        session_prepare_handler=None,
    ):
        self.signaling_url = f"{signaling_url}/{client_id}"
        self.client_id = client_id
        self.channel_handler = channel_handler
        self.session_prepare_handler = session_prepare_handler

        # Lưu trữ nguồn frame + clock gốc để mỗi PC clone track đúng
        if isinstance(video_track, AIVideoTrack):
            self.frame_source = video_track.frame_source
            self._start_time = video_track._start
            self._fps = video_track._fps
        else:
            self.frame_source = video_track
            self._start_time = None
            self._fps = 30

        self.pc: RTCPeerConnection | None = None
        self.websocket = None
        self._data_channel = None

    async def create_peer_connection(self):
        """Đảm bảo đóng kết nối cũ nếu có trước khi tạo kết nối mới."""
        if self.pc is not None:
            try:
                await self.pc.close()
            except Exception:
                pass
            self.pc = None

        # Chặn tạo media track cho tới khi nguồn đã seek xong và frame đầu của
        # loop mới thực sự tồn tại. Đây là ranh giới session khi hard refresh.
        if self.session_prepare_handler:
            await asyncio.to_thread(self.session_prepare_handler)

        self.pc = RTCPeerConnection()

        # Track mới cho mỗi PeerConnection — giữ clock/origin của pipeline
        new_track = AIVideoTrack(
            frame_source=self.frame_source,
            start_time=self._start_time,
            fps=self._fps,
        )
        self.pc.addTrack(new_track)

        # Data channel "detections" do browser (offerer) tạo → bắt sự kiện.
        # Channel được gắn đúng PeerConnection hiện tại + stream_id của track này.
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(
                f"DataChannel received: label={channel.label} state={channel.readyState} "
                f"stream_id={new_track.stream_id}"
            )
            self._data_channel = channel
            if self.channel_handler:
                self.channel_handler(channel, new_track.stream_id, new_track.origin_ms)

        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            if self.pc:
                logger.info(f"ICE Connection State: {self.pc.iceConnectionState}")
                if self.pc.iceConnectionState in ["failed", "closed"]:
                    try:
                        await self.pc.close()
                    except Exception:
                        pass

    async def handle_signaling_message(self, message: dict):
        msg_type = message.get("type")
        sender = message.get("sender")  # ID của Web Client (trình duyệt phụ huynh)

        if msg_type == "offer":
            logger.info(f"Nhận được SDP Offer từ {sender}")
            await self.create_peer_connection()

            offer = RTCSessionDescription(sdp=message["sdp"], type=message["type"])
            await self.pc.setRemoteDescription(offer)

            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)

            response = {
                "type": "answer",
                "target": sender,
                "sdp": self.pc.localDescription.sdp,
            }
            await self.websocket.send(json.dumps(response))

        elif msg_type == "candidate":
            candidate_info = message.get("candidate")
            if candidate_info and self.pc:
                candidate = RTCIceCandidate(
                    sdpMid=candidate_info["sdpMid"],
                    sdpMLineIndex=candidate_info["sdpMLineIndex"],
                    candidate=candidate_info["candidate"],
                )
                await self.pc.addIceCandidate(candidate)

    async def connect(self):
        """Kết nối signaling server với vòng lặp reconnect tự động."""
        logger.info(f"Đang kết nối Signaling Server: {self.signaling_url}")
        while True:
            try:
                async with websockets.connect(self.signaling_url) as websocket:
                    self.websocket = websocket
                    logger.info("Đã kết nối Signaling Server thành công. Đang chờ luồng từ Web...")
                    try:
                        async for message_str in websocket:
                            message = json.loads(message_str)
                            await self.handle_signaling_message(message)
                    except websockets.ConnectionClosed:
                        logger.warning("Mất kết nối tới Signaling Server.")
            except Exception as exc:
                logger.warning(f"Signaling connect error: {exc}")
            logger.info("Thử kết nối lại Signaling Server sau 3s...")
            await asyncio.sleep(3.0)
