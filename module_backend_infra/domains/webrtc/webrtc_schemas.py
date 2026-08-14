# domains/webrtc/webrtc_schemas.py
from pydantic import BaseModel
from typing import List, Optional, Union

class IceServerConfig(BaseModel):
    urls: Union[str, List[str]]
    username: Optional[str] = None
    credential: Optional[str] = None

class IceServersResponse(BaseModel):
    iceServers: List[IceServerConfig]