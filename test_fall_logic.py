"""Test FallDetector logic with synthetic poses."""
from module_edge_firmware.analysis.fall_detector import FallDetector
from module_ai_core.models.pose_estimator import PoseResult
import numpy as np
import time


def create_standing_keypoints():
    """Create synthetic standing pose (tall, narrow)."""
    kps = np.zeros((1, 17, 3), dtype=np.float32)
    # Vertical pose: height > width
    kps[0, :, 0] = 320  # X: centered at 320
    kps[0, :, 1] = np.linspace(100, 500, 17)  # Y: 100 to 500 (tall)
    kps[0, :, 2] = 0.9  # High confidence
    return kps


def create_lying_keypoints():
    """Create synthetic lying pose (wide, short)."""
    kps = np.zeros((1, 17, 3), dtype=np.float32)
    # Horizontal pose: width > height
    kps[0, :, 0] = np.linspace(100, 500, 17)  # X: 100 to 500 (wide)
    kps[0, :, 1] = 300  # Y: centered at 300
    kps[0, :, 2] = 0.9  # High confidence
    return kps


def test_no_fall_standing():
    """Test 1: Standing pose should not trigger fall."""
    print("Test 1: Standing pose (no fall)...")
    detector = FallDetector()

    for i in range(10):
        kps = create_standing_keypoints()
        poses = PoseResult(kps, np.array([0.9]), np.array([[100, 100, 200, 400]]))
        event = detector.update(poses)

        if event is not None:
            print(f"❌ False positive: standing detected as fall")
            return False

    print("✅ Standing pose: no fall detected")
    return True


def test_injury_fall():
    """Test 2: Lying pose with stillness should trigger injury fall."""
    print("\nTest 2: Injury fall (lying + stillness)...")
    detector = FallDetector()

    # Simulate sudden movement (high velocity) - need bigger movement
    for i in range(5):
        kps = create_standing_keypoints()
        kps[0, :, 1] += i * 60  # Move down rapidly (increased from 30 to 60)
        poses = PoseResult(kps, np.array([0.9]), np.array([[100, 100, 200, 400]]))
        detector.update(poses)

    # Now lying still - need to wait longer for injury detection (>2 seconds)
    # Without sleep, just loop to accumulate time
    injury_detected = False
    for i in range(200):  # More iterations to ensure >2 seconds pass
        kps = create_lying_keypoints()
        poses = PoseResult(kps, np.array([0.9]), np.array([[100, 200, 400, 300]]))
        event = detector.update(poses)

        if event and event.is_injury:
            print(f"✅ Injury fall detected after {event.duration_still:.1f}s")
            print(f"   Velocity: {event.velocity:.1f} px/frame")
            print(f"   Confidence: {event.confidence:.2f}")
            injury_detected = True
            break

        # Small sleep to let time pass
        if i % 10 == 0:
            time.sleep(0.1)

    if not injury_detected:
        print("❌ Injury fall not detected")
        return False

    return True


def test_playful_fall():
    """Test 3: Quick recovery should trigger playful fall."""
    print("\nTest 3: Playful fall (quick recovery)...")
    detector = FallDetector()

    # Simulate fall
    for i in range(5):
        kps = create_standing_keypoints()
        kps[0, :, 1] += i * 30
        poses = PoseResult(kps, np.array([0.9]), np.array([[100, 100, 200, 400]]))
        detector.update(poses)

    # Lying briefly
    for i in range(10):  # < 2 seconds
        kps = create_lying_keypoints()
        poses = PoseResult(kps, np.array([0.9]), np.array([[100, 200, 400, 300]]))
        detector.update(poses)
        time.sleep(0.01)

    # Stand up quickly
    kps = create_standing_keypoints()
    poses = PoseResult(kps, np.array([0.9]), np.array([[100, 100, 200, 400]]))
    event = detector.update(poses)

    if event and not event.is_injury:
        print(f"✅ Playful fall detected")
        print(f"   Duration: {event.duration_still:.1f}s")
        return True
    else:
        print("❌ Playful fall not detected correctly")
        return False


if __name__ == "__main__":
    results = []
    results.append(test_no_fall_standing())
    results.append(test_injury_fall())
    results.append(test_playful_fall())

    print("\n" + "="*50)
    if all(results):
        print("ALL TESTS PASSED ✅")
    else:
        print(f"SOME TESTS FAILED ❌ ({sum(results)}/{len(results)} passed)")
    print("="*50)
