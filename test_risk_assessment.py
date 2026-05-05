"""Test RiskAssessor integration with fall detection."""
from module_edge_firmware.analysis.risk_assessor import RiskAssessor, RiskLevel
from module_edge_firmware.inference.multi_task_runner import FrameAnalysis
from module_ai_core.models.pose_estimator import PoseResult
import numpy as np
import time


def create_lying_pose_result():
    """Create synthetic lying pose result."""
    kps = np.zeros((1, 17, 3), dtype=np.float32)
    kps[0, :, 0] = np.linspace(100, 500, 17)  # Wide
    kps[0, :, 1] = 300  # Short
    kps[0, :, 2] = 0.9
    return PoseResult(kps, np.array([0.9]), np.array([[100, 200, 400, 300]]))


def test_injury_fall_triggers_critical():
    """Test that injury fall triggers CRITICAL risk level."""
    print("Test: Injury fall → CRITICAL risk...")

    assessor = RiskAssessor()
    analysis = FrameAnalysis()

    # Simulate fall sequence
    for i in range(100):  # 3+ seconds
        analysis.poses = create_lying_pose_result()
        assessment = assessor.assess(analysis)

        if assessment.fall_event and assessment.fall_event.is_injury:
            # Verify CRITICAL level
            if assessment.level != RiskLevel.CRITICAL:
                print(f"❌ Wrong risk level: {assessment.level} (expected CRITICAL)")
                return False

            if not assessment.should_alert:
                print(f"❌ should_alert is False (expected True)")
                return False

            if not any("Té ngã chấn thương" in r for r in assessment.reasons):
                print(f"❌ Missing injury fall reason")
                return False

            print(f"✅ Injury fall triggers CRITICAL alert")
            print(f"   Duration: {assessment.fall_event.duration_still:.1f}s")
            print(f"   Reasons: {assessment.reasons}")
            return True

        time.sleep(0.01)

    print("❌ Injury fall not detected")
    return False


if __name__ == "__main__":
    success = test_injury_fall_triggers_critical()
    print("\n" + "="*50)
    if success:
        print("TEST PASSED ✅")
    else:
        print("TEST FAILED ❌")
    print("="*50)
