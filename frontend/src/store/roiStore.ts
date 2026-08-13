import { create } from "zustand";
import type { ROIPoint, ROIZone } from "../types";
import { useCameraStore } from "./cameraStore";
import { isValidPolygon } from "../utils/roiGeometry";

export type DrawingMode = "polygon" | "rectangle" | "edit" | "idle";
export type DrawingState = "roi_empty" | "roi_drawing" | "roi_unsaved" | "roi_saved" | "roi_editing" | "roi_invalid";

interface RoiState {
  zones: ROIZone[];
  selectedZoneId: string | null;
  draftZone: Partial<ROIZone> | null;
  draftPoints: ROIPoint[];
  drawingMode: DrawingMode;
  drawingState: DrawingState;
  selectedPointIndex: number | null;
  undoStack: ROIPoint[][];
  redoStack: ROIPoint[][];
  validationError: string | null;

  // Actions
  initializeZones: () => void;
  selectZone: (zoneId: string | null) => void;
  startDrawingPolygon: (cameraId: string) => void;
  startDrawingRectangle: (cameraId: string) => void;
  startEditingZone: (zone: ROIZone) => void;
  addDraftPoint: (point: ROIPoint) => void;
  updateDraftPoint: (index: number, point: ROIPoint) => void;
  deleteSelectedPoint: () => void;
  undo: () => void;
  redo: () => void;
  resetDraft: () => void;
  completeZone: () => void;
  saveDraftZone: () => boolean;
  deleteZone: (zoneId: string) => void;
  setZoneName: (name: string) => void;
  setSensitivity: (sensitivity: ROIZone["sensitivity"]) => void;
  toggleRule: (ruleKey: keyof ROIZone["rules"]) => void;
  setEnabled: (zoneId: string, enabled: boolean) => void;
  validateDraftZone: () => boolean;
  cancelDrawing: () => void;
}

// Helper to pull initial zones from cameraStore
const getInitialZones = (): ROIZone[] => {
  const cameras = useCameraStore.getState().cameras;
  return cameras.flatMap((c) => c.roiZones || []);
};

