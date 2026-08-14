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

export interface ROIRules {
  enterZone: boolean;
  stayTooLong: boolean;
  stayDurationSeconds: number;
  approachZone: boolean;
}

export interface ROIZone {
  id: string;
  cameraId: string;
  name: string;
  type: "polygon" | "rectangle";
  points: ROIPoint[];
  sensitivity: "low" | "medium" | "high";
  rules: ROIRules;
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
  alertsPaused?: boolean;
  lastAlertTime?: string;
  lastSeenAt: string;
}

// ---- AI detection feed (từ Edge qua WebRTC DataChannel) ----

export const AI_FEED_SCHEMA_VERSION = 1;

export interface TrackBox {
  trackId: number;
  classId: number;
  className: string;
  confidence: number;
  box: [number, number, number, number]; // [x1, y1, x2, y2] normalized 0-1
  confirmed: boolean;   // track đã ổn định — mới được dùng cho rule/alert
  zoneBreach?: boolean; // track thực sự đang vi phạm ROI (box đỏ)
  zoneId?: string | null;
  zoneName?: string | null;
}

export type AiStreamState =
  | "initializing"  // AI đang load model
  | "tracking"      // có đối tượng được track
  | "no_objects"    // video chạy, không có đối tượng
  | "error"         // lỗi inference
  | "offline";      // mất kết nối/heartbeat timeout

export interface AiFeedBase {
  schemaVersion: number;
  type: string;
  cameraId: string;
  streamId: string;
  sentAtMs: number;
}

export interface StreamSyncMessage extends AiFeedBase {
  type: "stream_sync";
  streamOriginMs: number; // source_time_ms của frame video đầu tiên trên PC này
  videoFps: number;
}

export interface TrackFrameMessage extends AiFeedBase {
  type: "tracks";
  frameId: number;
  sourcePtsMs: number;    // clock video trong loop (reset mỗi loop)
  sourceTimeMs: number;   // clock monotonic Edge (tăng liên tục)
  loopId: number;         // vòng lặp video (tracker reset mỗi loop)
  latencyMs: number;
  tracks: TrackBox[];
}

export interface AiStatusMessage extends AiFeedBase {
  type: "status";
  state: Exclude<AiStreamState, "offline">;
  latencyMs: number;
  trackCount: number;
  sourcePtsMs: number;
  loopId: number;
  alerts?: number;
}

export type AiFeedMessage = StreamSyncMessage | TrackFrameMessage | AiStatusMessage;

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
