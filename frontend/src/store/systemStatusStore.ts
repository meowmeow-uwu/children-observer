import { create } from "zustand";
import type { Device } from "../types";
import { fetchDevicesApi } from "../services/api";

interface SystemState {
  deviceInfo: Device | null;
  complianceChecks: {
    standard: string;
    passed: boolean;
    checks: Array<{ id: string; name: string; passed: boolean }>;
    warnings: string[];
  }[];
  isOnline: boolean;

  // Actions
  setDeviceInfo: (info: Device) => void;
  updatePerformance: (cpu: number, memory: number, diskFree: number) => void;
  setComplianceChecks: (checks: SystemState["complianceChecks"]) => void;
  setOnlineStatus: (isOnline: boolean) => void;
  loadDevices: () => Promise<void>;
}

export const useSystemStatusStore = create<SystemState>((set) => ({
  // Không seed mock device — load từ backend
  deviceInfo: null,
  complianceChecks: [],
  isOnline: true,

  setDeviceInfo: (deviceInfo) => set({ deviceInfo }),
  updatePerformance: (cpuUsage, memoryUsage, diskFreeGb) =>
    set((state) => ({
      deviceInfo: state.deviceInfo
        ? { ...state.deviceInfo, cpuUsage, memoryUsage, diskFreeGb }
        : null,
    })),
  setComplianceChecks: (complianceChecks) => set({ complianceChecks }),
  setOnlineStatus: (isOnline) => set({ isOnline }),

  /** Tải danh sách thiết bị từ GET /api/devices/ — lấy device đầu tiên làm Edge Hub */
  loadDevices: async () => {
    try {
      const devices = await fetchDevicesApi();
      if (devices && devices.length > 0) {
        set({ deviceInfo: devices[0] });
      }
    } catch {
      // Không crash nếu backend chưa có endpoint devices
    }
  },
}));
