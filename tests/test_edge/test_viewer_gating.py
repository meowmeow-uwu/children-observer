"""Viewer lifecycle của demo: không viewer thì không decode/inference/alert."""

from module_edge_firmware.demo_stream.pipeline import DemoStreamConfig, DemoStreamPipeline


class FakeDataChannel:
    def __init__(self, ready_state: str = "connecting") -> None:
        self.label = "detections"
        self.readyState = ready_state
        self._handlers = {}

    def on(self, event, handler):
        self._handlers[event] = handler

    def emit(self, event):
        self.readyState = "open" if event == "open" else "closed"
        self._handlers[event]()


def _pipeline() -> DemoStreamPipeline:
    return DemoStreamPipeline(
        DemoStreamConfig(
            camera_id="camera_test",
            ws_relay_enabled=False,
            viewer_gated=True,
        )
    )


def test_demo_starts_only_after_data_channel_is_open():
    pipeline = _pipeline()
    channel = FakeDataChannel()

    assert not pipeline._viewer_active.is_set()
    assert not pipeline.source._active.is_set()

    pipeline.set_channel(channel, "stream-test", lambda: None)
    assert not pipeline._viewer_active.is_set()

    channel.emit("open")
    assert pipeline._viewer_active.is_set()
    assert pipeline.source._active.is_set()
    assert pipeline._streams[channel]["active"] is True


def test_last_viewer_close_pauses_demo_and_drops_queued_alerts():
    pipeline = _pipeline()
    channel = FakeDataChannel(ready_state="open")
    pipeline.set_channel(channel, "stream-test", lambda: None)
    pipeline._alert_queue.put_nowait(object())

    channel.emit("close")

    assert not pipeline._viewer_active.is_set()
    assert not pipeline.source._active.is_set()
    assert channel not in pipeline._streams
    assert pipeline._alert_queue.empty()


def test_replacement_viewer_restarts_demo_before_old_channel_closes(monkeypatch):
    """Hard refresh có thể mở channel mới trong lúc channel cũ còn active."""
    pipeline = _pipeline()
    restart_calls = 0

    def count_restart():
        nonlocal restart_calls
        restart_calls += 1

    monkeypatch.setattr(pipeline.source, "restart", count_restart)

    old_channel = FakeDataChannel(ready_state="open")
    pipeline.set_channel(old_channel, "stream-old", lambda: None)
    assert restart_calls == 1

    new_channel = FakeDataChannel(ready_state="open")
    pipeline.set_channel(new_channel, "stream-new", lambda: None)

    assert restart_calls == 2
    assert pipeline._streams[old_channel]["active"] is True
    assert pipeline._streams[new_channel]["active"] is True


def test_prepared_session_does_not_restart_again_when_channel_opens(monkeypatch):
    """Barrier offer→frame đầu chỉ chạy một lần, DataChannel không seek lại."""
    pipeline = _pipeline()
    prepare_calls = 0
    fallback_restart_calls = 0

    def prepared_restart():
        nonlocal prepare_calls
        prepare_calls += 1
        return True

    def fallback_restart():
        nonlocal fallback_restart_calls
        fallback_restart_calls += 1

    monkeypatch.setattr(pipeline.source, "restart_and_wait", prepared_restart)
    monkeypatch.setattr(pipeline.source, "restart", fallback_restart)

    pipeline.prepare_viewer_session()
    channel = FakeDataChannel(ready_state="open")
    pipeline.set_channel(channel, "stream-prepared", lambda: None)

    assert prepare_calls == 1
    assert fallback_restart_calls == 0
    assert pipeline._prepared_sessions == 0
