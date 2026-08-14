import type { Camera, ROIZone } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8007/api";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore parse failure
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

// ---- Cameras ----

interface CameraApiDto {
  id: number;
  camera_id_string: string;
  name: string;
  location: string;
  status: string;
  is_active: boolean;
  alerts_paused?: boolean;
  roi_zones: Array<{
    id: number;
    camera_id: string;
    name: string;
    type?: string;
    points: Array<{ x: number; y: number }>;
    sensitivity: string;
    enabled: boolean;
    rules?: ROIZone["rules"];
  }>;
}

const DEFAULT_RULES: ROIZone["rules"] = {
  enterZone: true,
  stayTooLong: false,
  stayDurationSeconds: 5,
  approachZone: false,
};

export const mapCameraFromApi = (cam: CameraApiDto): Camera => ({
  id: cam.camera_id_string,
  name: cam.name,
  location: cam.location,
  status: (cam.status === "online" ? "online" : "offline") as Camera["status"],
  streamStatus: "idle",
  resolution: "1920x1080",
  fps: 25,
  signalQuality: "good",
  alertsPaused: Boolean(cam.alerts_paused),
  lastSeenAt: new Date().toISOString(),
  roiZones: (cam.roi_zones || []).map((z) => ({
    id: String(z.id),
    cameraId: z.camera_id,
    name: z.name,
    type: (z.type === "rectangle" ? "rectangle" : "polygon") as ROIZone["type"],
    points: z.points,
    sensitivity: (["low", "medium", "high"].includes(z.sensitivity) ? z.sensitivity : "medium") as ROIZone["sensitivity"],
    rules: { ...DEFAULT_RULES, ...(z.rules || {}) },
    enabled: Boolean(z.enabled),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: "",
  })),
});

export const fetchCamerasApi = async (): Promise<Camera[] | null> => {
  try {
    const data = await request<CameraApiDto[]>("/cameras");
    return data.map(mapCameraFromApi);
  } catch (err) {
    console.warn("Không tải được dữ liệu camera từ backend:", err);
    return null;
  }
};

export const fetchCameraRoiApi = async (cameraId: string): Promise<ROIZone[] | null> => {
  try {
    const data = await request<CameraApiDto["roi_zones"]>(`/cameras/${cameraId}/roi`);
    return data.map((z) => mapCameraFromApi({
      id: 0,
      camera_id_string: cameraId,
      name: "",
      location: "",
      status: "online",
      is_active: true,
      roi_zones: [z],
    }).roiZones[0]);
  } catch (err) {
    console.warn(`Không tải được ROI của ${cameraId}:`, err);
    return null;
  }
};

export const setCameraAlertsPausedApi = async (cameraId: string, paused: boolean): Promise<Camera> => {
  const data = await request<CameraApiDto>(`/cameras/${cameraId}/alerts-paused`, {
    method: "POST",
    body: JSON.stringify({ paused }),
  });
  return mapCameraFromApi(data);
};

// ---- ROI ----

export const toZonePayload = (zone: ROIZone) => ({
  name: zone.name,
  type: zone.type,
  points: zone.points,
  sensitivity: zone.sensitivity,
  enabled: zone.enabled,
  rules: zone.rules,
});

/**
 * Lưu TOÀN BỘ danh sách zone của camera (replace-whole-list có chủ đích).
 * Ném ApiError khi thất bại — caller phải xử lý loading/error thực.
 */
export const saveCameraRoiApi = async (cameraId: string, zones: ROIZone[]): Promise<ROIZone[]> => {
  const data = await request<CameraApiDto["roi_zones"]>(`/cameras/${cameraId}/roi`, {
    method: "POST",
    body: JSON.stringify(zones.map(toZonePayload)),
  });
  return data.map((z) => mapCameraFromApi({
    id: 0,
    camera_id_string: cameraId,
    name: "",
    location: "",
    status: "online",
    is_active: true,
    roi_zones: [z],
  }).roiZones[0]);
};

// ---- Alerts ----

export interface AlertApiItem {
  id: number;
  camera_id: string;
  camera_name: string;
  title: string;
  severity: string;
  status: string;
  snapshot_url: string;
  roi_name: string;
  notes: string;
  created_at?: string;
}

export const fetchAlertsApi = async (cameraId?: string): Promise<AlertApiItem[] | null> => {
  try {
    const qs = cameraId ? `?camera_id=${encodeURIComponent(cameraId)}` : "";
    return await request<AlertApiItem[]>(`/alerts${qs}`);
  } catch (err) {
    console.warn("Không tải được alerts:", err);
    return null;
  }
};

export const clearAlertsApi = async (): Promise<boolean> => {
  try {
    await request<{ deleted: number }>("/alerts", { method: "DELETE" });
    return true;
  } catch (err) {
    console.warn("Không thể xóa cảnh báo cũ khi tải lại trang:", err);
    return false;
  }
};

export const updateAlertStatusApi = async (alertId: string | number, status: string, notes?: string): Promise<boolean> => {
  try {
    await request(`/alerts/${alertId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, notes }),
    });
    return true;
  } catch (err) {
    console.error("Lỗi khi cập nhật cảnh báo:", err);
    return false;
  }
};
