# domains/webrtc/webrtc_controller.py
from fastapi import APIRouter, Depends
from domains.auth.dependencies import get_current_user
from domains.auth.auth_models import User
from . import webrtc_schemas
from .webrtc_service import WebRTCService

router = APIRouter(prefix="/api/webrtc", tags=["WebRTC"])

@router.get("/ice-servers", response_model=webrtc_schemas.IceServersResponse)
def get_ice_servers(current_user: User = Depends(get_current_user)):
    """
    Cấp phát danh sách ICE Servers (STUN/TURN) kèm thông tin xác thực động (Time-limited credentials)
    để thiết lập luồng stream video P2P.
    """
    servers = WebRTCService.get_ice_servers(user_id=str(current_user.id))
    return webrtc_schemas.IceServersResponse(iceServers=servers)