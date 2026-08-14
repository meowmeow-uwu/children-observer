import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { useRoiStore } from "../store/roiStore";
import { ROISVGOverlay } from "../components/ROI/ROISVGOverlay";
import { ROIToolbar } from "../components/ROI/ROIToolbar";
import { ROISettingsPanel } from "../components/ROI/ROISettingsPanel";
import { UnsavedChangesBlocker } from "../components/ROI/UnsavedChangesBlocker";
import { ErrorState } from "../components/ErrorState";

export const ROIDrawingView: React.FC = () => {
  const { cameraId } = useParams<{ cameraId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const { cameras } = useCameraStore();
  const { startDrawingPolygon, cancelDrawing, drawingMode, drawingState } = useRoiStore();
  const initializedRouteRef = useRef<string | null>(null);
  const [initializationError, setInitializationError] = useState<string | null>(null);

  const cam = cameras.find((c) => c.id === cameraId);

  // Cảnh báo mất thay đổi khi rời trang với vùng chưa lưu (dialog thật)
  const hasUnsavedChanges =
    drawingState === "roi_unsaved" ||
    drawingState === "roi_drawing" ||
    drawingState === "roi_invalid";

  useEffect(() => {
    if (!cam) return;
    const routeKey = `${cam.id}|${location.search}`;
    if (initializedRouteRef.current === routeKey) return;

    const searchParams = new URLSearchParams(location.search);
    const mode = searchParams.get("mode");
    const editZoneId = searchParams.get("zoneId");

    // Đồng bộ canonical zones của camera trước khi tạo draft edit. Việc này
    // đóng race giữa cameraStore render và Layout hydrate roiStore.
    const currentZones = useRoiStore.getState().zones;
    useRoiStore.setState({
      zones: [
        ...currentZones.filter((zone) => zone.cameraId !== cam.id),
        ...cam.roiZones,
      ],
    });

    setInitializationError(null);
    if (mode === "new") {
      startDrawingPolygon(cam.id);
    } else if (editZoneId) {
      const existingZone = cam.roiZones.find((zone) => zone.id === editZoneId);
      if (!existingZone) {
        setInitializationError("Vùng ROI cần chỉnh sửa không còn tồn tại hoặc chưa tải được.");
        return;
      }
      useRoiStore.getState().startEditingZone(existingZone);
    } else {
      const existingZone = cam.roiZones[0];
      if (existingZone) {
        useRoiStore.getState().startEditingZone(existingZone);
      } else {
        startDrawingPolygon(cam.id);
      }
    }
    initializedRouteRef.current = routeKey;
  }, [cam, location.search, startDrawingPolygon]);

  useEffect(() => () => {
    initializedRouteRef.current = null;
    cancelDrawing();
  }, [cancelDrawing]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if ((e.target as HTMLElement)?.tagName === "INPUT" || (e.target as HTMLElement)?.tagName === "TEXTAREA") return;

      if (e.ctrlKey && e.key === "z") {
        e.preventDefault();
        useRoiStore.getState().undo();
      } else if (e.ctrlKey && e.key === "y") {
        e.preventDefault();
        useRoiStore.getState().redo();
      } else if (e.key === "Delete" || e.key === "Backspace") {
        if (useRoiStore.getState().selectedPointIndex !== null && useRoiStore.getState().drawingMode !== "rectangle") {
          e.preventDefault();
          useRoiStore.getState().deleteSelectedPoint();
        }
      } else if (e.key === "Escape") {
        useRoiStore.getState().cancelDrawing();
        navigate(`/cameras/${cam?.id}`);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [cam, navigate]);

  if (!cam) {
    return (
      <div className="p-6">
        <ErrorState
          message={`Không tìm thấy camera với ID: ${cameraId}`}
          onRetry={() => navigate("/roi")}
        />
      </div>
    );
  }

  if (initializationError) {
    return (
      <div className="p-6">
        <ErrorState
          message={initializationError}
          onRetry={() => navigate("/roi")}
        />
      </div>
    );
  }

  // Stepper state mapping based on drawing states
  const getActiveStep = () => {
    if (drawingMode === "idle" && drawingState !== "roi_saved") return 1;
    if (drawingState === "roi_drawing") return 2;
    if (drawingState === "roi_unsaved" || drawingState === "roi_editing" || drawingState === "roi_invalid") return 3;
    if (drawingState === "roi_saved") return 4;
    return 2;
  };

  const steps = [
    { num: 1, label: "Chọn camera", icon: "videocam" },
    { num: 2, label: "Vẽ vùng", icon: "draw" },
    { num: 3, label: "Cấu hình", icon: "tune" },
    { num: 4, label: "Kích hoạt", icon: "verified" }
  ];

  const activeStep = getActiveStep();

  return (
    <div className="p-4 md:p-6 space-y-5">

      {/* Block điều hướng khi draft chưa lưu */}
      <UnsavedChangesBlocker when={hasUnsavedChanges} />
      {/* Header Row */}
      <div className="flex items-center gap-3 animate-fade-in">
        <button
          onClick={() => navigate(`/cameras/${cam.id}`)}
          className="w-10 h-10 rounded-full bg-surface-container-low hover:bg-surface-container-high transition-all flex items-center justify-center text-on-surface focus:outline-none cursor-pointer active:scale-95"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
        </button>
        <div>
          <h2 className="text-lg md:text-2xl font-bold text-on-surface">Thiết lập vùng nguy hiểm</h2>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Camera: <strong className="text-on-surface">{cam.name}</strong>
            <span className="text-outline mx-1.5">•</span>
            <span className="font-semibold text-amber-600">
              Chế độ ảnh tĩnh — không phát luồng, không cảnh báo
            </span>
          </p>
        </div>
      </div>

      {/* Stepper bar */}
      <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-4 shadow-sm max-w-3xl mx-auto animate-slide-up">
        <div className="flex justify-between items-center relative">

          {/* Background progress bar */}
          <div className="absolute left-6 right-6 top-[18px] h-0.5 bg-outline-variant/30 -z-0">
            <div
              className="h-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${((activeStep - 1) / (steps.length - 1)) * 100}%` }}
            ></div>
          </div>

          {steps.map((step) => {
            const isActive = step.num === activeStep;
            const isCompleted = step.num < activeStep;

            return (
              <div key={step.num} className="flex flex-col items-center z-10 select-none stepper-step">
                <div className={`w-9 h-9 rounded-full font-bold text-xs flex items-center justify-center border-2 transition-all duration-300 ${
                  isCompleted
                    ? "bg-primary border-primary text-white scale-100"
                    : isActive
                    ? "bg-white border-primary text-primary ring-4 ring-primary/10 scale-110"
                    : "bg-surface-container-low border-outline-variant/30 text-on-surface-variant scale-95 opacity-60"
                }`}>
                  {isCompleted ? (
                    <span className="material-symbols-outlined text-[16px] fill">check</span>
                  ) : (
                    <span className="material-symbols-outlined text-[16px]">{step.icon}</span>
                  )}
                </div>
                <span className={`text-[9px] md:text-[11px] font-bold mt-2 transition-all duration-300 text-center leading-tight ${
                  isActive ? "text-primary" : isCompleted ? "text-on-surface" : "text-on-surface-variant opacity-60"
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}

        </div>
      </div>

      {/* Mobile orientation hint */}
      <div className="md:hidden bg-amber-500/10 text-amber-800 border border-amber-500/20 px-4 py-3 rounded-xl text-xs flex gap-2 font-medium animate-fade-in">
        <span className="material-symbols-outlined text-[18px] text-amber-600 shrink-0">screen_rotation</span>
        <p className="leading-relaxed">
          <strong>Mẹo:</strong> Xoay ngang điện thoại để có diện tích vẽ lớn hơn.
        </p>
      </div>

      {/* Desktop orientation hint */}
      <div className="hidden md:flex bg-amber-500/8 text-amber-800 border border-amber-500/15 px-4 py-3 rounded-xl text-xs gap-2 font-medium animate-fade-in">
        <span className="material-symbols-outlined text-[18px] text-amber-600 shrink-0">info</span>
        <p className="leading-relaxed">
          <strong>Phím tắt:</strong> Ctrl+Z (Hoàn tác) • Ctrl+Y (Làm lại) • Del (Xóa điểm) • Esc (Thoát)
        </p>
      </div>

      {/* Main Drawing Area: Grid container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Left Column: Canvas and Drawing Toolbar */}
        <div className="lg:col-span-2 space-y-4">
          {/* SVG Canvas drawing tool */}
          <ROISVGOverlay
            cameraId={cam.id}
            cameraName={cam.name}
          />

          {/* Draw Toolbar */}
          <ROIToolbar />
        </div>

        {/* Right Column: Setting rules Panel */}
        <div className="space-y-4">
          <ROISettingsPanel />
        </div>

      </div>

    </div>
  );
};
export default ROIDrawingView;
