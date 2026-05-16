"""
Stress Test Script.

Chạy EdgePipeline với MockAIService trong 5-10 phút để kiểm tra độ ổn định.
"""

import time
import os
import psutil
import numpy as np
from loguru import logger
from module_edge_firmware.pipeline import EdgePipeline
from module_edge_firmware.inference.mock_ai_service import MockAIService
from configs.logging_config import setup_logging
import threading

def stress_test(duration_minutes: float = 2.0): # Chạy 2 phút cho demo
    logger.info(f"🔥 Starting stress test for {duration_minutes} minutes...")
    
    pipeline = EdgePipeline()
    # Inject Mock AI với incident dày đặc để test Buffer/Alert
    pipeline.ai_runner = MockAIService(incident_every=30) 
    
    process = psutil.Process(os.getpid())
    start_time = time.time()
    
    # Tạo frame giả lập (1080p)
    dummy_frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    
    try:
        setup_logging()
        pipeline.ai_runner.load_all()
        pipeline._running = True
        
        # Start health monitor manually for stress test
        health_thread = threading.Thread(target=pipeline._health_monitor_loop, daemon=True)
        health_thread.start()
        
        logger.info("Pipeline running in stress test mode (using dummy frames)...")
        
        while time.time() - start_time < duration_minutes * 60:
            pipeline._process_frame(dummy_frame)
            
            # Giả lập FPS (ví dụ 15 FPS)
            time.sleep(1/15)
            
            if pipeline._stats["frames_processed"] % 100 == 0:
                mem_mb = process.memory_info().rss / 1024 / 1024
                logger.info(
                    f"STRESS STATS: Frames={pipeline._stats['frames_processed']} | "
                    f"Latency={pipeline._stats['avg_latency_ms']:.1f}ms | "
                    f"Memory={mem_mb:.2f} MB | "
                    f"Alerts={pipeline._stats['alerts_sent']}"
                )
                
    except KeyboardInterrupt:
        logger.info("Stress test interrupted.")
    finally:
        pipeline.stop()
        logger.info("Stress test finished.")

if __name__ == "__main__":
    stress_test()
