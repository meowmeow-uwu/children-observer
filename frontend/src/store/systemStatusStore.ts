import { create } from "zustand";
import type { Device } from "../types";

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
}

const mockDevice: Device = {
  id: "edge_hub_01",
  name: "SafeKid Edge Hub Gateway",
  type: "gateway",
  status: "online",
  ipAddress: "192.168.1.15",
  macAddress: "00:1A:2B:3C:4D:5E",
  firmwareVersion: "v1.4.2-stable",
  cpuUsage: 34.5,
  memoryUsage: 512.4, // MB
  diskFreeGb: 14.8 // GB
};

const mockCompliance = [
  {
    standard: "QCVN 135:2024/BTTTT (Việt Nam)",
    passed: true,
    checks: [
      { id: "QCVN135-01", name: "Không sử dụng mật khẩu mặc định", passed: true },
      { id: "QCVN135-02", name: "Mã hóa E2EE cho dữ liệu nhạy cảm", passed: true },
      { id: "QCVN135-03", name: "Hỗ trợ cập nhật OTA an toàn", passed: true },
      { id: "QCVN135-04", name: "Bảo vệ thông tin cá nhân (làm mờ mặt)", passed: true }
    ],
    warnings: []
  },
  {
    standard: "PSTI (Vương quốc Anh)",
    passed: true,
    checks: [
      { id: "PSTI-01", name: "Không dùng mật khẩu mặc định duy nhất", passed: true },
      { id: "PSTI-02", name: "Chính sách công bố lỗ hổng bảo mật", passed: true },
      { id: "PSTI-03", name: "Thời hạn cập nhật bảo mật tối thiểu", passed: true }
    ],
    warnings: []
  }
];

export const useSystemStatusStore = create<SystemState>((set) => ({
  deviceInfo: mockDevice,
  complianceChecks: mockCompliance,
  isOnline: true,

  setDeviceInfo: (deviceInfo) => set({ deviceInfo }),
  updatePerformance: (cpuUsage, memoryUsage, diskFreeGb) =>
    set((state) => ({
      deviceInfo: state.deviceInfo
        ? { ...state.deviceInfo, cpuUsage, memoryUsage, diskFreeGb }
        : null
    })),
  setComplianceChecks: (complianceChecks) => set({ complianceChecks }),
  setOnlineStatus: (isOnline) => set({ isOnline })
}));
