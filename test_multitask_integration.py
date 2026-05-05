"""Test MultiTaskRunner integration with fall detection."""
from module_edge_firmware.inference.multi_task_runner import MultiTaskRunner
import numpy as np


def test_multitask_loading():
    """Test that MultiTaskRunner loads fall_detection."""
    print("Test: MultiTaskRunner loading...")

    runner = MultiTaskRunner()
    runner.load_all()

    # Verify fall_detection loaded
    if not runner._pose_loaded:
        print("❌ Pose estimator not loaded")
        return False

    print("✅ MultiTaskRunner loaded fall_detection")

    # Test analysis
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    analysis = runner.analyze_frame(frame)

    if "fall_detection" not in analysis.active_tasks:
        print("❌ fall_detection not in active_tasks")
        return False

    print(f"✅ Active tasks: {analysis.active_tasks}")
    print(f"   Latency: {analysis.latency_ms:.1f}ms")

    runner.shutdown()
    return True


if __name__ == "__main__":
    success = test_multitask_loading()
    print("\n" + "="*50)
    if success:
        print("TEST PASSED ✅")
    else:
        print("TEST FAILED ❌")
    print("="*50)
