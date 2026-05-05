"""FPS Benchmark for Fall Detection (Pose Estimation)."""
import time
import numpy as np
from module_ai_core.models.pose_estimator import PoseEstimator
from configs.settings import get_settings


def benchmark_fps(num_frames=100):
    """Benchmark pose estimation FPS."""
    settings = get_settings()
    print(f"Device: {settings.inference_device}")
    print(f"Benchmarking {num_frames} frames...")

    estimator = PoseEstimator()
    estimator.load()

    # Create realistic test frame (640x640 RGB)
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    # Warmup (10 frames)
    print("Warming up...")
    for _ in range(10):
        estimator.predict(frame, verbose=False)

    # Benchmark
    print("Running benchmark...")
    start = time.perf_counter()
    for i in range(num_frames):
        result = estimator.predict(frame, verbose=False)
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{num_frames}")
    elapsed = time.perf_counter() - start

    fps = num_frames / elapsed
    latency_ms = (elapsed / num_frames) * 1000

    print(f"\n{'='*50}")
    print(f"Benchmark Results ({num_frames} frames)")
    print(f"{'='*50}")
    print(f"FPS: {fps:.2f}")
    print(f"Latency: {latency_ms:.2f}ms per frame")
    print(f"Total time: {elapsed:.2f}s")
    print(f"{'='*50}")

    # Check DoD requirement (≥15 FPS on GPU)
    if settings.inference_device.startswith("cuda"):
        if fps >= 15:
            print(f"✅ PASSED: FPS {fps:.2f} >= 15 (GPU requirement)")
        else:
            print(f"❌ FAILED: FPS {fps:.2f} < 15 (GPU requirement)")
    else:
        print(f"ℹ️  CPU mode: FPS {fps:.2f} (no requirement)")

    return fps


if __name__ == "__main__":
    fps = benchmark_fps()
