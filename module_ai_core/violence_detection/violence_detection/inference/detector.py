"""
ViolenceDetector core inference engine.
"""

from __future__ import annotations

import time
from typing import Generator, Iterable, Sequence
import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger

from violence_detection.config import ViolenceDetectionConfig
from violence_detection.inference.engine import InferenceEngineFactory, BaseInferenceEngine
from violence_detection.preprocessing.video import preprocess_frames
from violence_detection.preprocessing.person_filter import PersonFilter
from violence_detection.inference.smoothing import TemporalSmoother
from violence_detection.types import ViolencePrediction


class ViolenceDetector:
    """
    Main Violence Detector class for clip prediction and video stream processing.
    Supports PyTorch and ONNX inference engines seamlessly via Strategy Pattern.
    Optionally includes a PersonFilter layer to skip inference when persons are absent.
    """

    def __init__(self, config: ViolenceDetectionConfig | None = None):
        """
        Initialize detector, inference engine, and optional PersonFilter.

        Args:
            config: ViolenceDetectionConfig instance. If None, default config is used.
        """
        self.config = config or ViolenceDetectionConfig()
        self.device = self.config.get_resolved_device()

        # Initialize Strategy Inference Engine (PyTorch or ONNX)
        self.engine: BaseInferenceEngine = InferenceEngineFactory.create_engine(self.config)

        # Initialize Person Filter if enabled
        self.person_filter: PersonFilter | None = None
        if self.config.enable_person_filter:
            logger.info("ViolenceDetector: PersonFilter layer enabled.")
            self.person_filter = PersonFilter(
                min_persons=self.config.min_persons_required,
                conf_threshold=self.config.person_conf_threshold,
                backend=self.config.person_filter_backend,
            )

        # Initialize temporal smoother
        self.smoother = TemporalSmoother(
            window_size=self.config.smoothing_window,
            method=self.config.smoothing_method,
            min_consecutive=self.config.alert_min_consecutive,
            threshold=self.config.violence_threshold,
        )

    def predict_clip(
        self,
        frames: list[np.ndarray],
        timestamp: float | None = None,
    ) -> ViolencePrediction:
        """
        Perform inference on a single video clip (sequence of frames).

        Args:
            frames: List of OpenCV BGR frames of length equal to config.clip_length (16).
            timestamp: Optional timestamp in seconds.

        Returns:
            ViolencePrediction DTO object.
        """
        start_time = time.perf_counter()

        # Optional Person Filter check
        if self.person_filter is not None:
            has_persons, count = self.person_filter.has_required_persons(frames)
            if not has_persons:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                smoothed_prob, is_alert = self.smoother.update(0.0)
                logger.debug(
                    f"PersonFilter: Found {count} person(s) (< {self.config.min_persons_required}). "
                    f"Skipping violence inference."
                )
                return ViolencePrediction(
                    violence=False,
                    confidence=smoothed_prob,
                    raw_probability=0.0,
                    smoothed_probability=smoothed_prob,
                    timestamp=timestamp,
                    inference_ms=elapsed_ms,
                )

        # Preprocess input frames
        clip_tensor = preprocess_frames(
            frames=frames,
            expected_clip_length=self.config.clip_length,
            spatial_size=self.config.spatial_size,
            mean=self.config.mean,
            std=self.config.std,
        )

        # Delegate inference to current strategy engine
        raw_prob = self.engine.predict_raw_prob(clip_tensor)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Temporal smoothing
        smoothed_prob, is_alert = self.smoother.update(raw_prob)

        logger.debug(
            f"Clip prediction: raw_prob={raw_prob:.4f}, smoothed_prob={smoothed_prob:.4f}, "
            f"violence={is_alert}, latency={elapsed_ms:.2f}ms"
        )

        return ViolencePrediction(
            violence=is_alert,
            confidence=smoothed_prob,
            raw_probability=raw_prob,
            smoothed_probability=smoothed_prob,
            timestamp=timestamp,
            inference_ms=elapsed_ms,
        )

    def reset_smoothing(self) -> None:
        """Reset temporal smoothing buffer state."""
        self.smoother.reset()

    def process_stream(
        self,
        source: str | int | None = None,
        stream=None,
        frame_stride: int | None = None,
    ) -> Generator[ViolencePrediction, None, None]:
        """
        High-level API to process a video stream or camera using sliding window buffer.

        Args:
            source: Stream source (webcam index 0, file path, or RTSP URL).
            stream: Pre-existing VideoStream instance.
            frame_stride: Overrides config.frame_stride if provided.

        Yields:
            ViolencePrediction objects for each evaluated clip window.
        """
        from violence_detection.stream.capture import VideoStream

        stride = frame_stride if frame_stride is not None else self.config.frame_stride

        # Use provided stream or create one from source
        stream_ctx = stream if stream is not None else VideoStream(source)

        with stream_ctx as video_stream:
            self.reset_smoothing()
            window_frames: list[np.ndarray] = []
            frame_counter = 0

            for frame, timestamp in video_stream:
                window_frames.append(frame)

                # Keep window size at most clip_length
                if len(window_frames) > self.config.clip_length:
                    window_frames.pop(0)

                # When window is full and hit stride interval, perform prediction
                if len(window_frames) == self.config.clip_length:
                    frame_counter += 1
                    if frame_counter % stride == 0 or frame_counter == 1:
                        prediction = self.predict_clip(window_frames, timestamp=timestamp)
                        yield prediction
