"""Test PoseEstimator loading and basic inference."""
from module_ai_core.models.pose_estimator import PoseEstimator
import numpy as np


def test_model_loading():
    """Test 1: Load model"""
    print("Test 1: Loading PoseEstimator...")
    estimator = PoseEstimator()
    estimator.load()
    assert estimator.is_loaded, "❌ Model failed to load"
    print("✅ Model loaded successfully")


def test_prediction():
    """Test 2: Predict on dummy frame"""
    print("\nTest 2: Testing prediction...")
    estimator = PoseEstimator()
    estimator.load()

    # Create dummy frame (640x640 black image)
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    result = estimator.predict(frame, verbose=False)

    print(f"✅ Prediction works: {len(result)} people detected")
    print(f"   Keypoints shape: {result.keypoints.shape}")
    assert result.keypoints.shape[1:] == (17, 3), "❌ Wrong keypoints shape"


if __name__ == "__main__":
    test_model_loading()
    test_prediction()
    print("\n" + "="*50)
    print("ALL TESTS PASSED ✅")
    print("="*50)
