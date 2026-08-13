import React from "react";
import { useRoiStore } from "../../store/roiStore";

export const ROIToolbar: React.FC = () => {
  const {
    drawingMode,
    drawingState,
    draftPoints,
    undoStack,
    redoStack,
    selectedPointIndex,
    startDrawingPolygon,
    startDrawingRectangle,
    startEditingZone,
    deleteSelectedPoint,
    undo,
    redo,
    resetDraft,
    completeZone,
    draftZone
  } = useRoiStore();

  const cameraId = draftZone?.cameraId || "";

  const handlePolygonClick = () => {
    if (drawingMode === "polygon") return;
    startDrawingPolygon(cameraId);
  };

  const handleRectangleClick = () => {
    if (drawingMode === "rectangle") return;
    startDrawingRectangle(cameraId);
  };

  const handleEditClick = () => {
    if (draftZone && drawingMode !== "edit") {
      startEditingZone(draftZone as any);
    }
  };

  return (
    <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-3 shadow-sm flex items-center overflow-x-auto w-full gap-2.5 scrollbar-thin">
      
      {/* Modes Selection */}
      <div className="flex items-center gap-1.5 shrink-0 border-r border-outline-variant/30 pr-2.5">
        <button
          type="button"
          onClick={handlePolygonClick}
          className={`py-2 px-3.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none ${
            drawingMode === "polygon"
              ? "bg-primary text-white"
              : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">polyline</span>
          Đa giác
        </button>

        <button
          type="button"
          onClick={handleRectangleClick}
          className={`py-2 px-3.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none ${
            drawingMode === "rectangle"
              ? "bg-primary text-white"
              : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">rectangle</span>
          Hình chữ nhật
        </button>

        <button
          type="button"
          onClick={handleEditClick}
          disabled={!draftZone || draftPoints.length === 0}
          className={`py-2 px-3.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed ${
            drawingMode === "edit"
              ? "bg-primary text-white"
              : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">edit</span>
          Chỉnh sửa điểm
        </button>
      </div>

      {/* Editing Point Actions */}
      <div className="flex items-center gap-1.5 shrink-0">
        
        {/* Delete selected point */}
        <button
          type="button"
          onClick={deleteSelectedPoint}
          disabled={selectedPointIndex === null || drawingMode === "rectangle"}
          className="p-2 bg-surface-container-low hover:bg-red-500/10 text-on-surface hover:text-error disabled:opacity-45 disabled:cursor-not-allowed disabled:text-on-surface-variant rounded-xl transition-all flex items-center justify-center focus:outline-none"
          title="Xóa điểm đang chọn"
        >
          <span className="material-symbols-outlined text-[20px]">delete_forever</span>
        </button>

        {/* Undo */}
        <button
          type="button"
          onClick={undo}
          disabled={undoStack.length === 0}
          className="p-2 bg-surface-container-low hover:bg-surface-container-high text-on-surface disabled:opacity-45 disabled:cursor-not-allowed disabled:text-on-surface-variant rounded-xl transition-all flex items-center justify-center focus:outline-none"
          title="Hoàn tác"
        >
          <span className="material-symbols-outlined text-[20px]">undo</span>
        </button>

        {/* Redo */}
        <button
          type="button"
          onClick={redo}
          disabled={redoStack.length === 0}
          className="p-2 bg-surface-container-low hover:bg-surface-container-high text-on-surface disabled:opacity-45 disabled:cursor-not-allowed disabled:text-on-surface-variant rounded-xl transition-all flex items-center justify-center focus:outline-none"
          title="Làm lại"
        >
          <span className="material-symbols-outlined text-[20px]">redo</span>
        </button>

        {/* Clear Area points */}
        <button
          type="button"
          onClick={resetDraft}
          disabled={draftPoints.length === 0}
          className="py-2 px-3 text-xs font-bold bg-surface-container-low hover:bg-red-500/10 text-on-surface hover:text-error disabled:opacity-45 disabled:cursor-not-allowed rounded-xl transition-all flex items-center gap-1.5 focus:outline-none"
        >
          <span className="material-symbols-outlined text-[18px]">clear_all</span>
          Xóa nét vẽ
        </button>

        {/* Complete Polygon zone */}
        {drawingMode === "polygon" && drawingState === "roi_drawing" && (
          <button
            type="button"
            onClick={completeZone}
            disabled={draftPoints.length < 3}
            className="py-2 px-4 text-xs font-bold bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-45 disabled:cursor-not-allowed rounded-xl transition-all flex items-center gap-1.5 focus:outline-none shadow-sm ml-2"
          >
            <span className="material-symbols-outlined text-[18px]">done_all</span>
            Hoàn tất vùng
          </button>
        )}

      </div>
    </div>
  );
};
export default ROIToolbar;
