import React from "react";
import { useNavigate } from "react-router-dom";
import { useRoiStore } from "../../store/roiStore";
import { useCameraStore } from "../../store/cameraStore";
import { useToast } from "../Toast";

import { saveCameraRoiApi } from "../../services/api";

export const ROISettingsPanel: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const {
    draftZone,
    draftPoints,
    saveDraftZone,
    cancelDrawing,
    setZoneName,
    setSensitivity,
    toggleRule,
    validationError
  } = useRoiStore();

  const { cameras } = useCameraStore();

  if (!draftZone) {
    return (
      <div className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/30 text-center text-outline text-xs">
        Chọn công cụ "Đa giác" hoặc "Hình chữ nhật" để bắt đầu thiết lập vùng nguy hiểm.
      </div>
    );
  }

  const camera = cameras.find((c) => c.id === draftZone.cameraId);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = saveDraftZone();
    if (success) {
      const currentZone = useRoiStore.getState().zones.find((z) => z.id === draftZone.id);
      if (currentZone) {
        await saveCameraRoiApi(draftZone.cameraId, [{
          name: currentZone.name,
          points: currentZone.points,
          sensitivity: currentZone.sensitivity,
          enabled: currentZone.enabled
        }]);
      }
      showToast("Đã lưu và đồng bộ vùng nguy hiểm thành công!", "success");
      navigate(`/cameras/${draftZone.cameraId}`);
    } else {
      showToast(validationError || "Thông tin cấu hình chưa hợp lệ!", "error");
    }
  };

  const handleCancel = () => {
    cancelDrawing();
    navigate(`/cameras/${draftZone.cameraId}`);
  };

  const activeRulesCount = Object.values(draftZone.rules || {}).filter(Boolean).length;

  return (
    <form onSubmit={handleSave} className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-6 flex flex-col justify-between">
      <div className="space-y-5">
        <h3 className="font-bold text-on-surface text-base border-b border-outline-variant/10 pb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">settings_accessibility</span>
          Cấu hình Vùng nguy hiểm
        </h3>

        {/* Camera info */}
        <div>
          <span className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Camera áp dụng</span>
          <span className="font-semibold text-sm text-on-surface block mt-1 bg-surface-container-low px-3 py-2 rounded-xl border border-outline-variant/20">
            {camera?.name || "Unknown Camera"}
          </span>
        </div>

        {/* Zone Name Input */}
        <div>
          <label className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1">
            Tên vùng nguy hiểm
          </label>
          <input
            type="text"
            value={draftZone.name || ""}
            onChange={(e) => setZoneName(e.target.value)}
            placeholder="Ví dụ: Lan can ban công, Cửa bếp, Lối cầu thang..."
            className="w-full p-3 border border-outline-variant rounded-xl text-xs bg-surface-container-low text-on-surface focus:ring-1 focus:ring-primary focus:outline-none"
            required
          />
        </div>

        {/* Sensitivity Selector */}
        <div>
          <label className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1.5">
            Độ nhạy phân tích (Sensitivity)
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(["low", "medium", "high"] as const).map((level) => (
              <button
                type="button"
                key={level}
                onClick={() => setSensitivity(level)}
                className={`py-2 text-xs font-semibold rounded-xl border transition-all focus:outline-none ${
                  draftZone.sensitivity === level
                    ? "bg-primary/5 border-primary text-primary font-bold"
                    : "bg-surface-container-low border-outline-variant/20 text-on-surface-variant hover:border-outline-variant"
                }`}
              >
                {level === "low" ? "Thấp" : level === "medium" ? "Trung bình" : "Cao"}
              </button>
            ))}
          </div>
        </div>

        {/* Alarm Rules */}
        <div className="space-y-3">
          <label className="block text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">
            Quy tắc cảnh báo kích hoạt
          </label>
          
          <div className="space-y-2">
            {/* Rule 1: Enter zone */}
            <label className="flex items-start gap-3 p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl cursor-pointer">
              <input
                type="checkbox"
                checked={draftZone.rules?.enterZone || false}
                onChange={() => toggleRule("enterZone")}
                className="mt-0.5 rounded text-primary focus:ring-primary"
              />
              <div>
                <span className="font-bold text-xs block text-on-surface">Trẻ đi vào vùng nguy hiểm</span>
                <span className="text-[10px] text-on-surface-variant block mt-0.5">Cảnh báo ngay lập tức khi phát hiện biên độ bé chạm vào vùng.</span>
              </div>
            </label>

            {/* Rule 2: Stay too long */}
            <label className="flex items-start gap-3 p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl cursor-pointer">
              <input
                type="checkbox"
                checked={draftZone.rules?.stayTooLong || false}
                onChange={() => toggleRule("stayTooLong")}
                className="mt-0.5 rounded text-primary focus:ring-primary"
              />
              <div>
                <span className="font-bold text-xs block text-on-surface">Trẻ đứng trong vùng &gt; 5 giây</span>
                <span className="text-[10px] text-on-surface-variant block mt-0.5">Tránh cảnh báo giả khi trẻ chỉ đi lướt qua nhặt đồ chơi.</span>
              </div>
            </label>

            {/* Rule 3: Approach zone */}
            <label className="flex items-start gap-3 p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl cursor-pointer">
              <input
                type="checkbox"
                checked={draftZone.rules?.approachZone || false}
                onChange={() => toggleRule("approachZone")}
                className="mt-0.5 rounded text-primary focus:ring-primary"
              />
              <div>
                <span className="font-bold text-xs block text-on-surface">Trẻ tiến lại gần ranh giới</span>
                <span className="text-[10px] text-on-surface-variant block mt-0.5">Phân tích hướng chuyển động để gửi cảnh báo phòng ngừa sớm.</span>
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
            <li>Loại hình vẽ: <strong className="text-on-surface capitalize">{draftZone.type === "rectangle" ? "Hình chữ nhật" : "Đa giác"}</strong></li>
            <li>Số điểm neo vẽ: <strong className="text-on-surface">{draftPoints.length} điểm</strong></li>
            <li>Độ nhạy: <strong className="text-on-surface capitalize">{draftZone.sensitivity === "high" ? "Cao" : draftZone.sensitivity === "medium" ? "Trung bình" : "Thấp"}</strong></li>
            <li>Quy tắc: <strong className="text-on-surface">{activeRulesCount} quy tắc đang bật</strong></li>
          </ul>
        </div>

        {/* Validation Errors */}
        {validationError && (
          <div className="p-3 bg-red-500/10 text-error border border-error/20 rounded-xl text-xs font-semibold leading-relaxed flex items-start gap-1.5">
            <span className="material-symbols-outlined text-[18px] shrink-0">error</span>
            {validationError}
          </div>
        )}
      </div>

      {/* Submit controls */}
      <div className="mt-8 grid grid-cols-2 gap-3 border-t border-outline-variant/10 pt-4">
        <button
          type="button"
          onClick={handleCancel}
          className="py-3 bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-bold rounded-xl transition-colors focus:outline-none"
        >
          Hủy bỏ
        </button>
        <button
          type="submit"
          className="py-3 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl transition-all shadow-md focus:outline-none"
        >
          Lưu thiết lập
        </button>
      </div>

    </form>
  );
};
export default ROISettingsPanel;
