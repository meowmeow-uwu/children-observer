import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRoiStore } from "../../store/roiStore";
import { useCameraStore } from "../../store/cameraStore";
import { useToast } from "../Toast";

import { saveCameraRoiApi } from "../../services/api";

const SENSITIVITY_EXPLAIN: Record<string, string> = {
  low: "Chấp nhận detection yếu hơn (conf ≥ 0.05), cần 5 frame xác nhận — ít cảnh báo hơn.",
  medium: "Cân bằng: conf ≥ 0.10, cần 3 frame xác nhận — phù hợp mặc định.",
  high: "Chỉ tin detection rõ (conf ≥ 0.15), 2 frame xác nhận — cảnh báo sớm nhất.",
};

export const ROISettingsPanel: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [isMobileExpanded, setIsMobileExpanded] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const {
    draftZone,
    draftPoints,
    drawingState,
    saveDraftZone,
    cancelDrawing,
    setZoneName,
    setSensitivity,
    toggleRule,
    setStayDurationSeconds,
    validationError
  } = useRoiStore();

  const { cameras } = useCameraStore();

  if (!draftZone) {
    return (
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/30 text-center text-outline text-xs animate-fade-in">
        <span className="material-symbols-outlined text-[32px] text-outline/40 block mb-2">draw</span>
        Chọn công cụ "Đa giác" hoặc "Hình chữ nhật" để bắt đầu thiết lập vùng nguy hiểm.
      </div>
    );
  }

  const camera = cameras.find((c) => c.id === draftZone.cameraId);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;

    const savedZone = saveDraftZone();
    if (!savedZone) {
      showToast(validationError || "Thông tin cấu hình chưa hợp lệ!", "error");
      return;
    }

    const cId = savedZone.cameraId;
    // Gửi TOÀN BỘ danh sách zone của camera (replace-whole-list có chủ đích)
    const allCameraZones = useRoiStore.getState().zones.filter((z) => z.cameraId === cId);
    setIsSaving(true);
    try {
      const serverZones = await saveCameraRoiApi(cId, allCameraZones);
      // Rehydrate từ bản server trả về (canonical) — không giữ id/draft local
      useRoiStore.getState().setZonesFromServer(serverZones, cId);
      showToast("Đã lưu và đồng bộ vùng nguy hiểm thành công!", "success");
      navigate(`/cameras/${cId}`);
    } catch (err) {
      console.error("Lưu ROI thất bại:", err);
      showToast(`Lưu thất bại: ${err instanceof Error ? err.message : "lỗi không xác định"} — vui lòng thử lại.`, "error");
      // KHÔNG rời trang khi API thất bại — khôi phục draft với đầy đủ điểm đã vẽ
      useRoiStore.getState().startEditingZone(savedZone);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    cancelDrawing();
    navigate(`/cameras/${draftZone.cameraId}`);
  };

  // Chỉ đếm 3 rule boolean thực sự (stayDurationSeconds là tham số, không phải rule)
  const booleanRules = ["enterZone", "stayTooLong", "approachZone"] as const;
  const activeRulesCount = booleanRules.filter((key) => draftZone.rules?.[key]).length;

  const sensitivityConfig = {
    low: { label: "Thấp", color: "text-emerald-600", bg: "bg-emerald-500/10 border-emerald-500/30", pos: "16.5%" },
    medium: { label: "Trung bình", color: "text-amber-600", bg: "bg-amber-500/10 border-amber-500/30", pos: "50%" },
    high: { label: "Cao", color: "text-red-600", bg: "bg-red-500/10 border-red-500/30", pos: "83.5%" }
  };

  const currentSensitivity = sensitivityConfig[draftZone.sensitivity || "medium"];

  return (
    <form onSubmit={handleSave} className="bg-surface-container-lowest rounded-2xl border border-outline-variant/30 shadow-sm flex flex-col justify-between animate-slide-up overflow-hidden">

      {/* Mobile collapse header */}
      <button
        type="button"
        onClick={() => setIsMobileExpanded(!isMobileExpanded)}
        className="lg:hidden flex items-center justify-between w-full p-4 text-left cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">settings_accessibility</span>
          <span className="font-bold text-on-surface text-sm">Cấu hình vùng nguy hiểm</span>
        </div>
        <span className={`material-symbols-outlined text-on-surface-variant transition-transform duration-200 ${isMobileExpanded ? "rotate-180" : ""}`}>
          expand_more
        </span>
      </button>

      {/* Desktop header (always visible) */}
      <div className="hidden lg:block p-5 pb-0">
        <h3 className="font-bold text-on-surface text-base border-b border-outline-variant/10 pb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">settings_accessibility</span>
          Cấu hình Vùng nguy hiểm
        </h3>
      </div>

      {/* Collapsible content */}
      <div className={`transition-all duration-300 ease-in-out overflow-hidden ${isMobileExpanded ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0 lg:max-h-[2000px] lg:opacity-100"}`}>
        <div className="p-5 pt-2 lg:pt-5 space-y-5">

          {/* Camera info */}
          <div>
            <span className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Camera áp dụng</span>
            <span className="font-semibold text-sm text-on-surface block mt-1 bg-surface-container-low px-3 py-2 rounded-xl border border-outline-variant/20">
              {camera?.name || "Unknown Camera"}
            </span>
          </div>

          {/* Zone name */}
          <div>
            <label htmlFor="roi-zone-name" className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">
              Tên vùng nguy hiểm <span className="text-error">*</span>
            </label>
            <input
              id="roi-zone-name"
              type="text"
              value={draftZone.name}
              onChange={(e) => setZoneName(e.target.value)}
              placeholder="VD: Khu vực ổ điện học tập"
              maxLength={80}
              required
              className="w-full px-3 py-2.5 text-sm font-semibold text-on-surface bg-surface-container-low border border-outline-variant/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-outline/60"
            />
          </div>

          {/* Sensitivity Selector with Visual Bar */}
          <div>
            <label className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">
              Độ nhạy phân tích (Sensitivity)
            </label>

            {/* Gradient bar indicator */}
            <div className="relative w-full mb-3 roi-sensitivity-bar">
              <div
                className="absolute top-1/2 w-3.5 h-3.5 rounded-full bg-white border-2 border-on-surface shadow-md transition-all duration-300"
                style={{ left: currentSensitivity.pos, transform: "translate(-50%, -50%)" }}
              ></div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {(["low", "medium", "high"] as const).map((level) => {
                const cfg = sensitivityConfig[level];
                return (
                  <button
                    type="button"
                    key={level}
                    onClick={() => setSensitivity(level)}
                    className={`py-2 text-xs font-semibold rounded-xl border transition-all focus:outline-none cursor-pointer ${
                      draftZone.sensitivity === level
                        ? `${cfg.bg} ${cfg.color} font-bold`
                        : "bg-surface-container-low border-outline-variant/20 text-on-surface-variant hover:border-outline-variant"
                    }`}
                  >
                    {cfg.label}
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-on-surface-variant mt-2 leading-relaxed">
              {SENSITIVITY_EXPLAIN[draftZone.sensitivity || "medium"]}
            </p>
          </div>

          {/* Alarm Rules */}
          <div className="space-y-3">
            <label className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">
              Quy tắc cảnh báo kích hoạt
            </label>

            <div className="space-y-2">
              {/* Rule 1: Enter zone */}
              <label className="flex items-start gap-3 p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl cursor-pointer hover:border-outline-variant/30 transition-all">
                <input
                  type="checkbox"
                  checked={draftZone.rules?.enterZone || false}
                  onChange={() => toggleRule("enterZone")}
                  className="mt-0.5 rounded text-primary focus:ring-primary cursor-pointer"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Trẻ đi vào vùng nguy hiểm</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Cảnh báo ngay khi track ổn định trong vùng N frame (theo độ nhạy).</span>
                </div>
              </label>

              {/* Rule 2: Stay too long */}
              <label className="flex items-start gap-3 p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl cursor-pointer hover:border-outline-variant/30 transition-all">
                <input
                  type="checkbox"
                  checked={draftZone.rules?.stayTooLong || false}
                  onChange={() => toggleRule("stayTooLong")}
                  className="mt-0.5 rounded text-primary focus:ring-primary cursor-pointer"
                />
                <div className="flex-1">
                  <span className="font-bold text-xs block text-on-surface">Trẻ đứng trong vùng quá lâu</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Cùng track_id ở trong vùng đủ số giây mới cảnh báo.</span>
                  {draftZone.rules?.stayTooLong && (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-[10px] text-on-surface-variant font-medium">Ngưỡng:</span>
                      <input
                        type="number"
                        min={1}
                        max={3600}
                        value={draftZone.rules?.stayDurationSeconds || 5}
                        onChange={(e) => setStayDurationSeconds(Number(e.target.value))}
                        aria-label="Số giây đứng trong vùng để cảnh báo"
                        className="w-20 px-2 py-1 text-xs font-bold text-primary bg-primary/5 border border-primary/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                      <span className="text-[10px] text-on-surface-variant font-medium">giây</span>
                    </div>
                  )}
                </div>
              </label>

              {/* Rule 3: Approach zone */}
              <label className="flex items-start gap-3 p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl cursor-pointer hover:border-outline-variant/30 transition-all">
                <input
                  type="checkbox"
                  checked={draftZone.rules?.approachZone || false}
                  onChange={() => toggleRule("approachZone")}
                  className="mt-0.5 rounded text-primary focus:ring-primary cursor-pointer"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Trẻ tiến lại gần ranh giới</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Khoảng cách tới biên giảm liên tục và nằm trong margin theo độ nhạy.</span>
                </div>
              </label>
            </div>
          </div>

          {/* Summary Block */}
          <div className="p-3 bg-primary-container/10 border border-primary-container/20 text-on-primary-container rounded-xl text-xs space-y-1.5">
            <p className="font-bold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px]">info</span>
              Tóm tắt vùng giám sát:
            </p>
            <ul className="space-y-0.5 text-[11px] list-disc list-inside font-medium text-on-surface-variant">
              <li>Tên vùng: <strong className="text-on-surface">{draftZone.name || "Chưa đặt tên"}</strong></li>
              <li>Loại hình vẽ: <strong className="text-on-surface capitalize">{draftZone.type === "rectangle" ? "Hình chữ nhật" : "Đa giác"}</strong></li>
              <li>Số điểm neo vẽ: <strong className="text-on-surface">{draftPoints.length} điểm</strong></li>
              <li>Độ nhạy: <strong className={currentSensitivity.color}>{currentSensitivity.label}</strong></li>
              <li>Quy tắc: <strong className="text-on-surface">{activeRulesCount} quy tắc đang bật</strong></li>
              <li>Trạng thái: <strong className={
                drawingState === "roi_unsaved" ? "text-amber-600" :
                drawingState === "roi_saved" ? "text-emerald-600" :
                drawingState === "roi_invalid" ? "text-error" :
                "text-primary"
              }>{
                drawingState === "roi_unsaved" ? "Chưa lưu" :
                drawingState === "roi_saved" ? "Đã lưu" :
                drawingState === "roi_invalid" ? "Không hợp lệ" :
                "Đang vẽ"
              }</strong></li>
            </ul>
          </div>

          {/* Validation Errors */}
          {validationError && (
            <div className="p-3 bg-red-500/10 text-error border border-error/20 rounded-xl text-xs font-semibold leading-relaxed flex items-start gap-1.5 animate-scale-up">
              <span className="material-symbols-outlined text-[18px] shrink-0">error</span>
              {validationError}
            </div>
          )}
        </div>

        {/* Submit controls */}
        <div className="p-5 pt-0">
          <div className="grid grid-cols-2 gap-3 border-t border-outline-variant/10 pt-4">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isSaving}
              className="py-3 bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-bold rounded-xl transition-colors focus:outline-none cursor-pointer disabled:opacity-50"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="py-3 bg-primary hover:bg-primary/90 text-white text-xs font-bold rounded-xl transition-all shadow-md focus:outline-none cursor-pointer active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSaving ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Đang lưu...
                </>
              ) : (
                "Lưu thiết lập"
              )}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
};
export default ROISettingsPanel;
