"""Fall detection runtime for the lightweight edge stream.

The worker intentionally consumes only the newest camera frame.  Pose inference can
be substantially slower than ROI detection on a Raspberry Pi 4; retaining old
frames would otherwise make an alert describe a scene that has already passed.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import cv2
import onnxruntime as ort
from loguru import logger


@dataclass(frozen=True)
class PosePerson:
    box: list[float]
    keypoints: np.ndarray  # (17, 3), normalised to 0..1
    confidence: float


@dataclass(frozen=True)
class FallAlert:
    camera_id: str
    track_id: int
    confidence: float
    at_ms: float
    title: str = "Phát hiện trẻ có dấu hiệu té ngã"
    severity: str = "danger"
    roi_name: str = ""

    @property
    def notes(self) -> str:
        return (
            f"event_type=fall_injury; track_id={self.track_id}; "
            f"confidence={self.confidence:.3f}; source_time_ms={self.at_ms:.1f}"
        )


@dataclass(frozen=True)
class FallAnnotation:
    state: str
    confidence: float
    latency_ms: float

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "confidence": round(self.confidence, 3),
            "latency_ms": round(self.latency_ms, 1),
        }


def serialise_keypoints(keypoints: np.ndarray) -> tuple[tuple[float, float, float], ...]:
    """Return JSON-safe, normalised COCO keypoints for the matched child only."""
    points = np.asarray(keypoints, dtype=np.float32).reshape(-1, 3)
    return tuple(
        (
            round(float(np.clip(np.nan_to_num(x, nan=0.0), 0.0, 1.0)), 4),
            round(float(np.clip(np.nan_to_num(y, nan=0.0), 0.0, 1.0)), 4),
            round(float(np.clip(np.nan_to_num(confidence, nan=0.0), 0.0, 1.0)), 4),
        )
        for x, y, confidence in points
    )


def pose_payload(person: PosePerson) -> dict:
    """JSON-safe pose data for UI rendering, independent from child tracking."""
    return {
        "box": [round(float(value), 4) for value in person.box],
        "confidence": round(float(np.clip(person.confidence, 0.0, 1.0)), 3),
        "keypoints": [list(point) for point in serialise_keypoints(person.keypoints)],
    }


class FallPoseEstimator:
    """YOLO11-Pose ONNX wrapper with deterministic CPU session options."""

    def __init__(self, model_path: str | Path, conf_threshold: float, input_size: int):
        self.model_path = Path(model_path)
        self.conf_threshold = conf_threshold
        self.input_size = input_size
        self._session: ort.InferenceSession | None = None
        self._input_name = ""

    def load(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"Fall ONNX model not found: {self.model_path}")
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.intra_op_num_threads = max(1, int(os.getenv("EDGE_FALL_ONNX_INTRA_THREADS", "2")))
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self._session = ort.InferenceSession(
            str(self.model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name
        self.predict(np.zeros((self.input_size, self.input_size, 3), dtype=np.uint8))
        logger.info("Fall pose ONNX ready: {} (threads={})", self.model_path.name, options.intra_op_num_threads)

    def predict(self, frame: np.ndarray) -> list[PosePerson]:
        if self._session is None:
            raise RuntimeError("Fall pose estimator is not loaded")
        h, w = frame.shape[:2]
        # OpenCV supplies BGR frames, while Ultralytics YOLO preprocessing feeds
        # RGB into the model.  Keep this conversion aligned with the .pt path
        # before resize/letterbox so exported ONNX sees the same channels.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ratio = min(self.input_size / h, self.input_size / w)
        resized = cv2.resize(rgb_frame, (int(round(w * ratio)), int(round(h * ratio))))
        pad_x = (self.input_size - resized.shape[1]) / 2.0
        pad_y = (self.input_size - resized.shape[0]) / 2.0
        image = cv2.copyMakeBorder(
            resized, int(round(pad_y - 0.1)), int(round(pad_y + 0.1)),
            int(round(pad_x - 0.1)), int(round(pad_x + 0.1)),
            cv2.BORDER_CONSTANT, value=(114, 114, 114),
        )
        output = self._session.run(None, {self._input_name: image.transpose(2, 0, 1)[None].astype(np.float32) / 255.0})[0]
        if output.ndim == 3:
            output = output[0].T
        if output.ndim != 2 or output.shape[1] < 56:
            raise ValueError(f"Unexpected YOLO pose output shape: {output.shape}")
        scores = output[:, 4]
        valid = scores >= self.conf_threshold
        rows, scores = output[valid], scores[valid]
        if len(rows) == 0:
            return []
        xywh = rows[:, :4]
        xyxy = np.column_stack((xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2, xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2))
        # cv2.dnn.NMSBoxes expects [x, y, width, height], not [x1, y1, x2, y2].
        nms_xywh = np.column_stack((
            xyxy[:, 0],
            xyxy[:, 1],
            xyxy[:, 2] - xyxy[:, 0],
            xyxy[:, 3] - xyxy[:, 1],
        ))
        indices = np.asarray(
            cv2.dnn.NMSBoxes(nms_xywh.tolist(), scores.tolist(), self.conf_threshold, 0.45)
        ).reshape(-1)
        people: list[PosePerson] = []
        for index in indices:
            box, score, row = xyxy[int(index)], scores[int(index)], rows[int(index)]
            normalised = row[5:56].reshape(17, 3).astype(np.float32, copy=True)
            normalised[:, 0] = np.clip((normalised[:, 0] - pad_x) / ratio / max(w, 1), 0, 1)
            normalised[:, 1] = np.clip((normalised[:, 1] - pad_y) / ratio / max(h, 1), 0, 1)
            people.append(
                PosePerson(
                    box=[
                        float(np.clip((box[0] - pad_x) / ratio / max(w, 1), 0, 1)),
                        float(np.clip((box[1] - pad_y) / ratio / max(h, 1), 0, 1)),
                        float(np.clip((box[2] - pad_x) / ratio / max(w, 1), 0, 1)),
                        float(np.clip((box[3] - pad_y) / ratio / max(h, 1), 0, 1)),
                    ],
                    keypoints=normalised,
                    confidence=float(score),
                )
            )
        return people


def box_iou(a: list[float], b: list[float]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def associate_child_poses(tracks: list[dict], people: list[PosePerson], min_iou: float = 0.2) -> list[tuple[int, PosePerson]]:
    """Greedily associate each confirmed child track with one pose observation."""
    remaining = list(people)
    matches: list[tuple[int, PosePerson]] = []
    for track in tracks:
        candidate = max(remaining, key=lambda person: box_iou(track["box"], person.box), default=None)
        if candidate is None or box_iou(track["box"], candidate.box) < min_iou:
            continue
        remaining.remove(candidate)
        matches.append((int(track["track_id"]), candidate))
    return matches


@dataclass
class _TrackState:
    state: str = "normal"
    previous_center: np.ndarray | None = None
    previous_at_ms: float | None = None
    suspected_at_ms: float | None = None
    last_seen_ms: float = 0.0
    alerted: bool = False
    confidence: float = 0.0


class FallStateEngine:
    """Track-scoped, time-based fall state machine."""

    def __init__(
        self,
        *,
        still_seconds: float,
        velocity_threshold: float,
        still_velocity_threshold: float,
        lying_ratio_threshold: float = 0.6,
        cooldown_seconds: float = 30.0,
        track_ttl_seconds: float = 3.0,
        alert_on_suspected: bool = True,
    ):
        self.still_ms = still_seconds * 1000.0
        self.velocity_threshold = velocity_threshold
        self.still_velocity_threshold = still_velocity_threshold
        self.lying_ratio_threshold = lying_ratio_threshold
        self.cooldown_ms = cooldown_seconds * 1000.0
        self.track_ttl_ms = track_ttl_seconds * 1000.0
        self.alert_on_suspected = alert_on_suspected
        self._states: dict[int, _TrackState] = {}
        self._last_alert_ms: dict[int, float] = {}

    def _emit_allowed(self, track_id: int, at_ms: float) -> bool:
        last = self._last_alert_ms.get(track_id)
        if last is not None and at_ms - last < self.cooldown_ms:
            return False
        self._last_alert_ms[track_id] = at_ms
        return True

    def update(self, track_id: int, keypoints: np.ndarray, at_ms: float) -> tuple[FallAnnotation, bool]:
        state = self._states.setdefault(track_id, _TrackState())
        valid = keypoints[keypoints[:, 2] >= 0.3, :2]
        state.last_seen_ms = at_ms
        if len(valid) < 4:
            return FallAnnotation(state.state, state.confidence, 0.0), False

        center = valid.mean(axis=0)
        velocity = 0.0
        had_previous_pose = state.previous_center is not None and state.previous_at_ms is not None
        if had_previous_pose:
            seconds = max((at_ms - state.previous_at_ms) / 1000.0, 0.001)
            velocity = float(np.linalg.norm(center - state.previous_center) / seconds)
        state.previous_center, state.previous_at_ms = center, at_ms

        width = float(valid[:, 0].max() - valid[:, 0].min())
        height = float(valid[:, 1].max() - valid[:, 1].min())
        lying = height / max(width, 1e-6) < self.lying_ratio_threshold
        emitted = False

        if state.state == "normal":
            # Alerting immediately requires evidence of a transition.  A first
            # pose that is already horizontal may simply be a child lying down.
            if lying and had_previous_pose and velocity >= self.velocity_threshold:
                state.state = "suspected"
                state.suspected_at_ms = at_ms
                state.confidence = min(0.8, 0.5 + velocity)
                if self.alert_on_suspected and self._emit_allowed(track_id, at_ms):
                    state.alerted = True
                    emitted = True
        elif state.state == "suspected":
            if not lying:
                state.state, state.suspected_at_ms, state.confidence = "normal", None, 0.0
            elif (
                state.suspected_at_ms is not None
                and at_ms - state.suspected_at_ms >= self.still_ms
                and velocity <= self.still_velocity_threshold
            ):
                state.state = "confirmed"
                state.confidence = min(0.98, 0.7 + (at_ms - state.suspected_at_ms) / 10000.0)
                if not self.alert_on_suspected and self._emit_allowed(track_id, at_ms):
                    state.alerted = True
                    emitted = True
        elif state.state == "confirmed" and not lying:
            state.state, state.confidence = "recovered", 0.6
        elif state.state == "recovered":
            state.state, state.suspected_at_ms, state.confidence = "normal", None, 0.0

        return FallAnnotation(state.state, state.confidence, 0.0), emitted

    def prune(self, now_ms: float) -> None:
        for track_id, state in list(self._states.items()):
            if now_ms - state.last_seen_ms > self.track_ttl_ms:
                self._states.pop(track_id, None)

    def reset(self) -> None:
        """Discard state that belongs to a previous video/viewer session."""
        self._states.clear()
        self._last_alert_ms.clear()


class FallMetricsWriter:
    def __init__(self, path: str | Path, model_path: str | Path):
        self.path = Path(path)
        self.model_path = Path(model_path).name
        self._lock = threading.RLock()

    def write(self, payload: dict) -> None:
        entry = {"timestamp_ms": round(time.time() * 1000), "model": self.model_path, **payload}
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Fall metrics disabled: {}", exc)


@dataclass(frozen=True)
class _WorkItem:
    frame: np.ndarray
    tracks: list[dict]
    at_ms: float
    frame_id: int
    generation: int


class FallWorker:
    """Bounded asynchronous pose inference with graceful retry on model failures."""

    def __init__(
        self,
        *,
        camera_id: str,
        model_path: str | Path,
        conf_threshold: float,
        input_size: int,
        fps: float,
        state_engine: FallStateEngine,
        metrics_path: str | Path,
    ):
        self.camera_id = camera_id
        self.estimator = FallPoseEstimator(model_path, conf_threshold, input_size)
        self.fps = max(fps, 0.1)
        self.engine = state_engine
        self.metrics = FallMetricsWriter(metrics_path, model_path)
        self._queue: queue.Queue[_WorkItem | None] = queue.Queue(maxsize=1)
        self._annotations: dict[int, FallAnnotation] = {}
        self._poses: list[dict] = []
        self._alerts: queue.Queue[tuple[FallAlert, np.ndarray]] = queue.Queue(maxsize=8)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_offer_ms = -float("inf")
        self._generation = 0
        self.status = "initializing"
        self._next_retry = 0.0

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="fall-pose", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread:
            self._thread.join(timeout=5)

    def reset(self) -> None:
        """Forget queued work and state when the source starts a new session."""
        with self._lock:
            self._generation += 1
            self.engine.reset()
            self._annotations.clear()
            self._poses.clear()
            self._last_offer_ms = -float("inf")
            self._drain_queue(self._queue)
            self._drain_queue(self._alerts)

    @staticmethod
    def _drain_queue(target: queue.Queue) -> None:
        while True:
            try:
                target.get_nowait()
            except queue.Empty:
                return

    def offer(self, frame: np.ndarray, tracks: list[dict], at_ms: float, frame_id: int) -> None:
        # Demo sources restart their timeline at the beginning of each loop.  The
        # reset keeps an old track state/cooldown from leaking into the new loop.
        if at_ms < self._last_offer_ms:
            self.reset()
        if at_ms - self._last_offer_ms < 1000.0 / self.fps:
            return
        self._last_offer_ms = at_ms
        with self._lock:
            generation = self._generation
        item = _WorkItem(
            frame,
            [dict(track) for track in tracks if track.get("confirmed")],
            at_ms,
            frame_id,
            generation,
        )
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(item)
            except queue.Empty:
                pass

    def annotate(self, tracks: list[dict]) -> None:
        with self._lock:
            annotations = dict(self._annotations)
        for track in tracks:
            annotation = annotations.get(int(track.get("track_id", -1)))
            if annotation:
                track["fall"] = annotation.as_dict()

    def poses(self) -> list[dict]:
        """Return the latest pose observations, including people without child tracks."""
        with self._lock:
            return [
                {
                    **pose,
                    "box": list(pose["box"]),
                    "keypoints": [list(point) for point in pose["keypoints"]],
                }
                for pose in self._poses
            ]

    def drain_alerts(self) -> list[tuple[FallAlert, np.ndarray]]:
        alerts = []
        while True:
            try:
                alerts.append(self._alerts.get_nowait())
            except queue.Empty:
                return alerts

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                return
            if time.monotonic() < self._next_retry:
                continue
            try:
                if self.estimator._session is None:
                    self.estimator.load()
                started = time.perf_counter()
                people = self.estimator.predict(item.frame)
                latency_ms = (time.perf_counter() - started) * 1000.0
                self._process(item, people, latency_ms)
                self.status = "ready"
            except Exception as exc:
                self.status = "degraded"
                self._next_retry = time.monotonic() + 30.0
                logger.exception("Fall inference degraded; retry in 30s: {}", exc)

    def _process(self, item: _WorkItem, people: list[PosePerson], latency_ms: float) -> None:
        with self._lock:
            if item.generation != self._generation:
                return
            annotations: dict[int, FallAnnotation] = {}
            self._poses = [pose_payload(person) for person in people]
            for track_id, match in associate_child_poses(item.tracks, people):
                annotation, emitted = self.engine.update(track_id, match.keypoints, item.at_ms)
                annotation = FallAnnotation(annotation.state, annotation.confidence, latency_ms)
                annotations[track_id] = annotation
                self.metrics.write({
                    "frame_id": item.frame_id,
                    "source_time_ms": round(item.at_ms, 1),
                    "track_id": track_id,
                    "state": annotation.state,
                    "confidence": round(annotation.confidence, 3),
                    "latency_ms": round(latency_ms, 1),
                    "alert_outcome": "emitted" if emitted else "none",
                })
                if emitted:
                    try:
                        self._alerts.put_nowait((FallAlert(self.camera_id, track_id, annotation.confidence, item.at_ms), item.frame.copy()))
                    except queue.Full:
                        logger.warning("Fall alert queue full; dropping newest alert")
            self.engine.prune(item.at_ms)
            self._annotations = annotations
