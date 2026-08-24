"""
DemoStreamPipeline — một tiến trình duy nhất sở hữu VideoCapture + ONNX + ByteTrack.

Luồng dữ liệu:

    DemoVideoSource (thread, clock monotonic thật, loop an toàn)
        └── FrameStore (latest-frame, maxsize=1)
              ├── AIVideoTrack (WebRTC video, per-PC stream_id/origin)
              └── Detection thread (sampling theo detection_fps)
                     → ONNX → ByteTrack (frame_rate=detection_fps)
                     → RoiStateEngine (hysteresis + cooldown, confirmed-only)
                          ├── tracks message ──► DataChannel + relay WS → Frontend
                          └── AlertEvent ──► alert queue worker → BackendSync POST

Wire contract: schema_version=1, snake_case, stream_id + source_time_ms
(clock monotonic pipeline, tăng liên tục qua mọi loop).
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from module_edge_firmware.demo_stream.backend_sync import BackendSync
from module_edge_firmware.demo_stream.detector import OnnxDetector
from module_edge_firmware.demo_stream.fall import FallStateEngine, FallWorker
from module_edge_firmware.demo_stream.frame_source import DemoVideoSource, FrameStore, RtspVideoSource
from module_edge_firmware.demo_stream.roi_engine import AlertEvent, RoiStateEngine
from module_edge_firmware.demo_stream.tracker import ByteTrackAdapter
from module_edge_firmware.mqtt_client import EdgeMqttClient

VIDEO_DEFAULT_PATH = Path("module_edge_firmware/test_video.mp4")
MODEL_DEFAULT_PATH = Path("weights/roi_detection/best.onnx")

SCHEMA_VERSION = 1


@dataclass
class DemoStreamConfig:
    camera_id: str = "camera_living_room_01"
    signaling_url: str = "ws://127.0.0.1:8007/ws/signaling"
    backend_url: str = "http://127.0.0.1:8007"
    rtsp_url: str | None = None
    video_path: Path = VIDEO_DEFAULT_PATH
    model_path: Path = MODEL_DEFAULT_PATH
    detection_fps: float = 12.0
    conf_threshold: float = 0.05
    track_thresh: float = 0.35
    track_buffer: int = 360
    track_match_thresh: float = 0.8
    roi_poll_seconds: float = 5.0
    alert_cooldown_seconds: float = 5.0
    fall_enabled: bool = False
    fall_model_path: Path = Path("weights/fall_detection/best-416.onnx")
    fall_fps: float = 2.0
    fall_conf_threshold: float = 0.50
    fall_still_seconds: float = 2.0
    fall_cooldown_seconds: float = 30.0
    fall_velocity_threshold: float = 0.15
    fall_still_velocity_threshold: float = 0.04
    fall_input_size: int = 416
    fall_publish_alerts: bool = True
    fall_metrics_path: Path = Path("/var/lib/children-observer/fall-metrics.jsonl")
    # Production contract in task_edge_firmware_integration.md.
    mqtt_enabled: bool = True
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    # REST is only a compatibility fallback for the previous web demo.
    rest_sync_enabled: bool = False
    ws_relay_enabled: bool = True
    ws_relay_url: str = "ws://127.0.0.1:8007/ws/detections/edge"
    heartbeat_seconds: float = 1.0
    frame_rate: int = 30
    # Demo web: chỉ decode/inference/cảnh báo khi DataChannel viewer đã open.
    viewer_gated: bool = True
    # Web demo mặc định phát toàn bộ file từ frame 0. Có thể giới hạn đoạn
    # bằng EDGE_DEMO_START_SECONDS/EDGE_DEMO_END_SECONDS khi benchmark model.
    start_seconds: float | None = 0.0
    end_seconds: float | None = None
    extra: dict = field(default_factory=dict)


def build_config_from_settings() -> DemoStreamConfig:
    """Lấy cấu hình demo từ biến môi trường EDGE_* (mặc định cho localhost).

    KHÔNG phụ thuộc configs.settings.AppSettings (yêu cầu .env với nhiều field
    training không liên quan demo) để chạy được trong Docker image gọn.
    """

    def env_float(name: str, default: str) -> float:
        return float(os.getenv(name, default))

    def env_int(name: str, default: str) -> int:
        return int(os.getenv(name, default))

    def env_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() not in {"0", "false", "no", "off"}

    start_s = os.getenv("EDGE_DEMO_START_SECONDS")
    end_s = os.getenv("EDGE_DEMO_END_SECONDS")
    return DemoStreamConfig(
        camera_id=os.getenv("EDGE_CAMERA_ID", "camera_living_room_01"),
        signaling_url=os.getenv(
            "EDGE_SIGNALING_URL", "ws://127.0.0.1:8007/ws/signaling"
        ),
        backend_url=os.getenv("EDGE_BACKEND_URL", "http://127.0.0.1:8007"),
        rtsp_url=os.getenv("EDGE_RTSP_URL") or None,
        video_path=Path(os.getenv("EDGE_VIDEO_PATH", str(VIDEO_DEFAULT_PATH))),
        model_path=Path(os.getenv("EDGE_MODEL_PATH", str(MODEL_DEFAULT_PATH))),
        detection_fps=env_float("EDGE_DETECTION_FPS", "12.0"),
        conf_threshold=env_float("EDGE_CONF_THRESHOLD", "0.05"),
        track_thresh=env_float("EDGE_TRACK_THRESH", "0.35"),
        track_buffer=env_int("EDGE_TRACK_BUFFER", "360"),
        track_match_thresh=env_float("EDGE_TRACK_MATCH_THRESH", "0.8"),
        viewer_gated=env_bool("EDGE_VIEWER_GATED", True),
        roi_poll_seconds=env_float("EDGE_ROI_POLL_SECONDS", "5.0"),
        alert_cooldown_seconds=env_float("EDGE_ALERT_COOLDOWN_SECONDS", "5.0"),
        fall_enabled=env_bool("EDGE_FALL_ENABLED", False),
        fall_model_path=Path(os.getenv("EDGE_FALL_MODEL_PATH", "weights/fall_detection/best-416.onnx")),
        fall_fps=env_float("EDGE_FALL_FPS", "2.0"),
        fall_conf_threshold=env_float("EDGE_FALL_CONF_THRESHOLD", "0.50"),
        fall_still_seconds=env_float("EDGE_FALL_STILL_SECONDS", "2.0"),
        fall_cooldown_seconds=env_float("EDGE_FALL_COOLDOWN_SECONDS", "30.0"),
        fall_velocity_threshold=env_float("EDGE_FALL_VELOCITY_THRESHOLD", "0.15"),
        fall_still_velocity_threshold=env_float("EDGE_FALL_STILL_VELOCITY_THRESHOLD", "0.04"),
        fall_input_size=env_int("EDGE_FALL_INPUT_SIZE", "416"),
        fall_publish_alerts=env_bool("EDGE_FALL_PUBLISH_ALERTS", True),
        fall_metrics_path=Path(os.getenv("EDGE_FALL_METRICS_PATH", "/var/lib/children-observer/fall-metrics.jsonl")),
        mqtt_enabled=env_bool("EDGE_MQTT_ENABLED", True),
        mqtt_host=os.getenv("MQTT_BROKER_HOST", "127.0.0.1"),
        mqtt_port=env_int("MQTT_BROKER_PORT", "1883"),
        mqtt_username=os.getenv("MQTT_USERNAME") or None,
        mqtt_password=os.getenv("MQTT_PASSWORD") or None,
        rest_sync_enabled=env_bool("EDGE_REST_SYNC_ENABLED", False),
        ws_relay_enabled=env_bool("EDGE_WS_RELAY_ENABLED", True),
        ws_relay_url=os.getenv(
            "EDGE_WS_RELAY_URL", "ws://127.0.0.1:8007/ws/detections/edge"
        ),
        frame_rate=env_int("EDGE_WEBRTC_FPS", "30"),
        start_seconds=float(start_s) if start_s is not None else 0.0,
        end_seconds=float(end_s) if end_s else None,
    )


class DemoStreamPipeline:
    """Orchestrator của pipeline demo — sở hữu toàn bộ tài nguyên AI/video."""

    def __init__(self, config: DemoStreamConfig | None = None):
        self.config = config or build_config_from_settings()
        # Đồng hồ monotonic dùng chung cho FrameSource + AIVideoTrack
        self.start_time = time.monotonic()
        self.pipeline_stream_id = f"pipeline-{uuid.uuid4().hex[:8]}"

        self.store = FrameStore()
        source_kwargs = {
            "frame_store": self.store,
            "start_time": self.start_time,
            "initial_active": not self.config.viewer_gated,
        }
        self.source = (
            RtspVideoSource(self.config.rtsp_url, **source_kwargs)
            if self.config.rtsp_url
            else DemoVideoSource(
                self.config.video_path,
                start_seconds=self.config.start_seconds,
                end_seconds=self.config.end_seconds,
                **source_kwargs,
            )
        )
        self.detector = OnnxDetector(
            self.config.model_path,
            conf_threshold=self.config.conf_threshold,
        )
        self.tracker = ByteTrackAdapter(
            track_thresh=self.config.track_thresh,
            track_buffer=self.config.track_buffer,
            match_thresh=self.config.track_match_thresh,
            frame_rate=int(round(self.config.detection_fps)),
            classes_to_track=("child",),
            high_thresh=0.15,
            low_thresh=0.05,
            new_thresh=0.1,
            confirm_frames=2,
            confirm_score=0.35,
        )
        self.engine = RoiStateEngine(
            camera_id=self.config.camera_id,
            cooldown_seconds=self.config.alert_cooldown_seconds,
        )
        self.backend = (
            BackendSync(
                backend_url=self.config.backend_url,
                camera_id=self.config.camera_id,
                poll_interval=self.config.roi_poll_seconds,
                on_roi_update=self.engine.set_zones,
                on_pause_change=self.engine.set_paused,
                on_camera_meta=lambda name: self._set_camera_name(name),
            )
            if self.config.rest_sync_enabled
            else None
        )
        self.mqtt: EdgeMqttClient | None = None
        self.fall_worker = (
            FallWorker(
                camera_id=self.config.camera_id,
                model_path=self.config.fall_model_path,
                conf_threshold=self.config.fall_conf_threshold,
                input_size=self.config.fall_input_size,
                fps=self.config.fall_fps,
                state_engine=FallStateEngine(
                    still_seconds=self.config.fall_still_seconds,
                    velocity_threshold=self.config.fall_velocity_threshold,
                    still_velocity_threshold=self.config.fall_still_velocity_threshold,
                    cooldown_seconds=self.config.fall_cooldown_seconds,
                ),
                metrics_path=self.config.fall_metrics_path,
            )
            if self.config.fall_enabled
            else None
        )

        # Outbox thread-safe: detection/status messages → async sender
        self.outbox: queue.Queue[dict] = queue.Queue(maxsize=64)
        # Alert queue bounded + worker (POST không block inference thread)
        self._alert_queue: queue.Queue[tuple[Any, bytes | None] | None] = queue.Queue(maxsize=64)
        self._alert_worker: threading.Thread | None = None

        # Per-PeerConnection stream identity: channel → {stream_id, origin_getter}
        self._streams: dict[Any, dict] = {}
        self._viewer_active = threading.Event()
        self._session_prepare_lock = threading.Lock()
        self._prepared_sessions = 0
        if not self.config.viewer_gated:
            self._viewer_active.set()
        self._camera_name = ""

        self._stop = threading.Event()
        self._running = False
        self._detection_thread: threading.Thread | None = None
        self._heartbeat_state = "initializing"
        self._latency_ms = 0.0
        self._last_frame_id = 0
        self._last_track_count = 0
        self._last_pts_ms = 0.0
        self._last_loop_id_beat = 0
        self._alert_count = 0
        self._relay_ws = None
        self._last_published_camera_online: bool | None = None

    def _set_camera_name(self, name: str) -> None:
        if name and name != self._camera_name:
            self._camera_name = name

    def attach_mqtt(self, mqtt: EdgeMqttClient) -> None:
        """Attach the shared MQTT transport before the pipeline starts."""
        self.mqtt = mqtt

    # ---- WebRTC attach ----
    def prepare_viewer_session(self) -> None:
        """Barrier gọi lúc nhận offer, trước khi tạo AIVideoTrack mới."""
        if not self.config.viewer_gated:
            return
        with self._session_prepare_lock:
            self._drain_queue(self.outbox)
            self._drain_queue(self._alert_queue)
            if self.fall_worker:
                self.fall_worker.reset()
            if not self.source.restart_and_wait():
                raise RuntimeError("Không thể tua video về đầu đoạn demo")
            self._prepared_sessions += 1
            self._heartbeat_state = "initializing"
            self._last_track_count = 0
            logger.info("Viewer session prepared at demo segment start")

    def set_channel(self, channel, stream_id: str | None = None, origin_getter: Callable[[], float | None] | None = None) -> None:
        """Gắn RTCDataChannel cho một PeerConnection với stream_id riêng.

        Mỗi viewer có stream_id/origin riêng; viewer mới không lấy channel cũ.
        """
        self._streams[channel] = {
            "stream_id": stream_id or self.pipeline_stream_id,
            "origin_ms": None,
            "origin_getter": origin_getter or (lambda: None),
            "sync_sent": False,
            "active": False,
        }
        if hasattr(channel, "on"):
            channel.on("open", lambda: self._activate_channel(channel))
            channel.on("close", lambda: self.remove_channel(channel))
        if getattr(channel, "readyState", "") == "open":
            self._activate_channel(channel)
        logger.info(
            f"DataChannel attached: {getattr(channel, 'label', '?')} "
            f"stream_id={self._streams[channel]['stream_id']}"
        )

    def _activate_channel(self, channel) -> None:
        info = self._streams.get(channel)
        if info is None or info["active"]:
            return
        first_viewer = not self._viewer_active.is_set()
        info["active"] = True
        self._viewer_active.set()
        if self.config.viewer_gated:
            # Luồng chuẩn đã được prepare trước khi AIVideoTrack được tạo.
            # Giữ fallback cho consumer cũ/test gọi set_channel trực tiếp.
            with self._session_prepare_lock:
                was_prepared = self._prepared_sessions > 0
                if was_prepared:
                    self._prepared_sessions -= 1
            if not was_prepared:
                self._drain_queue(self.outbox)
                self.source.restart()
                self.source.set_active(True)
                self._heartbeat_state = "initializing"
            logger.info(
                "WebRTC viewer session started at prepared segment origin"
                if was_prepared
                else "WebRTC viewer session started — fallback restart"
                if first_viewer
                else "Replacement WebRTC viewer connected — fallback restart"
            )

    def remove_channel(self, channel) -> None:
        self._streams.pop(channel, None)
        if self.config.viewer_gated and not any(info["active"] for info in self._streams.values()):
            self._viewer_active.clear()
            self.source.set_active(False)
            self._drain_queue(self.outbox)
            self._drain_queue(self._alert_queue)
            self._heartbeat_state = "initializing"
            self._last_track_count = 0
            logger.info("Last WebRTC viewer disconnected — demo inference paused")

    @staticmethod
    def _drain_queue(target: queue.Queue) -> None:
        while True:
            try:
                target.get_nowait()
            except queue.Empty:
                return

    # ---- Lifecycle ----
    async def run_async(self) -> None:
        """Chạy toàn bộ pipeline (detection thread + sender + heartbeat + relay WS)."""
        self._running = True
        self._stop.clear()

        self.detector.load()
        if self.fall_worker:
            self.fall_worker.start()
        if self.backend:
            self.backend.start()
        self.source.start()

        self._detection_thread = threading.Thread(
            target=self._detection_loop, name="demo-detection", daemon=True
        )
        self._detection_thread.start()
        self._alert_worker = threading.Thread(
            target=self._alert_worker_loop, name="demo-alert-worker", daemon=True
        )
        self._alert_worker.start()

        relay_task = asyncio.create_task(self._relay_ws_loop()) if self.config.ws_relay_enabled else None
        sender_task = asyncio.create_task(self._sender_loop())
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while not self._stop.is_set():
                await asyncio.sleep(0.5)
        finally:
            self._running = False
            for task in (sender_task, heartbeat_task, relay_task):
                if task:
                    task.cancel()
            await self._shutdown()

    async def _shutdown(self) -> None:
        try:
            self._alert_queue.put_nowait(None)  # sentinel dừng worker
        except queue.Full:
            pass
        self.source.stop()
        if self.fall_worker:
            self.fall_worker.stop()
        if self.backend:
            self.backend.stop()
        if self._detection_thread:
            self._detection_thread.join(timeout=5)
        if self._alert_worker:
            self._alert_worker.join(timeout=5)
        logger.info("DemoStreamPipeline stopped")

    def stop(self) -> None:
        self._stop.set()
        self._running = False

    # ---- Alert worker (không block inference) ----
    def _alert_worker_loop(self) -> None:
        while True:
            try:
                item = self._alert_queue.get(timeout=0.5)
            except queue.Empty:
                if not self._running and self._stop.is_set():
                    return
                continue
            if item is None:
                return
            alert, snapshot_jpeg = item
            is_fall = getattr(alert, "severity", None) is not None
            if self.mqtt:
                self.mqtt.publish_alert_and_snapshot(
                    camera_id=alert.camera_id,
                    title=alert.title if is_fall else f"{alert.title} ({alert.zone_name})",
                    severity=alert.severity if is_fall else ("danger" if alert.rule == "enterZone" else "warning"),
                    roi_name=getattr(alert, "roi_name", getattr(alert, "zone_name", "")),
                    snapshot_jpeg=snapshot_jpeg,
                    notes=getattr(alert, "notes", ""),
                )
            elif self.backend:
                if is_fall:
                    self.backend.post_fall_alert(alert, snapshot_jpeg)
                else:
                    self.backend.post_alert(alert, snapshot_jpeg)
            else:
                logger.warning("Alert dropped: neither MQTT nor REST backend is configured")

    # ---- Detection thread ----
    def _detection_loop(self) -> None:
        last_loop_id = -1
        last_pts_ms = -1.0  # clock video trong LOOP HIỆN TẠI — reset mỗi loop
        interval_ms = 1000.0 / max(1.0, self.config.detection_fps)
        session_active = not self.config.viewer_gated

        while self._running and not self._stop.is_set():
            if self.config.viewer_gated and not self._viewer_active.is_set():
                if session_active:
                    self.tracker.reset()
                    self.engine.reset_tracks()
                    if self.fall_worker:
                        self.fall_worker.reset()
                    session_active = False
                self._heartbeat_state = "initializing"
                time.sleep(0.05)
                continue
            if not session_active:
                last_loop_id = -1
                last_pts_ms = -1.0
                session_active = True

            snap = self.store.snapshot()
            if snap is None or not snap.is_valid:
                if isinstance(self.source, RtspVideoSource) and not self.source.connected:
                    self._heartbeat_state = "offline"
                    self._last_track_count = 0
                time.sleep(0.03)
                continue

            # Vòng lặp video mới → reset tracker + engine state + pacing gate
            if snap.loop_id != last_loop_id:
                last_loop_id = snap.loop_id
                last_pts_ms = -1.0  # QUAN TRỌNG: không để gate kẹt ở loop mới
                self.tracker.reset()
                self.engine.reset_tracks()
                logger.info(f"Video loop #{snap.loop_id} — tracker reset")

            # Pacing theo detection_fps (không tích backlog)
            if snap.source_pts_ms - last_pts_ms < interval_ms * 0.5:
                time.sleep(0.005)
                continue

            start = time.perf_counter()
            try:
                detections = self.detector.detect(snap.frame)
                tracks = self.tracker.update(detections)
                alerts = self.engine.update(tracks, now_ms=snap.source_time_ms)
                if self.fall_worker:
                    self.fall_worker.offer(snap.frame, tracks, snap.source_time_ms, snap.frame_index)
                    self.fall_worker.annotate(tracks)
            except Exception as exc:
                logger.error(f"Detection loop error: {exc}")
                self._heartbeat_state = "error"
                time.sleep(0.5)
                continue

            self._latency_ms = (time.perf_counter() - start) * 1000.0
            last_pts_ms = snap.source_pts_ms
            self._last_frame_id = snap.frame_index
            self._last_track_count = len(tracks)
            self._last_pts_ms = snap.source_pts_ms
            self._last_loop_id_beat = snap.loop_id
            self._heartbeat_state = "tracking" if tracks else "no_objects"

            for alert in alerts:
                self._alert_count += 1
                self._enqueue_alert(alert, snap.frame)
            if self.fall_worker:
                for alert, alert_frame in self.fall_worker.drain_alerts():
                    if self.config.fall_publish_alerts:
                        self._alert_count += 1
                        self._enqueue_alert(alert, alert_frame)

            message = {
                "schema_version": SCHEMA_VERSION,
                "type": "tracks",
                "camera_id": self.config.camera_id,
                "stream_id": self.pipeline_stream_id,
                "sent_at_ms": round(time.monotonic() * 1000.0, 1),
                "frame_id": self._last_frame_id,
                "source_pts_ms": round(snap.source_pts_ms, 1),
                "source_time_ms": round(snap.source_time_ms, 1),
                "loop_id": snap.loop_id,
                "latency_ms": round(self._latency_ms, 1),
                "tracks": tracks,
            }
            try:
                self.outbox.put_nowait(message)
            except queue.Full:
                # Outbox bounded: bỏ message cũ, giữ message mới nhất
                try:
                    self.outbox.get_nowait()
                    self.outbox.put_nowait(message)
                except (queue.Empty, queue.Full):
                    pass

            elapsed = (time.perf_counter() - start) * 1000.0
            time.sleep(max(0.0, (interval_ms - elapsed) / 1000.0))

    def _enqueue_alert(self, alert: Any, frame) -> None:
        # Chụp đúng frame phát sinh rule; queue chỉ giữ JPEG nhỏ, không giữ
        # ndarray 1080p khiến RAM tăng khi backend chậm.
        snapshot_jpeg: bytes | None = None
        try:
            import cv2

            ok, encoded = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
            )
            if ok:
                snapshot_jpeg = encoded.tobytes()
        except Exception as exc:
            logger.warning(f"Snapshot encode failed: {exc}")
        item = (alert, snapshot_jpeg)
        try:
            self._alert_queue.put_nowait(item)
        except queue.Full:
            # Bounded: bỏ alert cũ nhất thay vì chặn inference
            try:
                self._alert_queue.get_nowait()
                self._alert_queue.put_nowait(item)
            except (queue.Empty, queue.Full):
                pass

    # ---- Base message fields ----
    def _base_message(self, msg_type: str) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "type": msg_type,
            "camera_id": self.config.camera_id,
            "sent_at_ms": round(time.monotonic() * 1000.0, 1),
        }

    # ---- Async sender ----
    async def _sender_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.to_thread(self._outbox_get, 0.5)
            except queue.Empty:
                continue
            if msg is None:
                continue
            await self._send_message(msg)

    def _outbox_get(self, timeout: float):
        return self.outbox.get(timeout=timeout)

    async def _send_message(self, msg: dict) -> None:
        try:
            json.dumps(msg)
        except (TypeError, ValueError) as exc:
            logger.warning(f"Message not JSON serializable, dropped: {exc}")
            return

        for channel, info in list(self._streams.items()):
            try:
                if getattr(channel, "readyState", "") != "open":
                    continue
                stamped = self._stamp_for_stream(msg, info)
                channel.send(json.dumps(stamped))
            except Exception as exc:
                logger.warning(f"DataChannel send failed: {exc}")

        ws = self._relay_ws
        if ws is not None:
            try:
                await ws.send(json.dumps(msg))
            except Exception as exc:
                logger.warning(f"Relay WS send failed: {exc}")

    def _stamp_for_stream(self, msg: dict, info: dict) -> dict:
        """Gắn stream_id + gửi stream_sync lần đầu khi origin đã biết."""
        stamped = self._base_message(msg.get("type", "message"))
        stamped.update({k: v for k, v in msg.items() if k != "type"})
        stamped["stream_id"] = info["stream_id"]

        if not info["sync_sent"]:
            origin = info["origin_getter"]()
            if origin is not None:
                info["origin_ms"] = origin
                info["sync_sent"] = True
                sync_msg = self._base_message("stream_sync")
                sync_msg["stream_id"] = info["stream_id"]
                sync_msg["stream_origin_ms"] = round(origin, 1)
                sync_msg["video_fps"] = self.store.video_fps
                return sync_msg
        return stamped

    # ---- Heartbeat (không phụ thuộc viewer) ----
    async def _heartbeat_loop(self) -> None:
        while self._running:
            camera_online = not isinstance(self.source, RtspVideoSource) or self.source.connected
            if camera_online != self._last_published_camera_online:
                self._last_published_camera_online = camera_online
                if not camera_online:
                    self._heartbeat_state = "offline"
                    self._last_track_count = 0
                if self.mqtt:
                    self.mqtt.publish_camera_status(
                        online=camera_online,
                        reason="rtsp_connected" if camera_online else "rtsp_unavailable",
                    )
            msg = {
                "type": "status",
                "state": self._heartbeat_state,
                "latency_ms": round(self._latency_ms, 1),
                "track_count": self._last_track_count,
                "source_pts_ms": round(self._last_pts_ms, 1),
                "loop_id": self._last_loop_id_beat,
                "alerts": self._alert_count,
                "fall_state": self.fall_worker.status if self.fall_worker else "disabled",
            }
            await self._send_message(msg)
            for _ in range(int(max(0.5, self.config.heartbeat_seconds) * 2)):
                if not self._running:
                    return
                await asyncio.sleep(0.5)

    # ---- Relay WS (edge → backend → các web client khác) ----
    async def _relay_ws_loop(self) -> None:
        import websockets

        self._relay_ws = None
        while self._running:
            try:
                async with websockets.connect(self.config.ws_relay_url) as ws:
                    self._relay_ws = ws
                    logger.info(f"Relay WS connected: {self.config.ws_relay_url}")
                    try:
                        async for raw in ws:
                            pass  # giữ kết nối sống
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug(f"Relay WS reconnect in 3s ({exc})")
            finally:
                self._relay_ws = None
            if not self._running:
                break
            await asyncio.sleep(3.0)

    # ---- Stats (cho test) ----
    @property
    def stats(self) -> dict:
        return {
            "camera_id": self.config.camera_id,
            "latency_ms": round(self._latency_ms, 1),
            "state": self._heartbeat_state,
            "alerts": self._alert_count,
            "zones": self.engine.zone_count,
            "loops": self.store.loop_id,
            "detection_fps": self.config.detection_fps,
            "viewer_active": self._viewer_active.is_set(),
            "fall_state": self.fall_worker.status if self.fall_worker else "disabled",
        }


async def run(config: DemoStreamConfig | None = None) -> DemoStreamPipeline:
    """Run the edge pipeline with MQTT (production) or WebSocket (demo fallback)."""
    from module_edge_firmware.webrtc.client import EdgeWebRTCClient
    from module_edge_firmware.webrtc.video_track import AIVideoTrack

    cfg = config or build_config_from_settings()
    pipeline = DemoStreamPipeline(cfg)

    video_track = AIVideoTrack(
        frame_source=pipeline.store,
        start_time=pipeline.start_time,
        fps=cfg.frame_rate,
    )
    client = EdgeWebRTCClient(
        signaling_url=cfg.signaling_url,
        client_id=cfg.camera_id,
        video_track=video_track,
        channel_handler=pipeline.set_channel,
        session_prepare_handler=pipeline.prepare_viewer_session,
    )
    mqtt: EdgeMqttClient | None = None
    if cfg.mqtt_enabled:
        mqtt = EdgeMqttClient(
            host=cfg.mqtt_host,
            port=cfg.mqtt_port,
            device_id=cfg.camera_id,
            username=cfg.mqtt_username,
            password=cfg.mqtt_password,
            on_roi_update=pipeline.engine.set_zones,
            on_webrtc_offer=client.handle_offer,
        )
        pipeline.attach_mqtt(mqtt)
        mqtt.start()

    try:
        tasks = [pipeline.run_async()]
        # Preserve the existing WebSocket signaling only when explicitly
        # running without MQTT, e.g. the old frontend demo.
        if not cfg.mqtt_enabled:
            tasks.append(client.connect())
        await asyncio.gather(*tasks)
    finally:
        if mqtt:
            mqtt.stop()
    return pipeline


def main() -> None:
    """Entry point: chạy pipeline demo + WebRTC client."""
    from configs.logging_config import setup_logging

    setup_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Shutting down demo stream")


if __name__ == "__main__":
    main()
