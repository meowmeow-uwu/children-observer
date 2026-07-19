export type Role = "parent" | "guardian" | "viewer";
export type AlertStatus = "unread" | "checking" | "resolved" | "false_alarm";
export type NotificationChannel = "in_app" | "web_push" | "zalo" | "email" | "sms";
export type WebRTCConnectionState = "new" | "connecting" | "connected" | "disconnected" | "failed" | "closed";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatarUrl?: string;
}

export interface ROIPoint {
  x: number; // Normalized coordinate [0.0 - 1.0]
  y: number; // Normalized coordinate [0.0 - 1.0]
}

export interface ROIZone {
  id: string;
  cameraId: string;
  name: string;
  type: "polygon" | "rectangle";
  points: ROIPoint[];
  sensitivity: "low" | "medium" | "high";
  rules: {
    enterZone: boolean;
    stayTooLong: boolean;
    stayDurationSeconds: number;
    approachZone: boolean;
  };
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export interface Camera {
  id: string;
  name: string;
  location: string;
  status: "online" | "offline" | "loading";
  streamStatus: "idle" | "connecting" | "connected" | "reconnecting" | "failed" | "closed";
  resolution: string;
  fps: number;
  roiZones: ROIZone[];
  signalQuality: "good" | "fair" | "poor";
  lastAlertTime?: string;
  lastSeenAt: string;
}

export interface Device {
  id: string;
  name: string;
  type: "camera" | "gateway" | "hub";
  status: "online" | "offline";
  ipAddress: string;
  macAddress: string;
  firmwareVersion: string;
  cpuUsage: number;
  memoryUsage: number;
  diskFreeGb: number;
}

export interface Alert {
  id: string;
  cameraId: string;
  cameraName: string;
  roiId?: string;
  roiName?: string;
  title: string;
  severity: "info" | "warning" | "danger";
  status: AlertStatus;
  confidence: number;
  snapshotUrl: string; // Dynamic, authenticated URL
  channels: NotificationChannel[];
  createdAt: string;
  notes?: string;
  checkedBy?: string;
  resolvedBy?: string;
  resolvedAt?: string;
  falseAlarmReason?: string;
}

export interface ChildProfile {
  id: string;
  name: string;
  age: number;
  gender: "nam" | "nữ";
  avatarUrl?: string;
  notes?: string;
}
