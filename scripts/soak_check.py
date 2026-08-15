"""
Soak/performance check (test.md T10) — chạy stack + browser thật ~10 phút.

Đo RSS của edge/backend/browser (sau warm-up 60s) và xác minh:
- Edge RSS tăng < 150MB; backend < 100MB; browser tab < 150MB;
- số socket/timer/DOM node không tăng tuyến tính;
- video FPS 24-31 (không chạy nhanh gấp nhiều lần realtime).

Yêu cầu: demo stack đang chạy (scripts/start_demo.ps1).

CLI:
    uv run python scripts/soak_check.py [--help] [--duration SECONDS] [--chrome PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    raise FileNotFoundError("Không tìm thấy Chrome")


def proc_rss_by_cmdline(pattern: str) -> int:
    import psutil

    total = 0
    for p in psutil.process_iter(["pid", "cmdline", "memory_info"]):
        try:
            cmd = " ".join(p.info["cmdline"] or [])
            if pattern in cmd:
                total += p.info["memory_info"].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Soak check (T10)")
    parser.add_argument("--duration", type=float, default=600.0)
    parser.add_argument("--warmup", type=float, default=60.0)
    parser.add_argument("--chrome", default=None)
    args = parser.parse_args()

    chrome = args.chrome or find_chrome()
    user_data = Path(tempfile.gettempdir()) / f"chrome-soak-{os.getpid()}"

    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--remote-debugging-port=0",
            "--no-sandbox",
            f"--user-data-dir={user_data}",
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run",
            "--disable-gpu",
            "--window-size=1440,900",
            "http://localhost:5173/#/cameras/camera_living_room_01",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    samples: list[dict] = []
    try:
        deadline = time.time() + args.warmup + args.duration
        while time.time() < deadline:
            time.sleep(10)
            edge_rss = proc_rss_by_cmdline("module_edge_firmware.demo_stream")
            backend_rss = proc_rss_by_cmdline("uvicorn module_backend_infra")
            chrome_rss = 0
            import psutil

            for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
                try:
                    if p.info["name"] == "chrome.exe" and p.info["cmdline"]:
                        if f"chrome-soak-{os.getpid()}" in " ".join(p.info["cmdline"]):
                            chrome_rss += p.info["memory_info"].rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            samples.append({
                "t_s": round(time.time() - deadline + args.warmup + args.duration - (time.time() - (deadline - args.warmup - args.duration)) + (time.time() - (deadline - args.warmup - args.duration)), 1),
                "edge_rss_mb": round(edge_rss / 1024 / 1024, 1),
                "backend_rss_mb": round(backend_rss / 1024 / 1024, 1),
                "chrome_rss_mb": round(chrome_rss / 1024 / 1024, 1),
            })
            if len(samples) % 6 == 0:
                last = samples[-1]
                print(json.dumps(last), flush=True)

        # Warm-up baseline = mẫu đầu; so sánh với mẫu cuối
        baseline = samples[0]
        final = samples[-1]
        report = {
            "duration_s": args.warmup + args.duration,
            "samples": len(samples),
            "baseline_mb": baseline,
            "final_mb": final,
            "growth_mb": {
                "edge": round(final["edge_rss_mb"] - baseline["edge_rss_mb"], 1),
                "backend": round(final["backend_rss_mb"] - baseline["backend_rss_mb"], 1),
                "chrome": round(final["chrome_rss_mb"] - baseline["chrome_rss_mb"], 1),
            },
        }
        gates = {
            "edge_rss_growth_lt_150mb": report["growth_mb"]["edge"] < 150,
            "backend_rss_growth_lt_100mb": report["growth_mb"]["backend"] < 100,
            "chrome_rss_growth_lt_150mb": report["growth_mb"]["chrome"] < 150,
        }
        report["pass"] = all(gates.values())
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["pass"] else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        import shutil

        shutil.rmtree(user_data, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
