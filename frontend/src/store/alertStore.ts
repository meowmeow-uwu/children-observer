import { create } from "zustand";
import type { Alert, AlertStatus } from "../types";

interface AlertState {
  alerts: Alert[];
  selectedAlertId: string | null;
  filterStatus: AlertStatus | "all";
  filterSeverity: Alert["severity"] | "all";
  
  // Actions
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  selectAlert: (alertId: string | null) => void;
  updateAlertStatus: (alertId: string, status: AlertStatus, extra?: Partial<Alert>) => void;
  setFilterStatus: (status: AlertStatus | "all") => void;
  setFilterSeverity: (severity: Alert["severity"] | "all") => void;
}

const mockAlerts: Alert[] = [
  {
    id: "alert_001",
    cameraId: "camera_balcony_01",
    cameraName: "Ban công",
    roiId: "roi_balcony_01",
    roiName: "Ranh giới Lan can",
    title: "Phát hiện trẻ đi vào vùng nguy hiểm tại Ban công",
    severity: "danger",
    status: "unread",
    confidence: 0.98,
    snapshotUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuA-gRJDo3RZwsRoKLv_AyTihL94GeNsmph4WAGuy8d7pd7YLRV8kv7A5oExq5IlszdREk7kNbqsaDk9wnqU_fDe0HyyShBOo3rjHEO1fhK08Gt6AZklNZVVSPV97lX3kJ5sr8DV37_1Th6LvOjtLAFauac-uaNMGNZzk33P3-pA1BfL0lkcUFLkHRC3RNB9uMtMGh2VAy1Oi6a0k2XHDuFnTV-ssSvU1z2vcSKWwlLaSKCSwFc8-FvJG1PKbOcwVgsZmeaoVFhz5Vly",
    channels: ["in_app", "web_push", "zalo"],
    createdAt: new Date(Date.now() - 600000).toISOString() // 10 mins ago
  },
  {
    id: "alert_002",
    cameraId: "camera_living_room_01",
    cameraName: "Phòng khách",
    roiId: "roi_livingroom_01",
    roiName: "Khu vực ổ điện học tập",
    title: "Trẻ tiếp cận ổ điện phòng khách",
    severity: "warning",
    status: "checking",
    confidence: 0.89,
    snapshotUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuDWCSjBo6TnUsRWlJ2tjs-e3OaL7W2tW2n11xdmVvynBce6uvUvI3pe3tSUVlrrekzMsM-wvH0FK7JWVTD2DexHLv6rY8e2hgKEZP_Ggq7jdeH5_uVElfQkeDlGHwJJdxY3bOKvxNdJBqO8yBpMW3Zeu_mEXvjtFEZvqWg6hNE5k3Y63Jm_G34e1ZN464jc41DV_PyLaUsd6l-neyJ2WLi3cizEpihamSkrRnxSe2D7MtYWLqydFR00Xe5xnpdjFmY5erdJI3RY-2i_",
    channels: ["in_app", "zalo"],
    createdAt: new Date(Date.now() - 3600000 * 2).toISOString(), // 2 hours ago
    checkedBy: "Nguyễn Văn A"
  },
  {
    id: "alert_003",
    cameraId: "camera_kitchen_01",
    cameraName: "Nhà bếp",
    roiId: "roi_kitchen_01",
    roiName: "Khu vực Bếp ga & phích nước",
    title: "Phát hiện trẻ trong khu vực Bếp ga khi đang đun nấu",
    severity: "danger",
    status: "resolved",
    confidence: 0.94,
    snapshotUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuDJQJhk3Mo_3bA3uZVArlLWlawRzPJVtQSzOeyQot5g6XPiutk3m7nx_35dWI4r5WkTAY5ScnGF0pnCHMmD1tgNfN_iXyU_5qoxkcYzQkDlQAH7vxXhn_L21Q8YwWYAHX2EObBEjZ3HFKsCVtuEuYlFIE80Dc5CfafqkVTBMEGUtkbtzsFjHaYhG585gOuWSzzbjjzfi7NdSWX7Oytc1AqAOiCq7h3rpLkkYJNSn0hlu_AIAFW6OIY8GyzJMwUbg7t-2QtDyHcDCeUh",
    channels: ["in_app", "email"],
    createdAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    checkedBy: "Trần Thị B",
    resolvedBy: "Trần Thị B",
    resolvedAt: new Date(Date.now() - 86400000 + 300000).toISOString(), // 5 mins after trigger
    notes: "Đã vào bế bé ra phòng khách chơi."
  },
  {
    id: "alert_004",
    cameraId: "camera_kitchen_01",
    cameraName: "Nhà bếp",
    roiId: "roi_kitchen_01",
    roiName: "Khu vực Bếp ga & phích nước",
    title: "Cảnh báo chuyển động tại khu vực bếp được đánh dấu là báo nhầm",
    severity: "warning",
    status: "false_alarm",
    confidence: 0.72,
    snapshotUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuDWCSjBo6TnUsRWlJ2tjs-e3OaL7W2tW2n11xdmVvynBce6uvUvI3pe3tSUVlrrekzMsM-wvH0FK7JWVTD2DexHLv6rY8e2hgKEZP_Ggq7jdeH5_uVElfQkeDlGHwJJdxY3bOKvxNdJBqO8yBpMW3Zeu_mEXvjtFEZvqWg6hNE5k3Y63Jm_G34e1ZN464jc41DV_PyLaUsd6l-neyJ2WLi3cizEpihamSkrRnxSe2D7MtYWLqydFR00Xe5xnpdjFmY5erdJI3RY-2i_",
    channels: ["in_app"],
    createdAt: new Date(Date.now() - 3600000 * 5).toISOString(), // 5 hours ago
    checkedBy: "Nguyễn Văn A",
    falseAlarmReason: "Bố bé đi lấy nước ấm pha sữa"
  }
];

export const useAlertStore = create<AlertState>((set) => ({
  alerts: mockAlerts,
  selectedAlertId: null,
  filterStatus: "all",
  filterSeverity: "all",

  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts] })),
  selectAlert: (selectedAlertId) => set({ selectedAlertId }),
  updateAlertStatus: (alertId, status, extra = {}) =>
    set((state) => ({
      alerts: state.alerts.map((al) =>
        al.id === alertId ? { ...al, status, ...extra } : al
      ),
    })),
  setFilterStatus: (filterStatus) => set({ filterStatus }),
  setFilterSeverity: (filterSeverity) => set({ filterSeverity }),
}));
