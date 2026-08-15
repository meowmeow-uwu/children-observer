import { useEffect, useRef } from "react";
import { useAlertStore } from "../store/alertStore";
import { useToast } from "../components/Toast";
import { useBrowserNotification } from "./useBrowserNotification";
import { fetchAlertsApi } from "../services/api";
import { buildSnapshotUrl } from "../services/api";
import { buildSignalingUrl } from "../services/webrtc";
import { useCameraStore } from "../store/cameraStore";
import type { Alert } from "../types";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 8000;
// Chỉ toast/browser-notification tối đa 1 lần cho cùng (camera, vùng) trong
// khoảng này — Edge phát lại alert mỗi vòng video demo (12.6s), tránh spam.
// Alert vẫn được lưu đầy đủ vào danh sách lịch sử.
const TOAST_DEDUPE_MS = 3000;

// ---- Helper map API alert → domain Alert ----

const mapApiAlert = (raw: Record<string, unknown>): Alert => ({
  id: String(raw.id ?? raw.alert_id ?? Date.now()),
  cameraId: String(raw.camera_id ?? raw.cameraId ?? ""),
  cameraName: String(raw.camera_name ?? raw.cameraName ?? ""),
  title: String(raw.title ?? "Cảnh báo"),
  severity: (["info", "warning", "danger"].includes(String(raw.severity))
    ? raw.severity
    : "danger") as Alert["severity"],
  status: (["unread", "checking", "resolved", "false_alarm"].includes(
    String(raw.status)
  )
    ? raw.status
    : "unread") as Alert["status"],
  // Task 4.2: Build URL đầy đủ cho snapshot từ backend
  snapshotUrl: buildSnapshotUrl(
    String(raw.snapshot_url ?? raw.snapshotUrl ?? "")
  ),
  roiName: String(raw.roi_name ?? raw.roiName ?? ""),
  createdAt: String(
    raw.created_at ?? raw.createdAt ?? new Date().toISOString()
  ),
  confidence: Number(raw.confidence ?? 0),
  channels: Array.isArray(raw.channels) ? raw.channels : [],
});

export const useRealtimeAlerts = (userId = "web_parent_01") => {
  const addAlert = useAlertStore((s) => s.addAlert);
  const setAlerts = useAlertStore((s) => s.setAlerts);
  const { showToast } = useToast();
  const { showNotification } = useBrowserNotification();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  const generationRef = useRef(0);
  const lastToastAtRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    // Generation guard: chỉ effect hiện tại mới có quyền kết nối
    const gen = ++generationRef.current;
    let reconnectAttempt = 0;

    // ---- Kết nối WebSocket nhận tin nhắn Cảnh báo Thời gian thực ----
    const connect = () => {
      if (gen !== generationRef.current) return;

      // buildSignalingUrl đã tự gắn ?token=JWT theo Task 3.1
      const wsUrl = buildSignalingUrl(userId);
      let ws: WebSocket | null = null;
      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        console.warn("[useRealtimeAlerts] Không thể kết nối WebSocket:", e);
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt = 0;
        console.debug("[useRealtimeAlerts] WebSocket connected:", wsUrl);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string);

          // ---- Task 4.1: Lắng nghe "ALERT_NEW" theo đặc tả WebSocket spec ----
          // Spec: { "type": "ALERT_NEW", "data": { id, camera_id, title, severity, snapshot_url, roi_name, ... } }
          // Backward-compat: cũng hỗ trợ "new_alert" từ demo cũ
          const isSpecAlert = msg.type === "ALERT_NEW" && msg.data;
          const isDemoAlert = msg.type === "new_alert" && msg.alert;

          if (isSpecAlert || isDemoAlert) {
            // Normalize: spec dùng msg.data, demo cũ dùng msg.alert
            const rawAlert = isSpecAlert ? msg.data : msg.alert;
            const newAlert = mapApiAlert(rawAlert as Record<string, unknown>);

            // Luôn ghi vào store lịch sử
            addAlert(newAlert);

            // Chỉ toast khi camera đang stream (tránh cảnh báo đi trước hình ảnh)
            const camera = useCameraStore
              .getState()
              .cameras.find((c) => c.id === newAlert.cameraId);
            if (camera?.streamStatus !== "connected") return;

            // Dedupe toast theo (camera, vùng, tiêu đề) — không spam
            const toastKey = `${newAlert.cameraId}|${newAlert.roiName}|${newAlert.title}`;
            const now = Date.now();
            const lastToast = lastToastAtRef.current.get(toastKey) ?? 0;
            if (now - lastToast < TOAST_DEDUPE_MS) return;
            lastToastAtRef.current.set(toastKey, now);

            // Dọn map cũ để không phình vô hạn
            if (lastToastAtRef.current.size > 50) {
              const expired = [...lastToastAtRef.current.entries()].filter(
                ([, t]) => now - t > TOAST_DEDUPE_MS * 2
              );
              expired.forEach(([k]) => lastToastAtRef.current.delete(k));
            }

            // 🔊 Toast + 🔔 Browser Notification
            const icon = newAlert.severity === "danger" ? "🚨" : "⚠️";
            showToast(
              `${icon} ${newAlert.title}`,
              newAlert.severity === "danger" ? "error" : "warning"
            );
            showNotification(`🚨 ${newAlert.title}`, {
              body: `Camera ${newAlert.cameraName} phát hiện vi phạm vùng nguy hiểm${newAlert.roiName ? ` "${newAlert.roiName}"` : ""}.`,
            });

          } else if (msg.type === "alerts_cleared") {
            lastToastAtRef.current.clear();
            setAlerts([]);
          }
        } catch (e) {
          console.error("[useRealtimeAlerts] Lỗi xử lý WS message:", e);
        }
      };

      // Reconnect với exponential backoff (1s, 2s, 4s, 8s)
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (gen !== generationRef.current) return;
        const delay = Math.min(
          RECONNECT_MAX_MS,
          RECONNECT_BASE_MS * Math.pow(2, reconnectAttempt)
        );
        reconnectAttempt += 1;
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
      ws.onerror = () => {
        ws?.close();
      };
    };

    // ---- Bootstrap: fetch lịch sử alerts từ backend, rồi mở WS ----
    const bootstrap = async () => {
      // Task 4.3: Lấy lịch sử cảnh báo từ GET /api/alerts/
      const data = await fetchAlertsApi();
      if (gen !== generationRef.current) return;
      if (Array.isArray(data)) {
        setAlerts(
          data.map((item) =>
            mapApiAlert(item as unknown as Record<string, unknown>)
          )
        );
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
