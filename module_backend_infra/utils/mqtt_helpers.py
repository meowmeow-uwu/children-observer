def build_device_topic(device_id: str, subtopic: str) -> str:
    """
    Tạo chuỗi MQTT topic chuẩn hoá dạng: devices/{device_id}/{subtopic}
    """
    clean_device_id = device_id.strip("/")
    clean_subtopic = subtopic.strip("/")
    return f"devices/{clean_device_id}/{clean_subtopic}"
