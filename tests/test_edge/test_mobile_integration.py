import json
import socket
from types import SimpleNamespace

from module_edge_firmware.feedback_accuracy import AccuracyFeedbackTracker
from module_edge_firmware.mobile_gateway import MobileGateway


def _read_json_line(sock: socket.socket) -> dict:
    data = b""
    while not data.endswith(b"\n"):
        data += sock.recv(4096)
    return json.loads(data.decode("utf-8"))


def test_mobile_gateway_handles_json_commands():
    def handler(message):
        if message["type"] == "ping":
            return {"ok": True, "type": "pong"}
        return {"ok": False}

    gateway = MobileGateway("127.0.0.1", 0, handler)
    gateway.start()
    host, port = gateway.address

    try:
        with socket.create_connection((host, port), timeout=2) as sock:
            sock.sendall(b'{"type":"ping"}\n')
            assert _read_json_line(sock) == {"ok": True, "type": "pong"}
    finally:
        gateway.stop()


def test_feedback_tracker_records_accuracy(tmp_path):
    tracker = AccuracyFeedbackTracker(output_dir=tmp_path)
    alert = SimpleNamespace(
        to_dict=lambda: {
            "alert_id": "alert_000001",
            "risk_level": "high",
            "reasons": ["roi intrusion"],
        }
    )

    tracker.register_alert(alert)
    summary = tracker.submit_feedback("alert_000001", is_correct=False, correct_label="normal")

    assert summary["total_feedback"] == 1
    assert summary["correct_feedback"] == 0
    assert summary["accuracy"] == 0.0
    assert list(tmp_path.glob("edge_feedback_*.jsonl"))