export const useRoiStore = create<RoiState>((set, get) => ({
  zones: getInitialZones(),
  selectedZoneId: null,
  draftZone: null,
  draftPoints: [],
  drawingMode: "idle",
  drawingState: "roi_empty",
  selectedPointIndex: null,
  undoStack: [],
  redoStack: [],
  validationError: null,

  initializeZones: () => {
    set({ zones: getInitialZones() });
  },

  selectZone: (selectedZoneId) => {
    set({ selectedZoneId });
  },

  startDrawingPolygon: (cameraId) => {
    set({
      drawingMode: "polygon",
      drawingState: "roi_drawing",
      draftPoints: [],
      undoStack: [],
      redoStack: [],
      validationError: null,
      selectedPointIndex: null,
      draftZone: {
        id: `roi_${Date.now()}`,
        cameraId,
        name: "",
        type: "polygon",
        sensitivity: "medium",
        rules: {
          enterZone: true,
          stayTooLong: false,
          stayDurationSeconds: 5,
          approachZone: false
        },
        enabled: true,
        createdBy: "Nguyễn Văn A"
      }
    });
  },

  startDrawingRectangle: (cameraId) => {
    set({
      drawingMode: "rectangle",
      drawingState: "roi_drawing",
      draftPoints: [],
      undoStack: [],
      redoStack: [],
      validationError: null,
      selectedPointIndex: null,
      draftZone: {
        id: `roi_${Date.now()}`,
        cameraId,
        name: "",
        type: "rectangle",
        sensitivity: "medium",
        rules: {
          enterZone: true,
          stayTooLong: false,
          stayDurationSeconds: 5,
          approachZone: false
        },
        enabled: true,
        createdBy: "Nguyễn Văn A"
      }
    });
  },

  startEditingZone: (zone) => {
    set({
      drawingMode: "edit",
      drawingState: "roi_editing",
      draftZone: { ...zone },
      draftPoints: [...zone.points],
      undoStack: [],
      redoStack: [],
      selectedZoneId: zone.id,
      selectedPointIndex: null,
      validationError: null
    });
  },

  addDraftPoint: (point) => {
    const { draftPoints, drawingMode, undoStack } = get();
    
    // For rectangles, we only allow 2 clicks to define diagonal corners
    if (drawingMode === "rectangle" && draftPoints.length >= 2) {
      return;
    }

    const nextPoints = [...draftPoints, point];
    set({
      draftPoints: nextPoints,
      undoStack: [...undoStack, draftPoints],
      redoStack: [], // Clear redo history on new actions
      drawingState: drawingMode === "rectangle" && nextPoints.length === 2 ? "roi_unsaved" : "roi_drawing"
    });
  },

  updateDraftPoint: (index, newPoint) => {
    const { draftPoints, undoStack } = get();
    const nextPoints = draftPoints.map((p, i) => (i === index ? newPoint : p));
    
    set({
      draftPoints: nextPoints,
      undoStack: [...undoStack, draftPoints],
      redoStack: [],
      drawingState: "roi_unsaved"
    });
  },

  deleteSelectedPoint: () => {
    const { draftPoints, selectedPointIndex, undoStack, draftZone } = get();
    if (selectedPointIndex === null) return;

    const nextPoints = draftPoints.filter((_, i) => i !== selectedPointIndex);
    
    // Polygon needs at least 3 points, if it has less after completion it is invalid
    const isPolygon = draftZone?.type === "polygon";
    const isInvalid = isPolygon && nextPoints.length < 3;

    set({
      draftPoints: nextPoints,
      selectedPointIndex: null,
      undoStack: [...undoStack, draftPoints],
      redoStack: [],
      drawingState: isInvalid ? "roi_invalid" : "roi_unsaved",
      validationError: isInvalid ? "Vùng đa giác cần ít nhất 3 điểm." : null
    });
  },

  undo: () => {
    const { undoStack, draftPoints, redoStack } = get();
    if (undoStack.length === 0) return;

    const prevPoints = undoStack[undoStack.length - 1];
    set({
      draftPoints: prevPoints,
      undoStack: undoStack.slice(0, -1),
      redoStack: [...redoStack, draftPoints],
      drawingState: "roi_unsaved"
    });
  },

  redo: () => {
    const { redoStack, draftPoints, undoStack } = get();
    if (redoStack.length === 0) return;

    const nextPoints = redoStack[redoStack.length - 1];
    set({
      draftPoints: nextPoints,
      undoStack: [...undoStack, draftPoints],
      redoStack: redoStack.slice(0, -1),
      drawingState: "roi_unsaved"
    });
  },

  resetDraft: () => {
    set({
      draftPoints: [],
      undoStack: [],
      redoStack: [],
      drawingState: "roi_drawing",
      validationError: null,
      selectedPointIndex: null
    });
  },

  completeZone: () => {
    const { draftPoints, draftZone } = get();
    if (draftZone?.type === "polygon") {
      if (isValidPolygon(draftPoints)) {
        set({ drawingState: "roi_unsaved", validationError: null });
      } else {
        set({ drawingState: "roi_invalid", validationError: "Vùng đa giác cần ít nhất 3 điểm." });
      }
    }
  },

  setZoneName: (name) => {
    const { draftZone } = get();
    if (!draftZone) return;
    set({
      draftZone: { ...draftZone, name },
      drawingState: "roi_unsaved"
    });
  },

  setSensitivity: (sensitivity) => {
    const { draftZone } = get();
    if (!draftZone) return;
    set({
      draftZone: { ...draftZone, sensitivity },
      drawingState: "roi_unsaved"
    });
  },

  toggleRule: (ruleKey) => {
    const { draftZone } = get();
    if (!draftZone || !draftZone.rules) return;
    
    const rules = {
      ...draftZone.rules,
      [ruleKey]: !draftZone.rules[ruleKey]
    };
    
    set({
      draftZone: { ...draftZone, rules },
      drawingState: "roi_unsaved"
    });
  },

  setEnabled: (zoneId, enabled) => {
    const nextZones = get().zones.map((z) =>
      z.id === zoneId ? { ...z, enabled } : z
    );
    set({ zones: nextZones });
    
    // Sync to cameraStore
    const zone = get().zones.find((z) => z.id === zoneId);
    if (zone) {
      const cameraId = zone.cameraId;
      const cameraZones = nextZones.filter((z) => z.cameraId === cameraId);
      useCameraStore.getState().updateCameraZones(cameraId, cameraZones);
    }
  },

  validateDraftZone: () => {
    const { draftZone, draftPoints } = get();
    if (!draftZone) return false;

    if (!draftZone.name || draftZone.name.trim() === "") {
      set({ validationError: "Vui lòng đặt tên vùng nguy hiểm trước khi lưu." });
      return false;
    }

    if (draftZone.type === "polygon" && draftPoints.length < 3) {
      set({ validationError: "Vùng đa giác cần ít nhất 3 điểm." });
      return false;
    }

    if (draftZone.type === "rectangle" && draftPoints.length < 4) {
      set({ validationError: "Vùng hình chữ nhật chưa hoàn thành vẽ (cần 4 góc)." });
      return false;
    }

    set({ validationError: null });
    return true;
  },

  saveDraftZone: () => {
    const { draftZone, draftPoints, validateDraftZone, zones } = get();
    if (!validateDraftZone() || !draftZone) return false;

    const completedZone: ROIZone = {
      ...(draftZone as ROIZone),
      points: draftPoints,
      updatedAt: new Date().toISOString(),
      createdAt: draftZone.createdAt || new Date().toISOString()
    };

    // Replace if exists, or append if new
    const isNew = !zones.some((z) => z.id === completedZone.id);
    const nextZones = isNew
      ? [...zones, completedZone]
      : zones.map((z) => (z.id === completedZone.id ? completedZone : z));

    set({
      zones: nextZones,
      drawingMode: "idle",
      drawingState: "roi_saved",
      draftZone: null,
      draftPoints: [],
      selectedZoneId: completedZone.id
    });

    // Synchronize to CameraStore
    const cameraId = completedZone.cameraId;
    const cameraZones = nextZones.filter((z) => z.cameraId === cameraId);
    useCameraStore.getState().updateCameraZones(cameraId, cameraZones);

    return true;
  },

  deleteZone: (zoneId) => {
    const { zones } = get();
    const zoneToDelete = zones.find((z) => z.id === zoneId);
    if (!zoneToDelete) return;

    const nextZones = zones.filter((z) => z.id !== zoneId);
    set({
      zones: nextZones,
      selectedZoneId: null
    });

    // Synchronize to CameraStore
    const cameraId = zoneToDelete.cameraId;
    const cameraZones = nextZones.filter((z) => z.cameraId === cameraId);
    useCameraStore.getState().updateCameraZones(cameraId, cameraZones);
  },

  cancelDrawing: () => {
    set({
      drawingMode: "idle",
      drawingState: "roi_empty",
      draftZone: null,
      draftPoints: [],
      undoStack: [],
      redoStack: [],
      validationError: null,
      selectedPointIndex: null
    });
  }
}));
export default useRoiStore;
