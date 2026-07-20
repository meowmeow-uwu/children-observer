import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRoiStore } from "../store/roiStore";
import { useCameraStore } from "../store/cameraStore";
import { useToast } from "../components/Toast";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";

export const ROIListView: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const { zones, setEnabled, deleteZone } = useRoiStore();
  const { cameras } = useCameraStore();

  const [zoneToDeleteId, setZoneToDeleteId] = useState<string | null>(null);

  const getCameraName = (cameraId: string) => {
    const cam = cameras.find((c) => c.id === cameraId);
    return cam ? cam.name : "Camera không khả dụng";
  };

  const handleToggleZone = (zoneId: string, enabled: boolean) => {
    setEnabled(zoneId, !enabled);
    showToast(`Đã ${!enabled ? "kích hoạt" : "vô hiệu hóa"} vùng nguy hiểm`, "info");
  };

  const handleDeleteConfirm = () => {
    if (zoneToDeleteId) {
      deleteZone(zoneToDeleteId);
      setZoneToDeleteId(null);
      showToast("Đã xóa vùng nguy hiểm thành công", "success");
    }
  };

  const getActiveRulesText = (rules: any) => {
    const list = [];
    if (rules?.enterZone) list.push("Đi vào vùng");
    if (rules?.stayTooLong) list.push("Đứng lâu >5s");
    if (rules?.approachZone) list.push("Lại gần ranh giới");
    return list.length > 0 ? list.join(", ") : "Không có quy tắc";
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Vùng nguy hiểm ROI đang hoạt động</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Danh sách các khu vực rào chắn AI đang giám sát trẻ em trong ngôi nhà của bạn.
          </p>
        </div>

        {cameras.length > 0 && (
          <button
            onClick={() => navigate(`/roi/${cameras[0].id}`)}
            className="py-2.5 px-4 bg-primary text-white hover:bg-primary/95 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none shrink-0 shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Tạo vùng nguy hiểm đầu tiên
          </button>
        )}
      </div>

      {/* ROI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {zones.map((zone) => (
          <div
            key={zone.id}
            className={`bg-surface-container-lowest p-5 rounded-2xl border transition-all flex flex-col justify-between shadow-sm hover:shadow-md ${
              zone.enabled ? "border-outline-variant/30" : "border-outline-variant/10 opacity-70"
            }`}
          >
            <div>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-bold text-sm md:text-base text-on-surface">{zone.name}</h3>
                  <p className="text-xs text-on-surface-variant mt-0.5 font-semibold">Camera: {getCameraName(zone.cameraId)}</p>
                </div>
                
                {/* Enable toggle */}
                <button
                  onClick={() => handleToggleZone(zone.id, zone.enabled)}
                  className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center shrink-0 ${
                    zone.enabled ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
                </button>
              </div>

              {/* Specs */}
              <div className="space-y-2.5 py-3 border-t border-b border-outline-variant/10 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-on-surface-variant font-medium">Trạng thái:</span>
                  <span className={`font-semibold ${zone.enabled ? "text-emerald-500" : "text-outline"}`}>
                    {zone.enabled ? "✓ Đang giám sát" : "⏸ Đang tạm dừng"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-on-surface-variant font-medium">Độ nhạy AI:</span>
                  <StatusBadge type={zone.sensitivity === "high" ? "danger" : zone.sensitivity === "medium" ? "warning" : "info"} label={zone.sensitivity === "high" ? "Cao" : zone.sensitivity === "medium" ? "Trung bình" : "Thấp"} />
                </div>
                <div className="space-y-1">
                  <span className="text-on-surface-variant font-medium block">Quy tắc đã chọn:</span>
                  <span className="font-semibold text-on-surface text-[11px] leading-relaxed block pl-2 border-l border-primary/20">
                    {getActiveRulesText(zone.rules)}
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-5 pt-3 flex gap-2">
              <button
                onClick={() => navigate(`/roi/${zone.cameraId}`)}
                className="flex-1 py-2 text-xs font-bold bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-xl transition-all text-center focus:outline-none"
              >
                Chỉnh sửa
              </button>
              <button
                onClick={() => setZoneToDeleteId(zone.id)}
                className="py-2 px-3.5 bg-red-500/5 hover:bg-red-500/10 text-error rounded-xl transition-all focus:outline-none flex items-center justify-center"
                title="Xóa vùng nguy hiểm"
              >
                <span className="material-symbols-outlined text-[18px]">delete</span>
              </button>
            </div>

          </div>
        ))}
      </div>

      {zones.length === 0 && (
        <EmptyState
          icon="detector_status"
          title="Chưa thiết lập vùng nguy hiểm"
          description="Hãy tạo khu vực giám sát thông minh đầu tiên xung quanh ổ điện, cửa sổ, ban công để hệ thống AI bảo vệ bé."
          action={
            cameras.length > 0 ? (
              <button
                onClick={() => navigate(`/roi/${cameras[0].id}`)}
                className="py-2.5 px-6 bg-primary text-white font-bold rounded-xl text-xs shadow-sm hover:bg-primary/95 focus:outline-none"
              >
                Tạo vùng nguy hiểm đầu tiên
              </button>
            ) : undefined
          }
        />
      )}

      {/* Confirm Delete Dialog */}
      {zoneToDeleteId && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-2xl max-w-sm w-full p-6 shadow-xl border border-outline-variant/20 animate-scale-up text-center">
            <div className="w-14 h-14 rounded-full bg-error/10 text-error flex items-center justify-center mx-auto mb-4">
              <span className="material-symbols-outlined text-[32px] fill">delete</span>
            </div>
            
            <h3 className="font-bold text-on-surface text-base mb-2">Xác nhận xóa vùng nguy hiểm?</h3>
            <p className="text-xs text-on-surface-variant leading-relaxed mb-6">
              Bạn có chắc chắn muốn xóa vùng nguy hiểm này không? Hệ thống AI sẽ ngưng theo dõi ranh giới an toàn tại vùng này ngay lập tức.
            </p>

            <div className="flex gap-2">
              <button
                onClick={() => setZoneToDeleteId(null)}
                className="flex-1 py-2.5 rounded-lg bg-surface-container-high text-xs font-bold text-on-surface hover:bg-surface-container-highest"
              >
                Hủy bỏ
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 py-2.5 rounded-lg bg-error text-white text-xs font-bold hover:bg-error/90"
              >
                Đúng, xóa đi
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
export default ROIListView;
