"""
Tests cho Edge Firmware - analysis components.
"""

import numpy as np

from module_edge_firmware.analysis.roi_checker import ROIChecker, ROIZone
from module_edge_firmware.buffer.circular_buffer import CircularBuffer
from module_edge_firmware.ingestion.preprocessor import FramePreprocessor


class TestROIZone:
    def test_contains_point_inside(self):
        zone = ROIZone("test", [[0, 0], [100, 0], [100, 100], [0, 100]])
        assert zone.contains_point((50, 50)) is True

    def test_contains_point_outside(self):
        zone = ROIZone("test", [[0, 0], [100, 0], [100, 100], [0, 100]])
        assert zone.contains_point((150, 150)) is False

    def test_distance_to_point(self):
        zone = ROIZone("test", [[0, 0], [100, 0], [100, 100], [0, 100]])
        dist = zone.distance_to_point((50, 50))
        assert dist > 0  # Inside = positive distance


class TestROIChecker:
    def test_no_zones(self):
        checker = ROIChecker(config_path="/nonexistent/config.json")
        assert checker.has_zones is False
        assert checker.zone_count == 0

    def test_update_zones(self, tmp_path):
        checker = ROIChecker(config_path=str(tmp_path / "roi.json"))
        zones = [
            {
                "zone_id": "kitchen",
                "vertices": [[0, 0], [100, 0], [100, 100], [0, 100]],
                "label": "Bếp",
            },
        ]
        checker.update_zones(zones)
        assert checker.has_zones is True
        assert checker.zone_count == 1


class TestPreprocessor:
    def test_letterbox(self):
        proc = FramePreprocessor(target_size=640)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = proc.process(frame)
        assert result.shape == (640, 640, 3)

    def test_scale_info(self):
        proc = FramePreprocessor(target_size=640)
        info = proc.get_scale_info((1080, 1920), 640)
        assert "scale" in info
        assert "pad_x" in info


class TestCircularBuffer:
    def test_add_frame(self):
        buf = CircularBuffer(buffer_seconds=5, fps=10)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        buf.add_frame(frame)
        assert buf.frame_count == 1

    def test_buffer_limit(self):
        buf = CircularBuffer(buffer_seconds=1, fps=2)  # Max 2 frames
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        for _ in range(5):
            buf.add_frame(frame)
        assert buf.frame_count == 2  # Capped at maxlen
