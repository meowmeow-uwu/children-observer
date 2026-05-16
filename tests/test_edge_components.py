"""
Integration Tests for Edge Firmware & ROI.

Kiểm tra sự phối hợp giữa:
1. Preprocessor -> Tensor conversion
2. ROIChecker -> Intrusion detection
3. CircularBuffer -> Async clip extraction
"""

import unittest
import numpy as np
import time
from pathlib import Path
import json

from module_edge_firmware.ingestion.preprocessor import FramePreprocessor
from module_edge_firmware.analysis.roi_checker import ROIChecker
from module_edge_firmware.buffer.circular_buffer import CircularBuffer

class TestEdgeComponents(unittest.TestCase):
    
    def setUp(self):
        self.preprocessor = FramePreprocessor(target_size=640, normalize=True)
        self.roi_checker = ROIChecker(config_path="./tests/test_roi.json")
        self.buffer = CircularBuffer(buffer_seconds=5, fps=10, output_dir="./tests/test_clips")
        
        # Tạo ROI giả lập (tọa độ chuẩn hóa 0-1)
        test_zones = {
            "zones": [
                {
                    "zone_id": "test_zone",
                    "label": "dangerous_area",
                    "vertices": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]]
                }
            ]
        }
        Path("./tests").mkdir(exist_ok=True)
        with open("./tests/test_roi.json", "w") as f:
            json.dump(test_zones, f)
        self.roi_checker._load_config()
        # Giả lập frame 1000x1000 để dễ tính toán
        self.roi_checker._update_all_scales((1000, 1000))

    def test_preprocessor_normalization(self):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        tensor = self.preprocessor.to_tensor(frame)
        
        # Check shape (NCHW)
        self.assertEqual(tensor.shape, (1, 3, 640, 640))
        # Check normalization
        self.assertTrue(tensor.max() <= 1.0)
        self.assertTrue(tensor.min() >= 0.0)
        self.assertEqual(tensor.dtype, np.float32)

    def test_roi_intrusion(self):
        # Point inside (0.15 * 1000 = 150)
        intruded = self.roi_checker.check_intrusion((150, 150))
        self.assertEqual(len(intruded), 1)
        self.assertEqual(intruded[0].zone_id, "test_zone")
        
        # Point outside
        intruded = self.roi_checker.check_intrusion((50, 50))
        self.assertEqual(len(intruded), 0)
        
        # Box intrusion
        box = np.array([120, 120, 180, 180]) # fully inside
        self.assertEqual(len(self.roi_checker.check_box_intrusion(box, frame_size=(1000, 1000))), 1)

    def test_circular_buffer_async_extraction(self):
        # Add some frames
        for i in range(20):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            self.buffer.add_frame(frame)
            
        clip_path = self.buffer.extract_clip(duration=1)
        self.assertIsNotNone(clip_path)
        
        # Clip is extracted async, wait a bit for file to be written
        time.sleep(1)
        self.assertTrue(clip_path.exists())
        self.assertTrue(clip_path.stat().st_size > 0)
        
        # Cleanup
        if clip_path.exists():
            clip_path.unlink()

    def tearDown(self):
        # Cleanup test files
        if Path("./tests/test_roi.json").exists():
            Path("./tests/test_roi.json").unlink()
        for p in Path("./tests/test_clips").glob("*.mp4"):
            p.unlink()

if __name__ == "__main__":
    unittest.main()
