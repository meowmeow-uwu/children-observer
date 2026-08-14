import { useEffect, useRef } from "react";
import { useAlertStore } from "../store/alertStore";
import { useToast } from "../components/Toast";
import { useBrowserNotification } from "./useBrowserNotification";
import { clearAlertsApi, fetchAlertsApi } from "../services/api";
import { buildSignalingUrl } from "../services/webrtc";
import { useCameraStore } from "../store/cameraStore";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 8000;
// Chỉ toast/browser-notification tối đa 1 lần cho cùng (camera, vùng) trong
// khoảng này — Edge phát lại alert mỗi vòng video demo (12.6s), tránh spam
// "vẫn cứ hiện thông báo". Alert vẫn được lưu đầy đủ vào danh sách lịch sử.
// Edge đã lọc transition outside→inside. Frontend chỉ chặn duplicate WS sát
// nhau, không được che các lần trẻ thực sự quay lại ROI trong video demo 26.9s.
const TOAST_DEDUPE_MS = 3000;

// Một lần duy nhất trong mỗi document JS. Mở web/reload tạo runtime mới nên
// reset lại; điều hướng SPA và StrictMode remount không xóa lần thứ hai.
let pageLoadAlertReset: Promise<boolean> | null = null;
const resetAlertsOncePerPageLoad = () => {
  if (!pageLoadAlertReset) pageLoadAlertReset = clearAlertsApi();
  return pageLoadAlertReset;
};

export const useRealtimeAlerts = (userId = "user_guardian_01") => {
  // Zustand selector — chỉ subscribe action ổn định, không cả state
  const addAlert = useAlertStore((s) => s.addAlert);
  const setAlerts = useAlertStore((s) => s.setAlerts);
  const { showToast } = useToast(); // đã memoized (useCallback)
  const { showNotification } = useBrowserNotification(); // đã memoized

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  const generationRef = useRef(0);
  const lastToastAtRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    // Generation guard: callback/timer của effect cũ không được kết nối lại
    // sau StrictMode remount — chỉ effect hiện tại mới có quyền kết nối.
    const gen = ++generationRef.current;
    let reconnectAttempt = 0;

    // Kết nối WebSocket nhận tin nhắn Cảnh báo Thời gian thực
    const connect = () => {
      if (gen !== generationRef.current) return;

      const wsUrl = buildSignalingUrl(userId);
      let ws: WebSocket | null = null;
      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        console.warn("Không thể kết nối WebSocket thông báo:", e);
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "alerts_cleared") {
            lastToastAtRef.current.clear();
            setAlerts([]);
          } else if (msg.type === "new_alert" && msg.alert) {
            const newAlert = msg.alert;

            addAlert({
              id: String(newAlert.id),
              cameraId: newAlert.cameraId,
              cameraName: newAlert.cameraName || "",
              title: newAlert.title,
              severity: newAlert.severity || "danger",
              status: newAlert.status || "unread",
              snapshotUrl: newAlert.snapshotUrl || "/test_video_thumb.jpg",
              roiName: newAlert.roiName || "",
              createdAt: newAlert.createdAt || new Date().toISOString(),
              confidence: newAlert.confidence || 0,
              channels: newAlert.channels || []
            });

            // Lưu lịch sử thật nhưng chỉ toast cảnh báo live khi video của
            // chính camera đó đã kết nối. Tránh cảnh báo đi trước hình ảnh.
            const camera = useCameraStore
              .getState()
              .cameras.find((item) => item.id === newAlert.cameraId);
            if (camera?.streamStatus !== "connected") return;

            // Dedupe toast theo (camera, vùng) — không spam, vẫn ghi lịch sử
            const toastKey = `${newAlert.cameraId}|${newAlert.roiName || ""}|${newAlert.title}`;
            const now = Date.now();
            const lastToast = lastToastAtRef.current.get(toastKey) || 0;
            if (now - lastToast < TOAST_DEDUPE_MS) return;
            lastToastAtRef.current.set(toastKey, now);
            // Dọn map cũ để không phình vô hạn
            if (lastToastAtRef.current.size > 50) {
              const expired = [...lastToastAtRef.current.entries()].filter(([, t]) => now - t > TOAST_DEDUPE_MS * 2);
              expired.forEach(([k]) => lastToastAtRef.current.delete(k));
            }

            const iconStr = newAlert.severity === "danger" ? "🚨" : "⚠️";
            showToast(`${iconStr} ${newAlert.title}`, newAlert.severity === "danger" ? "error" : "warning");

            showNotification(`🚨 ${newAlert.title}`, {
              body: `Camera ${newAlert.cameraName || ""} phát hiện vi phạm vùng nguy hiểm ${newAlert.roiName || ''}.`
            });
          }
        } catch (e) {
          console.error("Lỗi xử lý tin nhắn cảnh báo WebSocket:", e);
        }
      };

      // Reconnect với backoff (1s, 2s, 4s, 8s) + generation guard — chỉ một timer
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (gen !== generationRef.current) return;
        const delay = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * Math.pow(2, reconnectAttempt));
        reconnectAttempt += 1;
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
      ws.onerror = () => {
        ws?.close();
      };
    };

    const bootstrap = async () => {
      // Xóa backend trước, sau đó mới fetch và mở WS để không hồi sinh alert cũ.
      await resetAlertsOncePerPageLoad();
      if (gen !== generationRef.current) return;
      setAlerts([]);

      const data = await fetchAlertsApi();
      if (gen !== generationRef.current) return;
      if (Array.isArray(data)) {
        setAlerts(data.map((item: any) => ({
          id: String(item.id),
          cameraId: item.camera_id || item.cameraId,
          cameraName: item.camera_name || item.cameraName || "",
          title: item.title,
          severity: item.severity || "warning",
          status: item.status || "unread",
          snapshotUrl: item.snapshot_url || item.snapshotUrl || "/test_video_thumb.jpg",
          roiName: item.roi_name || item.roiName || "",
          createdAt: item.created_at || item.createdAt || new Date().toISOString(),
          confidence: item.confidence || 0,
          channels: item.channels || []
        })));
      }
      connect();
    };
    void bootstrap();

    return () => {
      generationRef.current += 1; // vô hiệu hoá mọi callback/timer cũ
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = undefined;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [userId, addAlert, setAlerts, showToast, showNotification]);

  return null;
};

export default useRealtimeAlerts;
