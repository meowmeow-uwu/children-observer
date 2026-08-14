import { create } from "zustand";
import type { Alert, AlertStatus } from "../types";
import { updateAlertStatusApi } from "../services/api";

interface AlertState {
  alerts: Alert[];
  selectedAlertId: string | null;
  filterStatus: AlertStatus | "all";
  filterSeverity: Alert["severity"] | "all";
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  selectAlert: (alertId: string | null) => void;
  updateAlertStatus: (alertId: string, status: AlertStatus, extra?: Partial<Alert>) => void;
  setFilterStatus: (status: AlertStatus | "all") => void;
  setFilterSeverity: (severity: Alert["severity"] | "all") => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  // Không seed mock: lịch sử và cảnh báo đều phải đến từ backend thật.
  alerts: [],
  selectedAlertId: null,
  filterStatus: "all",
  filterSeverity: "all",

  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts] })),
  selectAlert: (selectedAlertId) => set({ selectedAlertId }),
  updateAlertStatus: (alertId, status, extra = {}) => {
    updateAlertStatusApi(alertId, status).catch(() => undefined);
    set((state) => ({
      alerts: state.alerts.map((alert) =>
        alert.id === alertId ? { ...alert, status, ...extra } : alert
      ),
    }));
  },
  setFilterStatus: (filterStatus) => set({ filterStatus }),
  setFilterSeverity: (filterSeverity) => set({ filterSeverity }),
}));
