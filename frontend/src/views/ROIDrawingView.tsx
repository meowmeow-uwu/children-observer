import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { useRoiStore } from "../store/roiStore";
import { ROISVGOverlay } from "../components/ROI/ROISVGOverlay";
import { ROIToolbar } from "../components/ROI/ROIToolbar";
import { ROISettingsPanel } from "../components/ROI/ROISettingsPanel";
import { ErrorState } from "../components/ErrorState";

export const ROIDrawingView: React.FC = () => {
  const { cameraId } = useParams<{ cameraId: string }>();
  const navigate = useNavigate();

  const { cameras } = useCameraStore();
  const { startDrawingPolygon, cancelDrawing, drawingMode, draftZone } = useRoiStore();

  const cam = cameras.find((c) => c.id === cameraId);

  useEffect(() => {
    if (cam) {
      // Load existing zone if it exists, otherwise start a fresh polygon
      const existingZone = useRoiStore.getState().zones.find((z) => z.cameraId === cam.id);
      if (existingZone) {
        useRoiStore.getState().startEditingZone(existingZone);
      } else {
        startDrawingPolygon(cam.id);
      }
    }

    return () => {
      // Clean up drawing store when leaving the page
      cancelDrawing();
    };
  }, [cameraId, cam, startDrawingPolygon, cancelDrawing]);

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

  // Stepper state mapping based on drawing states
  const getActiveStep = () => {
    if (drawingMode === "idle") return 1;
    if (draftZone && (!draftZone.name || useRoiStore.getState().draftPoints.length === 0)) return 2;
    return 3; // Setting rules
  };

  const steps = [
    { num: 1, label: "Chọn camera" },
    { num: 2, label: "Vẽ vùng nguy hiểm" },
    { num: 3, label: "Thiết lập cảnh báo" },
    { num: 4, label: "Kích hoạt" }
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      
      {/* Header Row */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(`/cameras/${cam.id}`)}
          className="w-10 h-10 rounded-full bg-surface-container-low hover:bg-surface-container-high transition-all flex items-center justify-center text-on-surface focus:outline-none"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
        </button>
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Thiết lập vùng nguy hiểm (ROI)</h2>
          <p className="text-xs md:text-sm text-on-surface-variant mt-0.5">Camera đang áp dụng: <strong className="text-on-surface">{cam.name}</strong></p>
        </div>
      </div>

      {/* Stepper bar */}
      <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-4 shadow-sm max-w-3xl mx-auto">
        <div className="flex justify-between items-center relative">
          
          {/* Background progress bar */}
          <div className="absolute left-6 right-6 top-4 h-0.5 bg-outline-variant/40 -z-0">
            <div 
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${((getActiveStep() - 1) / (steps.length - 1)) * 100}%` }}
            ></div>
          </div>

          {steps.map((step) => {
            const isActive = step.num === getActiveStep();
            const isCompleted = step.num < getActiveStep();
            
            return (
              <div key={step.num} className="flex flex-col items-center z-10 select-none">
                <div className={`w-9 h-9 rounded-full font-bold text-xs flex items-center justify-center border transition-all ${
                  isCompleted
                    ? "bg-primary border-primary text-white"
                    : isActive
                    ? "bg-white border-primary text-primary ring-4 ring-primary-container/20"
                    : "bg-surface-container-low border-outline-variant/30 text-on-surface-variant"
                }`}>
                  {isCompleted ? (
                    <span className="material-symbols-outlined text-[16px] fill">check</span>
                  ) : (
                    step.num
                  )}
                </div>
                <span className={`text-[10px] md:text-xs font-bold mt-2 transition-all ${
                  isActive || isCompleted ? "text-on-surface" : "text-on-surface-variant"
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}

        </div>
      </div>

      {/* Main Drawing Area: Grid container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Canvas and Drawing Toolbar */}
        <div className="lg:col-span-2 space-y-4">
          {/* Drawing mode instructions helper warning */}
          <div className="bg-amber-500/10 text-amber-800 border border-amber-500/20 px-4 py-3.5 rounded-xl text-xs flex gap-2 font-medium">
            <span className="material-symbols-outlined text-[20px] text-amber-600 shrink-0">warning</span>
            <p className="leading-relaxed">
              <strong>Mẹo di động:</strong> Để có diện tích vẽ và tinh chỉnh điểm neo chính xác hơn trên các thiết bị di động, bạn nên <strong>xoay ngang màn hình điện thoại</strong> hoặc thiết lập trên máy tính.
            </p>
          </div>

          {/* SVG Canvas drawing tool */}
          <ROISVGOverlay
            imageSrc="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1200&auto=format&fit=crop"
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
