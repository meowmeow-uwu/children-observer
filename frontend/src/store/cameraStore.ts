import { create } from "zustand";
import type { Camera, ROIZone } from "../types";
import { fetchCamerasApi } from "../services/api";

interface CameraState {
  cameras: Camera[];
  selectedCameraId: string | null;
  isLoading: boolean;
  error: string | null;
  setCameras: (cameras: Camera[]) => void;
  selectCamera: (cameraId: string | null) => void;
  updateCameraStatus: (cameraId: string, status: Camera["status"]) => void;
  updateCameraStreamStatus: (cameraId: string, streamStatus: Camera["streamStatus"]) => void;
  updateCameraZones: (cameraId: string, zones: ROIZone[]) => void;
  updateCameraAlertsPaused: (cameraId: string, paused: boolean) => void;
  loadCameras: () => Promise<void>;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useCameraStore = create<CameraState>((set) => ({
  // Camera/ROI luôn hydrate từ backend; không fallback sang geometry mock cũ.
  cameras: [],
  selectedCameraId: "camera_living_room_01",
  isLoading: false,
  error: null,

  setCameras: (cameras) => set({ cameras }),
  selectCamera: (selectedCameraId) => set({ selectedCameraId }),
  updateCameraStatus: (cameraId, status) =>
    set((state) => ({
      cameras: state.cameras.map((camera) =>
        camera.id === cameraId
          ? { ...camera, status, lastSeenAt: new Date().toISOString() }
          : camera
      ),
    })),
  updateCameraStreamStatus: (cameraId, streamStatus) =>
    set((state) => ({
      cameras: state.cameras.map((camera) =>
        camera.id === cameraId ? { ...camera, streamStatus } : camera
      ),
    })),
  updateCameraZones: (cameraId, zones) =>
    set((state) => ({
      cameras: state.cameras.map((camera) =>
        camera.id === cameraId ? { ...camera, roiZones: zones } : camera
      ),
    })),
  updateCameraAlertsPaused: (cameraId, paused) =>
    set((state) => ({
      cameras: state.cameras.map((camera) =>
        camera.id === cameraId ? { ...camera, alertsPaused: paused } : camera
      ),
    })),
  loadCameras: async () => {
    set({ isLoading: true, error: null });
    const fetched = await fetchCamerasApi();
    if (fetched !== null) {
      set((state) => ({
        cameras: fetched.map((apiCamera) => {
          const local = state.cameras.find((camera) => camera.id === apiCamera.id);
          return local
            ? {
                ...apiCamera,
                streamStatus: local.streamStatus,
                lastSeenAt: local.lastSeenAt,
              }
            : apiCamera;
        }),
        isLoading: false,
      }));
      return;
    }
    set({ isLoading: false, error: "Không tải được dữ liệu camera từ backend." });
  },
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
