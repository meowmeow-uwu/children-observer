import React from "react";
import { useRoiStore } from "../../store/roiStore";
import type { ROIZone } from "../../types";

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
      startEditingZone(draftZone as ROIZone);
    }
  };

  // Tool button component for consistency
  const ToolBtn: React.FC<{
    onClick: () => void;
    active?: boolean;
    disabled?: boolean;
    icon: string;
    label: string;
    title: string;
    shortcut?: string;
    variant?: "default" | "danger" | "success";
  }> = ({ onClick, active, disabled, icon, label, title, shortcut, variant = "default" }) => {
    const baseClass = "py-2 px-3 min-h-[44px] text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer";
    const disabledClass = "disabled:opacity-40 disabled:cursor-not-allowed disabled:focus:ring-0";

    let variantClass = "";
    if (active) {
      variantClass = "bg-primary text-white shadow-sm";
    } else if (variant === "danger") {
      variantClass = "bg-surface-container-low hover:bg-red-500/10 text-on-surface hover:text-error";
    } else if (variant === "success") {
      variantClass = "bg-emerald-500 text-white hover:bg-emerald-600 shadow-sm";
    } else {
      variantClass = "bg-surface-container-low text-on-surface hover:bg-surface-container-high";
    }

    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        title={shortcut ? `${title} (${shortcut})` : title}
        aria-label={label || title}
        className={`${baseClass} ${variantClass} ${disabledClass}`}
      >
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{icon}</span>
        <span className="hidden sm:inline">{label}</span>
      </button>
    );
  };

  return (
    <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-3 shadow-sm animate-slide-up">
      {/* Responsive: wrap on mobile, single row on desktop */}
      <div className="flex flex-wrap items-center gap-2">

        {/* Drawing Mode Selection */}
        <div className="flex items-center gap-1.5 shrink-0 border-r border-outline-variant/20 pr-2.5">
          <ToolBtn
            onClick={handlePolygonClick}
            active={drawingMode === "polygon"}
            icon="polyline"
            label="Đa giác"
            title="Vẽ vùng đa giác tự do"
          />

          <ToolBtn
            onClick={handleRectangleClick}
            active={drawingMode === "rectangle"}
            icon="crop_square"
            label="Hình chữ nhật"
            title="Vẽ vùng hình chữ nhật (2 góc đối diện)"
          />

          <ToolBtn
            onClick={handleEditClick}
            disabled={!draftZone || draftPoints.length === 0}
            active={drawingMode === "edit"}
            icon="edit"
            label="Chỉnh sửa"
            title="Kéo thả các điểm neo"
          />
        </div>

        {/* Editing Actions */}
        <div className="flex items-center gap-1.5 shrink-0">

          {/* Delete selected point */}
          <ToolBtn
            onClick={deleteSelectedPoint}
            disabled={selectedPointIndex === null}
            icon="delete_forever"
            label=""
            title="Xóa điểm đang chọn"
            shortcut="Del"
            variant="danger"
          />

          {/* Undo */}
          <ToolBtn
            onClick={undo}
            disabled={undoStack.length === 0}
            icon="undo"
            label=""
            title="Hoàn tác"
            shortcut="Ctrl+Z"
          />

          {/* Redo */}
          <ToolBtn
            onClick={redo}
            disabled={redoStack.length === 0}
            icon="redo"
            label=""
            title="Làm lại"
            shortcut="Ctrl+Y"
          />

          {/* Clear All */}
          <ToolBtn
            onClick={resetDraft}
            disabled={draftPoints.length === 0}
            icon="clear_all"
            label="Xóa nét vẽ"
            title="Xóa toàn bộ nét vẽ hiện tại"
            variant="danger"
          />

          {/* Complete Polygon zone */}
          {drawingMode === "polygon" && drawingState === "roi_drawing" && (
            <ToolBtn
              onClick={completeZone}
              disabled={draftPoints.length < 3}
              icon="done_all"
              label="Hoàn tất vùng"
              title="Khép kín và hoàn thành đa giác"
              variant="success"
            />
          )}
        </div>

        {/* Status indicator on right */}
        {draftPoints.length > 0 && (
          <div className="ml-auto hidden md:flex items-center gap-2 text-[10px] font-bold text-on-surface-variant bg-surface-container-low px-3 py-1.5 rounded-lg">
            <span className={`w-1.5 h-1.5 rounded-full ${
              drawingState === "roi_saved" ? "bg-emerald-500" :
              drawingState === "roi_unsaved" ? "bg-amber-500" :
              drawingState === "roi_invalid" ? "bg-error" :
              "bg-primary"
            }`}></span>
            {drawingState === "roi_saved" ? "Đã lưu" :
             drawingState === "roi_unsaved" ? "Chưa lưu" :
             drawingState === "roi_invalid" ? "Không hợp lệ" :
             "Đang vẽ"
            }
            <span className="text-outline">•</span>
            <span>{draftPoints.length} điểm</span>
          </div>
        )}
      </div>
    </div>
  );
};
export default ROIToolbar;
