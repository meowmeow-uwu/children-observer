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
from violence_detection.model.loader import load_model
from violence_detection.preprocessing.video import preprocess_frames
from violence_detection.inference.smoothing import TemporalSmoother
from violence_detection.types import ViolencePrediction


class ViolenceDetector:
    """
    Main Violence Detector class for clip prediction and video stream processing.
    """

    def __init__(self, config: ViolenceDetectionConfig | None = None):
        """
        Initialize detector and load pretrained model.

        Args:
            config: ViolenceDetectionConfig instance. If None, default config is used.
        """
        self.config = config or ViolenceDetectionConfig()
        self.device = self.config.get_resolved_device()

        # Load model once during detector lifecycle
        self.model = load_model(self.config)

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

        # Preprocess input frames
        clip_tensor = preprocess_frames(
            frames=frames,
            expected_clip_length=self.config.clip_length,
            spatial_size=self.config.spatial_size,
            mean=self.config.mean,
            std=self.config.std,
        ).to(self.device)

        # Inference in mode without gradients
        with torch.inference_mode():
            logits = self.model(clip_tensor)
            probs = F.softmax(logits, dim=1)

            if self.device.type == "cuda":
                torch.cuda.synchronize()

            # Index 1 is violence class
            raw_prob = float(probs[0, 1].item())

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
