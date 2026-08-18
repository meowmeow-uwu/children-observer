from module_edge_firmware.rtsp_utils import redact_rtsp_url


def test_rtsp_log_url_redacts_credentials() -> None:
    value = "rtsp://admin:secret%23value@192.168.2.106:554/cam/realmonitor?channel=1"

    safe = redact_rtsp_url(value)

    assert "secret" not in safe
    assert safe == (
        "rtsp://<credentials-redacted>@192.168.2.106:554/cam/realmonitor?channel=1"
    )

