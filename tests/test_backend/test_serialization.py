"""
Tests cho serialization JSON-safe (root cause của lỗi float32 crash).
"""

import json

import numpy as np

from module_edge_firmware.demo_stream.detector import to_json_safe


def test_numpy_float32_becomes_python_float():
    value = to_json_safe(np.float32(0.5))
    assert isinstance(value, float)
    json.dumps(value)


def test_numpy_array_becomes_list():
    value = to_json_safe(np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert isinstance(value, list)
    json.dumps(value)


def test_nested_dict_with_numpy_values():
    payload = {
        "box": [
            round(float(v), 4)
            for v in (np.float32(0.1), np.float32(0.2), np.float32(0.3), np.float32(0.4))
        ],
        "confidence": np.float32(0.57),
        "track_id": np.int64(12),
    }
    dumped = json.dumps(to_json_safe(payload))
    assert (
        dumped == '{"box": [0.1, 0.2, 0.3, 0.4], "confidence": 0.5699999928474426, "track_id": 12}'
    )


def test_rounded_values_serialize_cleanly():
    """Payload thực tế đã round bằng float() → JSON sạch không nhiễu float32."""
    payload = {
        "confidence": round(float(np.float32(0.57)), 3),
        "box": [
            round(float(v), 4)
            for v in (np.float32(0.1), np.float32(0.2), np.float32(0.3), np.float32(0.4))
        ],
    }
    dumped = json.dumps(to_json_safe(payload))
    assert dumped == '{"confidence": 0.57, "box": [0.1, 0.2, 0.3, 0.4]}'


def test_detector_output_is_json_safe():
    """Output của detector (numpy raw) phải serialize được qua to_json_safe."""
    det = {
        "box": (
            round(np.float32(0.1), 4),
            round(np.float32(0.2), 4),
            round(np.float32(0.3), 4),
            round(np.float32(0.4), 4),
        ),
        "class": "child",
        "score": round(np.float32(0.6), 3),
    }
    # round() trên numpy.float32 vẫn trả về numpy.float32 — root cause cũ
    assert isinstance(det["box"][0], np.floating)
    json.dumps(to_json_safe(det))
