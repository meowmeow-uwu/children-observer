import { useEffect } from "react";
import { useAlertStore } from "../store/alertStore";
import { useToast } from "../components/Toast";
import { useBrowserNotification } from "./useBrowserNotification";
import { fetchAlertsApi } from "../services/api";
import { buildSignalingUrl } from "../services/webrtc";

export const useRealtimeAlerts = (userId = "user_guardian_01") => {
  const { addAlert, setAlerts } = useAlertStore();
  const { showToast } = useToast();
  const { showNotification } = useBrowserNotification();

  useEffect(() => {
    // 1. Tải danh sách Cảnh báo ban đầu từ Backend REST API
    fetchAlertsApi().then((data) => {
      if (Array.isArray(data) && data.length > 0) {
        const formattedAlerts = data.map((item: any) => ({
          id: String(item.id),
          cameraId: item.camera_id || item.cameraId,
          cameraName: item.camera_name || item.cameraName || "Phòng khách",
          title: item.title,
          severity: item.severity || "warning",
          status: item.status || "unread",
          snapshotUrl: item.snapshot_url || item.snapshotUrl || "",
          roiName: item.roi_name || item.roiName || "",
          createdAt: item.created_at || item.createdAt || new Date().toISOString()
        }));
        setAlerts(formattedAlerts);
      }
    });

    // 2. Kết nối WebSocket nhận tin nhắn Cảnh báo Thời gian thực từ Server
    const wsUrl = buildSignalingUrl(userId);
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "new_alert" && msg.alert) {
            const newAlert = msg.alert;
            
            // Thêm vào Zustand store
            addAlert({
              id: String(newAlert.id),
              cameraId: newAlert.cameraId,
              cameraName: newAlert.cameraName,
              title: newAlert.title,
              severity: newAlert.severity || "danger",
              status: newAlert.status || "unread",
              snapshotUrl: newAlert.snapshotUrl || "",
              roiName: newAlert.roiName || "",
              createdAt: newAlert.createdAt || new Date().toISOString()
            });

            // Hiển thị Toast thông báo nổi bật
            const iconStr = newAlert.severity === "danger" ? "🚨" : "⚠️";
            showToast(`${iconStr} ${newAlert.title}`, newAlert.severity === "danger" ? "error" : "warning");

            // Bật thông báo Trình duyệt (Desktop Notification)
            showNotification(`🚨 ${newAlert.title}`, {
              body: `Camera ${newAlert.cameraName} phát hiện vi phạm vùng nguy hiểm ${newAlert.roiName || ''}.`
            });
          }
        } catch (e) {
          console.error("Lỗi xử lý tin nhắn cảnh báo WebSocket:", e);
        }
      };
    } catch (e) {
      console.warn("Không thể kết nối WebSocket thông báo:", e);
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [userId, addAlert, setAlerts, showToast, showNotification]);
};

export default useRealtimeAlerts;
