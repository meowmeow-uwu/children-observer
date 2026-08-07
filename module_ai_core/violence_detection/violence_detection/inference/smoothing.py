"""
Temporal smoothing for reducing false alerts in video stream predictions.
"""

from __future__ import annotations

from collections import deque
import numpy as np


class TemporalSmoother:
    """
    Temporal smoothing buffer for model predictions.

    Maintains a rolling window of recent raw violence probabilities and computes a smoothed score
    using moving average or median. Also enforces a minimum number of consecutive positive
    window predictions before triggering an alert.
    """

    def __init__(
        self,
        window_size: int = 5,
        method: str = "moving_average",
        min_consecutive: int = 2,
        threshold: float = 0.4,
    ):
        """
        Args:
            window_size: Number of recent probabilities to keep in sliding window.
            method: 'moving_average' or 'median'.
            min_consecutive: Minimum consecutive smoothed values >= threshold required for alert.
            threshold: Violence decision threshold.
        """
        if window_size <= 0:
            raise ValueError(f"window_size must be positive, got {window_size}")
        if method not in ("moving_average", "median"):
            raise ValueError(
                f"Invalid method '{method}'. Supported methods: 'moving_average', 'median'."
            )

        self.window_size = window_size
        self.method = method
        self.min_consecutive = min_consecutive
        self.threshold = threshold

        self._buffer: deque[float] = deque(maxlen=window_size)
        self._consecutive_positives: int = 0

    def update(self, raw_prob: float) -> tuple[float, bool]:
        """
        Add a new raw probability to the window and return smoothed probability and alert status.

        Args:
            raw_prob: Raw violence probability from current clip inference [0.0, 1.0].

        Returns:
            Tuple of (smoothed_probability, is_violence_alert)
        """
        self._buffer.append(float(raw_prob))

        if self.method == "moving_average":
            smoothed_prob = float(np.mean(self._buffer))
        else:  # median
            smoothed_prob = float(np.median(self._buffer))

        # Check threshold
        if smoothed_prob >= self.threshold:
            self._consecutive_positives += 1
        else:
            self._consecutive_positives = 0

        # Alert triggered if consecutive positive count satisfies min_consecutive
        is_alert = self._consecutive_positives >= self.min_consecutive

        return smoothed_prob, is_alert

    def reset(self) -> None:
        """Reset internal buffer state."""
        self._buffer.clear()
        self._consecutive_positives = 0
