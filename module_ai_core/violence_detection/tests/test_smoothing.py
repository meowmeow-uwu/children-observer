"""
Unit tests for TemporalSmoother.
"""

import pytest
from violence_detection.inference.smoothing import TemporalSmoother


def test_normal_sequence():
    """Normal sequence with low raw probabilities should not trigger alert."""
    smoother = TemporalSmoother(window_size=5, method="moving_average", min_consecutive=2, threshold=0.4)
    
    probs = [0.1, 0.15, 0.2, 0.12, 0.18]
    for p in probs:
        smoothed_p, is_alert = smoother.update(p)
        assert is_alert is False
        assert smoothed_p < 0.4


def test_positive_spike_isolation():
    """Single positive spike surrounded by low values should be smoothed out and not alert."""
    smoother = TemporalSmoother(window_size=5, method="moving_average", min_consecutive=2, threshold=0.4)

    # 4 normal frames, 1 spike frame (0.9)
    # Window average: (0.1*4 + 0.9)/5 = 1.3 / 5 = 0.26 < 0.4
    for _ in range(4):
        smoother.update(0.1)

    smoothed_p, is_alert = smoother.update(0.9)
    assert smoothed_p < 0.4
    assert is_alert is False


def test_persistent_positive_triggers_alert():
    """Persistent high probabilities should cause smoothed score >= threshold and trigger alert after min_consecutive windows."""
    smoother = TemporalSmoother(window_size=3, method="moving_average", min_consecutive=2, threshold=0.4)

    # Window 1: [0.8] -> avg 0.8 -> consecutive = 1 -> is_alert False (min_consecutive=2)
    s1, alert1 = smoother.update(0.8)
    assert s1 >= 0.4
    assert alert1 is False

    # Window 2: [0.8, 0.85] -> avg 0.825 -> consecutive = 2 -> is_alert True
    s2, alert2 = smoother.update(0.85)
    assert s2 >= 0.4
    assert alert2 is True


def test_threshold_boundary():
    """Test behavior right around boundary of threshold."""
    smoother = TemporalSmoother(window_size=1, method="moving_average", min_consecutive=1, threshold=0.4)

    _, alert_below = smoother.update(0.399)
    assert alert_below is False

    _, alert_at = smoother.update(0.400)
    assert alert_at is True


def test_median_smoothing():
    """Test median smoothing method behavior."""
    smoother = TemporalSmoother(window_size=5, method="median", min_consecutive=1, threshold=0.4)
    
    # 0.1, 0.1, 0.9, 0.1, 0.1 -> median is 0.1
    probs = [0.1, 0.1, 0.9, 0.1, 0.1]
    for p in probs:
        s_prob, alert = smoother.update(p)
    
    assert pytest.approx(s_prob) == 0.1
    assert alert is False
