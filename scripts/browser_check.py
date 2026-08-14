"""
Browser functional check (test.md T08) — chạy headless Chrome + CDP.

Khởi động Chrome headless với remote debugging, vào camera demo, kiểm tra:
- video WebRTC thật phát (readyState, currentTime tăng, videoWidth 1920x1080);
- bounding box SVG xuất hiện khi trẻ vào đoạn demo (không phải mock);
- ROI polygon render đúng trên video;
- console không có error/unhandled rejection;
- đúng số WebSocket (alerts + signaling), không request loop;
- resize viewport desktop → mobile không vỡ overlay, không lỗi mới;
- screenshot desktop 1440x900 và mobile 390x844.

CLI:
    uv run python scripts/browser_check.py [--help]
    --url URL            (default http://localhost:5173)
    --chrome PATH        (default: đường dẫn Chrome tự dò)
    --duration SECONDS   thời gian quan sát video (default 30)
    --shots-dir PATH     nơi lưu screenshot (default <TEMP>/browser_shots)

Exit 0 khi đạt, 1 khi fail. --help không khởi động workload.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    which = shutil.which("chrome") or shutil.which("chromium")
    if which:
        return which
    raise FileNotFoundError("Không tìm thấy Chrome/Chromium")


class CDP:
    def __init__(self, ws_url: str):
        from concurrent.futures import Future
        from websockets.sync.client import connect

        self._Future = Future
        self._ws = connect(ws_url)
        self._id = 0
        self._pending: dict[int, Future] = {}
        self._events: list[dict] = []
        import threading

        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            try:
                msg = json.loads(self._ws.recv())
            except Exception:
                return
            if "id" in msg:
                fut = self._pending.pop(msg["id"], None)
                if fut is not None:
                    fut.set_result(msg)
            else:
                self._events.append(msg)

    def send(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        fut = self._Future()
        self._pending[self._id] = fut
        self._ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        msg = fut.result(timeout=30)
        if "error" in msg:
            raise RuntimeError(f"CDP {method} error: {msg['error']}")
        return msg.get("result", {})

    def drain_events(self) -> list[dict]:
        events = list(self._events)
        self._events.clear()
        return events

    def evaluate(self, expr: str) -> dict:
        return self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass


def connect_page(port: int) -> CDP:
    deadline = time.time() + 30
    last_err = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as resp:
                targets = json.loads(resp.read())
            page = next((t for t in targets if t.get("type") == "page"), None)
            if page:
                return CDP(page["webSocketDebuggerUrl"])
        except Exception as exc:
            last_err = repr(exc)
            time.sleep(0.5)
    raise TimeoutError(f"Chrome CDP không sẵn sàng (last: {last_err})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Browser functional check (T08)")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--chrome", default=None)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--shots-dir", default=None)
    parser.add_argument("--cdp-port", type=int, default=0)  # 0 = random để tránh xung đột
    args = parser.parse_args()

    chrome = args.chrome or find_chrome()
    cdp_port = args.cdp_port or (9000 + os.getpid() % 400)
    user_data = Path(tempfile.gettempdir()) / f"chrome-demo-{os.getpid()}"
    shots_dir = Path(args.shots_dir) if args.shots_dir else Path(tempfile.gettempdir()) / "browser_shots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={cdp_port}",
            f"--user-data-dir={user_data}",
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run",
            "--disable-gpu",
            "--use-fake-ui-for-media-stream",
            "--window-size=1440,900",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    failures: list[str] = []
    console_errors: list[str] = []
    ws_connections: list[str] = []
    fetch_log: list[str] = []

    try:
        cdp = connect_page(cdp_port)
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        cdp.send("Log.enable")
        cdp.send("Network.enable")

        # Collect console + network (reader thread đẩy vào cdp._events)
        def _collect():
            for msg in cdp.drain_events():
                method = msg.get("method", "")
                if method == "Runtime.consoleAPICalled":
                    if msg.get("params", {}).get("type") == "error":
                        args_ = msg["params"].get("args", [])
                        console_errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in args_))
                elif method == "Runtime.exceptionThrown":
                    d = msg.get("params", {}).get("exceptionDetails", {})
                    console_errors.append("exception: " + d.get("text", ""))
                elif method == "Log.entryAdded":
                    if msg.get("params", {}).get("entry", {}).get("level") in ("error",):
                        console_errors.append("log: " + str(msg["params"]["entry"].get("text", "")))
                elif method == "Network.webSocketCreated":
                    ws_connections.append(msg["params"].get("url", ""))
                elif method == "Network.requestWillBeSent":
                    url = msg.get("params", {}).get("request", {}).get("url", "")
                    if "/api/" in url:
                        fetch_log.append(url)

        import threading

        def _collector_loop():
            while True:
                time.sleep(0.3)
                try:
                    _collect()
                except Exception:
                    return

        threading.Thread(target=_collector_loop, daemon=True).start()

        # 1. Auth mock (chèn TRƯỚC khi script chạy) + vào trang camera
        cdp.send(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """localStorage.setItem('safekid_token','demo');
                localStorage.setItem('safekid_user', JSON.stringify({id:'web_parent_01', name:'Demo', email:'demo@x', role:'parent'}));"""
            },
        )
        cdp.send("Page.navigate", {"url": args.url + "/#/cameras/camera_living_room_01"})
        time.sleep(5)

        # 2. Đợi WebRTC connected (click Play nếu idle) — tối đa 90s
        deadline = time.time() + 90
        connected = False
        while time.time() < deadline:
            res = cdp.evaluate(
                """(() => {
                    const v = document.querySelector('video');
                    if (!v) return 'no_video';
                    if (v.paused && v.currentTime === 0) {
                        const btn = document.querySelector('button[aria-label="Bắt đầu xem trực tiếp"]');
                        if (btn) btn.click();
                        return 'idle_clicked';
                    }
                    return v.readyState >= 2 && v.currentTime > 0 ? 'playing' : 'connecting';
                })()"""
            )
            state = res.get("result", {}).get("value", "")
            if state == "playing":
                connected = True
                break
            time.sleep(1)

        if not connected:
            failures.append("video WebRTC không phát được trong 90s")

        # 3. Quan sát video + box trong --duration
        boxes_seen = 0
        roi_seen = False
        video_info = {}
        connecting_overlap = 0
        deadline = time.time() + args.duration
        while time.time() < deadline:
            res = cdp.evaluate(
                """(() => {
                    const v = document.querySelector('video');
                    // Box track: rect xanh/đỏ của track (stroke #22c55e/#ef4444),
                    // KHÔNG tính stats panel (fill rgba(0,0,0,0.6) ở góc trên phải).
                    const trackBoxes = [...document.querySelectorAll('svg rect')].filter(r => {
                        const s = (r.getAttribute('stroke') || '').toLowerCase();
                        const fill = (r.getAttribute('fill') || '');
                        return (s === '#22c55e' || s === '#ef4444') && !fill.includes('0.6');
                    });
                    const rois = [...document.querySelectorAll('svg polygon')];
                    return {
                        readyState: v ? v.readyState : -1,
                        currentTime: v ? v.currentTime : -1,
                        videoWidth: v ? v.videoWidth : 0,
                        videoHeight: v ? v.videoHeight : 0,
                        trackBoxes: trackBoxes.length,
                        polygons: rois.length,
                        spinner: document.body.innerText.includes('Đang kết nối luồng camera'),
                        playing: !!(v && !v.paused && v.currentTime > 0),
                    };
                })()"""
            )
            info = res.get("result", {}).get("value", {})
            video_info = info
            if info.get("trackBoxes", 0) > 0:
                boxes_seen += 1
            if info.get("polygons", 0) > 0:
                roi_seen = True
            # Mô phỏng đúng như camera thật: KHÔNG được vừa "đang kết nối"
            # vừa có video chạy
            if info.get("spinner") and info.get("playing"):
                connecting_overlap += 1
            time.sleep(0.5)
        if connecting_overlap > 0:
            failures.append(f"UI vừa hiển thị 'đang kết nối' vừa chạy video ({connecting_overlap} mẫu) — phải che video khi chưa connected")

        if not video_info.get("videoWidth"):
            failures.append("video không có kích thước (WebRTC track không bám)")
        else:
            w, h = video_info["videoWidth"], video_info["videoHeight"]
            if not (w == 1920 and h == 1080):
                failures.append(f"video size lạ: {w}x{h} (kỳ vọng 1920x1080)")
        if boxes_seen == 0:
            failures.append(f"không thấy bounding box SVG nào trong {args.duration}s")
        if not roi_seen:
            failures.append("không thấy ROI polygon nào")

        # 3b. Box label + vị trí hợp lệ (retry tới khi trẻ vào khung trong loop)
        dom_info = {"labels": [], "boxes": []}
        deadline = time.time() + 20
        while time.time() < deadline and not dom_info.get("labels"):
            res = cdp.evaluate(
                """(() => {
                    const texts = [...document.querySelectorAll('svg text')].map(t => t.textContent);
                    const labels = texts.filter(t => t.includes('Trẻ #'));
                    const rects = [...document.querySelectorAll('svg rect')].filter(r => {
                        const s = (r.getAttribute('stroke') || '').toLowerCase();
                        return (s === '#22c55e' || s === '#ef4444');
                    });
                    const coords = rects.slice(0, 3).map(r => ({
                        x: parseFloat(r.getAttribute('x')),
                        y: parseFloat(r.getAttribute('y')),
                        w: parseFloat(r.getAttribute('width')),
                        h: parseFloat(r.getAttribute('height')),
                    }));
                    return { labels: labels.slice(0, 3), boxes: coords };
                })()"""
            )
            dom_info = res.get("result", {}).get("value", {})
            if not dom_info.get("labels"):
                time.sleep(0.5)
        if not dom_info.get("labels"):
            failures.append("không thấy label 'Trẻ #' trên box trong 20s (trẻ xuất hiện mỗi loop ~2.7s)")
        else:
            bad = [b for b in dom_info.get("boxes", []) if not (0 <= b["x"] < 1000 and 0 <= b["y"] < 1000 and b["w"] > 0 and b["h"] > 0)]
            if bad:
                failures.append(f"box nằm ngoài viewBox: {bad[:2]}")
        print(json.dumps({"box_dom": dom_info}, ensure_ascii=False))

        # 3c. Pause alerts interaction: bấm nút → API POST + trạng thái thay đổi
        res = cdp.evaluate(
            """(() => {
                const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Tạm dừng cảnh báo'));
                if (btn) { btn.click(); return 'clicked'; }
                return 'no_btn';
            })()"""
        )
        if res.get("result", {}).get("value") == "clicked":
            time.sleep(3)
            res = cdp.evaluate(
                """(() => {
                    const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('cảnh báo'));
                    return btn ? btn.textContent.trim() : 'none';
                })()"""
            )
            pause_text = res.get("result", {}).get("value", "")
            if "Kích hoạt lại" not in pause_text:
                failures.append(f"nút pause không đổi trạng thái sau khi bấm: '{pause_text}'")
            else:
                paused_posted = any("alerts-paused" in u for u in fetch_log)
                if not paused_posted:
                    failures.append("không thấy POST alerts-paused từ nút pause")
            # Resume để demo tiếp tục
            cdp.evaluate(
                """(() => { const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Kích hoạt lại'));
                if (btn) btn.click(); return 'ok'; })()"""
            )
            time.sleep(2)

        # 4. Screenshot desktop
        shot = cdp.send("Page.captureScreenshot", {"format": "png"})
        (shots_dir / "desktop_1440x900.png").write_bytes(base64.b64decode(shot["data"]))

        # 5. Resize mobile + chụp
        cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True,
        })
        time.sleep(3)
        res = cdp.evaluate(
            """(() => { const v = document.querySelector('video');
            return { playing: v && !v.paused && v.currentTime > 0, boxes: document.querySelectorAll('svg rect').length,
                     rois: document.querySelectorAll('svg polygon').length }; })()"""
        )
        mobile = res.get("result", {}).get("value", {})
        shot = cdp.send("Page.captureScreenshot", {"format": "png"})
        (shots_dir / "mobile_390x844.png").write_bytes(base64.b64decode(shot["data"]))
        if not mobile.get("playing"):
            failures.append("video dừng khi resize mobile")
        cdp.send("Emulation.clearDeviceMetricsOverride")

        # 6. Tổng kết console/network
        real_errors = [e for e in console_errors if "favicon" not in e.lower()]
        if real_errors:
            failures.append(f"console errors: {real_errors[:5]}")
        api_calls = [u for u in fetch_log if "/api/alerts" in u]
        if len(set(api_calls)) > 3:
            failures.append(f"alerts API gọi lặp: {len(set(api_calls))} lần (storm?)")

        # 7. Re-entry: rời trang rồi quay lại → kết nối MỚI + video chạy lại từ đầu
        # (đếm theo LIST — các kết nối cùng URL không bị dedupe bằng set)
        sig_before = len([u for u in ws_connections if "/ws/signaling/web_parent_01" in u])
        cdp.evaluate("location.hash = '#/dashboard';")
        time.sleep(2)
        res = cdp.evaluate(
            """(() => {
                const text = document.body.innerText;
                const previews = [...document.querySelectorAll('img[alt^="Ảnh xem trước"]')];
                const alertImages = [...document.querySelectorAll('img[alt="Snapshot Cảnh báo"]')];
                return {
                    readyBadges: (text.match(/Sẵn sàng|Đang xem Live/g) || []).length,
                    connectingStates: (text.match(/Đang kết nối/g) || []).length,
                    failedStates: (text.match(/Lỗi kết nối/g) || []).length,
                    offlineStates: (text.match(/Ngoại tuyến/g) || []).length,
                    disconnectedLabels: (text.match(/Chưa kết nối/g) || []).length,
                    previews: previews.length,
                    brokenPreviews: previews.filter(img => !img.complete || img.naturalWidth === 0).length,
                    alertImages: alertImages.length,
                    brokenAlertImages: alertImages.filter(img => !img.complete || img.naturalWidth === 0).length,
                };
            })()"""
        )
        dashboard = res.get("result", {}).get("value", {})
        if dashboard.get("readyBadges", 0) != 1:
            failures.append("Dashboard phải có đúng một camera Phòng khách sẵn sàng")
        if dashboard.get("connectingStates", 0) == 0 or dashboard.get("failedStates", 0) == 0 or dashboard.get("offlineStates", 0) == 0:
            failures.append(f"Dashboard chưa mô phỏng đủ trạng thái camera: {dashboard}")
        if dashboard.get("disconnectedLabels", 0) > 0:
            failures.append("Dashboard vẫn hiển thị camera online là 'Chưa kết nối'")
        if dashboard.get("previews", 0) != 1 or dashboard.get("brokenPreviews", 0) > 0:
            failures.append(f"Ảnh xem trước camera lỗi: {dashboard}")
        if dashboard.get("alertImages", 0) > 0 and dashboard.get("brokenAlertImages", 0) > 0:
            failures.append(f"Ảnh cảnh báo không tải được: {dashboard}")
        cdp.evaluate("location.hash = '#/cameras/camera_living_room_01';")
        reentry = {"readyState": -1, "playing": False}
        deadline = time.time() + 15
        while time.time() < deadline:
            time.sleep(1)
            res = cdp.evaluate(
                """(() => { const v = document.querySelector('video');
                return { readyState: v ? v.readyState : -1, playing: !!(v && !v.paused && v.currentTime > 0) }; })()"""
            )
            reentry = res.get("result", {}).get("value", {})
            if reentry.get("playing"):
                break
        time.sleep(1)
        sig_after = len([u for u in ws_connections if "/ws/signaling/web_parent_01" in u])
        if not reentry.get("playing"):
            failures.append("video không phát lại sau khi quay lại trang camera")
        if sig_after != sig_before + 1:
            failures.append(
                f"quay lại trang không tạo kết nối MỚI ({sig_before}→{sig_after}) — video sẽ chiếu tiếp ở đoạn giữa chừng"
            )

        # 8. Trang vẽ ROI: ảnh tĩnh + không có detection overlay
        cdp.evaluate("location.hash = '#/roi/camera_living_room_01?mode=new';")
        deadline = time.time() + 20
        static_ok = False
        while time.time() < deadline:
            res = cdp.evaluate(
                """(() => {
                    const img = document.querySelector('img[src^="data:image"]');
                    const drawSvg = !!document.querySelector('svg[viewBox="0 0 1000 1000"]');
                    const labels = [...document.querySelectorAll('svg text')].some(t => t.textContent.includes('Trẻ #'));
                    return { hasStatic: !!img, drawSvg, hasDetLabels: labels };
                })()"""
            )
            info = res.get("result", {}).get("value", {})
            if info.get("hasStatic") and info.get("drawSvg"):
                static_ok = True
                if info.get("hasDetLabels"):
                    failures.append("trang vẽ ROI vẫn hiển thị detection box (phải là ảnh tĩnh)")
                break
            time.sleep(0.5)
        if not static_ok:
            failures.append("trang vẽ ROI không hiển thị ảnh tĩnh để vẽ")
        else:
            print(json.dumps({"roi_static": info}, ensure_ascii=False))

        # 9. Refresh thường phải giữ đúng Dashboard mới (không dính PWA cache cũ).
        cdp.evaluate("location.hash = '#/dashboard';")
        time.sleep(2)
        cdp.evaluate("location.reload();")
        time.sleep(4)
        res = cdp.evaluate(
            """(() => {
                const text = document.body.innerText;
                return {
                    ready: (text.match(/Sẵn sàng|Đang xem Live/g) || []).length,
                    connecting: (text.match(/Đang kết nối/g) || []).length,
                    failed: (text.match(/Lỗi kết nối/g) || []).length,
                    offline: (text.match(/Ngoại tuyến/g) || []).length,
                    staleDisconnected: (text.match(/Chưa kết nối/g) || []).length,
                };
            })()"""
        )
        normal_refresh = res.get("result", {}).get("value", {})
        if (
            normal_refresh.get("ready") != 1
            or normal_refresh.get("connecting", 0) == 0
            or normal_refresh.get("failed", 0) == 0
            or normal_refresh.get("offline", 0) == 0
            or normal_refresh.get("staleDisconnected", 0) > 0
        ):
            failures.append(f"Refresh thường trả lại Dashboard cũ: {normal_refresh}")

        print(json.dumps({
            "video": video_info,
            "boxes_seen_samples": boxes_seen,
            "roi_seen": roi_seen,
            "mobile": mobile,
            "reentry": reentry,
            "dashboard": dashboard,
            "normal_refresh": normal_refresh,
            "signaling_sockets": {"before": sig_before, "after": sig_after},
            "console_errors": real_errors[:10],
            "ws_connections": sorted(set(ws_connections)),
            "api_fetches": sorted(set(fetch_log)),
            "screenshots": [str(shots_dir / "desktop_1440x900.png"), str(shots_dir / "mobile_390x844.png")],
        }, indent=2, ensure_ascii=False))

        if failures:
            print("FAIL: " + "; ".join(failures))
            return 1
        print("BROWSER CHECK PASS")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(user_data, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
