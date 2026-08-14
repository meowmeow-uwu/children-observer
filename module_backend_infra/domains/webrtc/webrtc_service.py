# domains/webrtc/webrtc_service.py
import time
import hmac
import hashlib
import base64
from typing import List
from core.config import settings
from .webrtc_schemas import IceServerConfig

class WebRTCService:
    @staticmethod
    def get_ice_servers(user_id: str) -> List[IceServerConfig]:
        # 1. Luôn luôn cấp phát STUN Server miễn phí của Google (Dùng khi mạng mở)
        servers = [
            IceServerConfig(urls="stun:stun.l.google.com:19302")
        ]
        
        # 2. Cấp phát TURN Server (Dùng khi mạng 4G/Tường lửa chặn P2P)
        if settings.TURN_SERVER_URL and settings.TURN_SERVER_SECRET:
            # Token chỉ có hiệu lực trong 24 giờ (86400 giây)
            ttl = 86400 
            timestamp = int(time.time()) + ttl
            
            # Cấu trúc username chuẩn của Coturn: <timestamp>:<định_danh>
            username = f"{timestamp}:user_{user_id}"
            
            # Tạo mật khẩu HMAC-SHA1
            mac = hmac.new(
                settings.TURN_SERVER_SECRET.encode('utf-8'),
                username.encode('utf-8'),
                hashlib.sha1
            )
            credential = base64.b64encode(mac.digest()).decode('utf-8')
            
            # Gắn vào danh sách
            servers.append(
                IceServerConfig(
                    urls=settings.TURN_SERVER_URL,
                    username=username,
                    credential=credential
                )
            )
            
        return servers