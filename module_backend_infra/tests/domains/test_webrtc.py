# tests/domains/test_webrtc.py
def test_get_ice_servers_unauthorized(client):
    """Bắt lỗi không có Token JWT khi lấy ICE Servers."""
    response = client.get("/api/webrtc/ice-servers")
    assert response.status_code == 401

def test_get_ice_servers_success(client, auth_headers):
    """Kiểm tra API cấp phát STUN/TURN server thành công."""
    response = client.get("/api/webrtc/ice-servers", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "iceServers" in data
    assert isinstance(data["iceServers"], list)
    
    # Ít nhất phải có 1 STUN server của Google được cấp
    urls = []
    for server in data["iceServers"]:
        if isinstance(server["urls"], str):
            urls.append(server["urls"])
        elif isinstance(server["urls"], list):
            urls.extend(server["urls"])
            
    assert any("stun.l.google.com" in url for url in urls)