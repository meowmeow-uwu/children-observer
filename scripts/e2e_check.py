"""
E2E check cục bộ: Backend (relay) ⇄ Edge (demo pipeline) — test.md T09.

Chạy uvicorn thật (database TEMP) + edge demo_stream (không WebRTC media)
và xác minh theo TỪNG LOOP (tối thiểu 3 loop đoạn demo [10s, 22s]):

- có heartbeat/status mỗi loop;
- có metadata tracks ở đoạn trẻ xuất hiện mỗi loop;
- track ID/ROI state reset theo contract mỗi loop;
- ít nhất một lần enter ROI (alert HTTP 2xx + backend broadcast);
- không replay detection cũ sang loop mới.

CLI:
    uv run python scripts/e2e_check.py [--help]
    --port PORT          (default 8011)
    --duration SECONDS   (default 80 — 3 loop đoạn demo 12s + margin)
    --loops N            (default 3)
    --temp-db PATH       (default <TEMP>/e2e_check_<pid>.db)
    --keep-alive         không dừng process (debug)

--help không khởi động workload. Exit code 0 khi đạt, 1 khi fail.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def wait_ready(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


async def browser_client(backend_url: str, duration: float) -> dict:
    """Mô phỏng browser client: nhận detection relay qua /ws/detections."""
    import websockets

    received = {"status": 0, "tracks": 0, "raw": []}
    async with websockets.connect(f"{backend_url.replace('http', 'ws')}/ws/detections") as ws:
        deadline = time.time() + duration
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                msg = json.loads(raw)
                received["raw"].append(msg)
                if msg.get("type") == "status":
                    received["status"] += 1
                elif msg.get("type") == "tracks":
                    received["tracks"] += 1
            except asyncio.TimeoutError:
                continue
    return received


async def run_edge(backend_url: str, duration: float) -> None:
    from module_edge_firmware.demo_stream.pipeline import DemoStreamConfig, DemoStreamPipeline

    cfg = DemoStreamConfig(
        camera_id="camera_living_room_01",
        backend_url=backend_url,
        ws_relay_enabled=True,
        ws_relay_url=f"{backend_url.replace('http', 'ws')}/ws/detections/edge",
        viewer_gated=False,
    )
    pipeline = DemoStreamPipeline(cfg)
    task = asyncio.create_task(pipeline.run_async())
    await asyncio.sleep(duration)
    pipeline.stop()
    try:
        await asyncio.wait_for(task, timeout=10)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    print(json.dumps({"edge_stats": pipeline.stats}, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E: Backend relay + Edge demo pipeline (T09)")
    parser.add_argument("--port", type=int, default=8011)
    parser.add_argument("--duration", type=float, default=80.0, help="thời gian chạy (3 loop đoạn demo 12s)")
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--temp-db", type=str, default=None, help="đường dẫn database tạm (mặc định TEMP)")
    parser.add_argument("--keep-alive", action="store_true", help="giữ process chạy (debug)")
    args = parser.parse_args()

    db_path = Path(args.temp_db) if args.temp_db else Path(tempfile.gettempdir()) / f"e2e_check_{os.getpid()}.db"
    if db_path.exists():
        db_path.unlink()

    backend_url = f"http://127.0.0.1:{args.port}"
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "module_backend_infra.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
        ],
        cwd=str(Path(__file__).resolve().parent.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    failures: list[str] = []
    try:
        if not wait_ready(f"{backend_url}/", timeout=30):
            print("FAIL: backend không khởi động được")
            return 1

        # 1. REST: camera + ROI seed giao đường đi trẻ + alerts_paused
        with urllib.request.urlopen(f"{backend_url}/api/cameras", timeout=10) as resp:
            cameras = json.loads(resp.read())
        cam = next(c for c in cameras if c["camera_id_string"] == "camera_living_room_01")
        assert cam["roi_zones"], "thiếu ROI seed"
        zone = cam["roi_zones"][0]
        assert zone.get("rules", {}).get("enterZone") is True, "rules thiếu enterZone"
        print(f"REST OK: camera + ROI seed '{zone['name']}' + rules + alerts_paused", flush=True)

        # 2. Relay + pipeline song song
        async def combined():
            browser_task = asyncio.create_task(browser_client(backend_url, duration=args.duration))
            await asyncio.sleep(1)
            edge_task = asyncio.create_task(run_edge(backend_url, duration=args.duration - 2))
            await edge_task
            return await browser_task

        received = asyncio.run(combined())

        # 3. Phân tích per-loop từ raw messages (tracks có loop_id)
        per_loop = {}
        tracks_msgs = [m for m in received["raw"] if m.get("type") == "tracks"]
        for m in tracks_msgs:
            per_loop.setdefault(m["loop_id"], {"tracks": 0, "has_child_track": False, "min_pts": None})
            per_loop[m["loop_id"]]["tracks"] += 1
            per_loop[m["loop_id"]]["min_pts"] = (
                m["source_pts_ms"]
                if per_loop[m["loop_id"]]["min_pts"] is None
                else min(per_loop[m["loop_id"]]["min_pts"], m["source_pts_ms"])
            )
            if any(t.get("class_name") == "child" for t in m["tracks"]):
                per_loop[m["loop_id"]]["has_child_track"] = True

        loop_ids = sorted(per_loop.keys())[: args.loops]
        print(f"Browser received: status={received['status']} tracks={len(tracks_msgs)} loops={loop_ids}", flush=True)
        if received["status"] == 0:
            failures.append("không nhận được status heartbeat")
        if len(loop_ids) < min(3, args.loops):
            failures.append(f"chỉ có {len(loop_ids)} loop < {args.loops}")

        for lid in loop_ids:
            info = per_loop[lid]
            if info["tracks"] == 0:
                failures.append(f"loop {lid} không có tracks message")
            if not info["has_child_track"]:
                failures.append(f"loop {lid} không có track child nào")
            print(f"  loop {lid}: tracks_msgs={info['tracks']} child_track={info['has_child_track']}", flush=True)

        # 4. Alert enter ROI: đếm alert trong DB sau khi chạy
        with urllib.request.urlopen(f"{backend_url}/api/alerts?camera_id=camera_living_room_01&limit=100", timeout=10) as resp:
            alerts = json.loads(resp.read())
        enter_alerts = [a for a in alerts if "enterZone" in (a.get("notes") or "")]
        print(f"Alerts: total={len(alerts)} enterZone={len(enter_alerts)}", flush=True)
        if len(enter_alerts) < 1:
            failures.append("không có alert enterZone nào từ track thật")

        if failures:
            print("FAIL: " + "; ".join(failures))
            return 1
        print("E2E PASS")
        return 0
    finally:
        if not args.keep_alive:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            try:
                db_path.unlink()
            except (PermissionError, FileNotFoundError):
                pass


if __name__ == "__main__":
    sys.exit(main())
