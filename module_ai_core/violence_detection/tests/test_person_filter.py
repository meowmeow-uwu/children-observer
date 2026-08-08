"""
Unit test for PersonFilter layer.
"""

from __future__ import annotations

import numpy as np
import pytest
from violence_detection.config import ViolenceDetectionConfig
from violence_detection.preprocessing.person_filter import PersonFilter


def test_person_filter_hog_backend():
    # Test built-in OpenCV HOG backend
    filter_layer = PersonFilter(min_persons=2, backend="hog")
    assert filter_layer.active_backend == "hog"

    # Empty black frame -> should detect 0 persons
    blank_frame = np.zeros((400, 400, 3), dtype=np.uint8)
    count = filter_layer.count_persons_in_frame(blank_frame)
    assert count == 0

    frames = [blank_frame for _ in range(16)]
    has_persons, max_count = filter_layer.has_required_persons(frames)
    assert not has_persons
    assert max_count == 0


def test_person_filter_auto_fallback():
    # Auto fallback to hog if yolo is not available
    filter_layer = PersonFilter(min_persons=1, backend="auto")
    assert filter_layer.active_backend in ("yolo", "hog")
