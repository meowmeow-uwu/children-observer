#!/usr/bin/env python3
"""
Launcher / Entry point for Violence Detection GUI Studio.
Invokes the main detector in module_ai_core/violence_detection/src/CodeBase/Final_Deployment/gui_detector.py
"""
import os
import sys

TARGET_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "module_ai_core", "violence_detection", "src", "CodeBase", "Final_Deployment", "gui_detector.py"
)

if __name__ == "__main__":
    if os.path.exists(TARGET_SCRIPT):
        # Add target dir to sys.path and execute
        sys.path.insert(0, os.path.dirname(TARGET_SCRIPT))
        import runpy
        runpy.run_path(TARGET_SCRIPT, run_name="__main__")
    else:
        print(f"Error: Could not locate {TARGET_SCRIPT}")
        sys.exit(1)
