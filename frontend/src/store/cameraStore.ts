import { create } from "zustand";
import type { Camera, ROIZone } from "../types";

interface CameraState {
  cameras: Camera[];
  selectedCameraId: string | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setCameras: (cameras: Camera[]) => void;
  selectCamera: (cameraId: string | null) => void;
  updateCameraStatus: (cameraId: string, status: Camera["status"]) => void;
  updateCameraStreamStatus: (cameraId: string, streamStatus: Camera["streamStatus"]) => void;
  updateCameraZones: (cameraId: string, zones: ROIZone[]) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

// Rich mock data representing typical home cameras
const mockCameras: Camera[] = [
  {
    id: "camera_living_room_01",
    name: "Phòng khách",
    location: "Khu vực bàn học & đồ chơi",
    status: "online",
    streamStatus: "idle",
    resolution: "1920x1080",
    fps: 25,
    signalQuality: "good",
    lastSeenAt: new Date().toISOString(),
    lastAlertTime: new Date(Date.now() - 3600000 * 7).toISOString(), // 7 hours ago
    roiZones: [
      {
        id: "roi_livingroom_01",
        cameraId: "camera_living_room_01",
        name: "Khu vực ổ điện học tập",
        type: "rectangle",
        points: [
          { x: 0.15, y: 0.40 },
          { x: 0.45, y: 0.40 },
          { x: 0.45, y: 0.80 },
          { x: 0.15, y: 0.80 }
        ],
        sensitivity: "medium",
        rules: {
          enterZone: true,
          stayTooLong: false,
          stayDurationSeconds: 5,
          approachZone: true
        },
        enabled: true,
        createdAt: new Date(Date.now() - 86400000 * 10).toISOString(),
        updatedAt: new Date(Date.now() - 86400000 * 10).toISOString(),
        createdBy: "Nguyễn Văn A"
      }
    ]
  },
  {
    id: "camera_balcony_01",
    name: "Ban công",
    location: "Cửa kính hướng ra ban công căn hộ",
    status: "online",
    streamStatus: "connected",
    resolution: "1920x1080",
    fps: 25,
    signalQuality: "fair",
    lastSeenAt: new Date().toISOString(),
    lastAlertTime: new Date(Date.now() - 600000).toISOString(), // 10 mins ago
    roiZones: [
      {
        id: "roi_balcony_01",
        cameraId: "camera_balcony_01",
        name: "Ranh giới Lan can",
        type: "polygon",
        points: [
          { x: 0.20, y: 0.45 },
          { x: 0.80, y: 0.45 },
          { x: 0.85, y: 0.90 },
          { x: 0.15, y: 0.90 }
        ],
        sensitivity: "high",
        rules: {
          enterZone: true,
          stayTooLong: true,
          stayDurationSeconds: 3,
          approachZone: true
        },
        enabled: true,
        createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
        updatedAt: new Date(Date.now() - 86400000 * 2).toISOString(),
        createdBy: "Nguyễn Văn A"
      }
    ]
  },
  {
    id: "camera_kitchen_01",
    name: "Nhà bếp",
    location: "Khu vực bếp nấu & tủ lạnh",
    status: "online",
    streamStatus: "connecting",
    resolution: "1280x720",
    fps: 20,
    signalQuality: "good",
    lastSeenAt: new Date().toISOString(),
    lastAlertTime: new Date(Date.now() - 3600000 * 24).toISOString(), // 24 hours ago
    roiZones: [
      {
        id: "roi_kitchen_01",
        cameraId: "camera_kitchen_01",
        name: "Khu vực Bếp ga & phích nước",
        type: "rectangle",
        points: [
          { x: 0.50, y: 0.30 },
          { x: 0.90, y: 0.30 },
          { x: 0.90, y: 0.75 },
          { x: 0.50, y: 0.75 }
        ],
        sensitivity: "medium",
        rules: {
          enterZone: true,
          stayTooLong: false,
          stayDurationSeconds: 5,
          approachZone: true
        },
        enabled: true,
        createdAt: new Date(Date.now() - 86400000 * 12).toISOString(),
        updatedAt: new Date(Date.now() - 86400000 * 12).toISOString(),
        createdBy: "Trần Thị B"
      }
    ]
  },
  {
    id: "camera_stairs_01",
    name: "Cầu thang",
    location: "Lối lên xuống tầng 1 & 2",
    status: "offline",
    streamStatus: "failed",
    resolution: "1920x1080",
    fps: 25,
    signalQuality: "poor",
    lastSeenAt: new Date(Date.now() - 3600000 * 3).toISOString(), // 3 hours ago
    roiZones: []
  }
];

export const useCameraStore = create<CameraState>((set) => ({
  cameras: mockCameras,
  selectedCameraId: "camera_living_room_01",
  isLoading: false,
  error: null,

  setCameras: (cameras) => set({ cameras }),
  selectCamera: (selectedCameraId) => set({ selectedCameraId }),
  updateCameraStatus: (cameraId, status) =>
    set((state) => ({
      cameras: state.cameras.map((cam) =>
        cam.id === cameraId ? { ...cam, status, lastSeenAt: new Date().toISOString() } : cam
      ),
    })),
  updateCameraStreamStatus: (cameraId, streamStatus) =>
    set((state) => ({
      cameras: state.cameras.map((cam) =>
        cam.id === cameraId ? { ...cam, streamStatus } : cam
      ),
    })),
  updateCameraZones: (cameraId, zones) =>
    set((state) => ({
      cameras: state.cameras.map((cam) =>
        cam.id === cameraId ? { ...cam, roiZones: zones } : cam
      ),
    })),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
