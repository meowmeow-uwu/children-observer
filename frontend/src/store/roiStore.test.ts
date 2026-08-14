import { beforeEach, describe, expect, it } from "vitest";
import type { ROIZone } from "../types";
import { useRoiStore } from "./roiStore";

const savedRectangle: ROIZone = {
  id: "1",
  cameraId: "camera_living_room_01",
  name: "Vùng thử nghiệm",
  type: "rectangle",
  points: [
    { x: 0.35, y: 0.5 },
    { x: 0.55, y: 0.5 },
    { x: 0.55, y: 0.8 },
    { x: 0.35, y: 0.8 },
  ],
  sensitivity: "high",
  rules: {
    enterZone: true,
    stayTooLong: false,
    stayDurationSeconds: 5,
    approachZone: false,
  },
  enabled: true,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
  createdBy: "tester",
};

describe("roiStore editing identity", () => {
  beforeEach(() => {
    useRoiStore.getState().cancelDrawing();
    useRoiStore.setState({ zones: [savedRectangle] });
  });

  it("keeps the edited zone hidden when changing shape and clearing strokes", () => {
    const store = useRoiStore.getState();
    store.startEditingZone(savedRectangle);
    useRoiStore.getState().startDrawingPolygon(savedRectangle.cameraId);

    expect(useRoiStore.getState().selectedZoneId).toBe(savedRectangle.id);
    expect(useRoiStore.getState().draftZone?.id).toBe(savedRectangle.id);
    expect(useRoiStore.getState().draftZone?.type).toBe("polygon");

    useRoiStore.getState().resetDraft();
    expect(useRoiStore.getState().draftPoints).toEqual([]);
    expect(useRoiStore.getState().selectedZoneId).toBe(savedRectangle.id);
    expect(useRoiStore.getState().draftZone?.id).toBe(savedRectangle.id);
  });

  it("does not lose edited-zone identity when camera hydration finishes late", () => {
    useRoiStore.getState().startEditingZone(savedRectangle);
    useRoiStore.getState().resetDraft();

    useRoiStore.getState().hydrateFromCameras();
    expect(useRoiStore.getState().selectedZoneId).toBe(savedRectangle.id);
    expect(useRoiStore.getState().draftZone?.id).toBe(savedRectangle.id);

    useRoiStore.getState().startDrawingPolygon(savedRectangle.cameraId);
    expect(useRoiStore.getState().selectedZoneId).toBe(savedRectangle.id);
    expect(useRoiStore.getState().draftZone?.type).toBe("polygon");
    expect(useRoiStore.getState().draftPoints).toEqual([]);
  });
});
