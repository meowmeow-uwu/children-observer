import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRoiStore } from "../store/roiStore";
import { useCameraStore } from "../store/cameraStore";
import { useToast } from "../components/Toast";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { saveCameraRoiApi } from "../services/api";

export const ROIListView: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const { zones, setEnabled, deleteZone } = useRoiStore();
  const { cameras } = useCameraStore();
  const [zoneToDeleteId, setZoneToDeleteId] = useState<string | null>(null);
  const [showCameraSelect, setShowCameraSelect] = useState(false);

  const getCameraName = (cameraId: string) => {
    const cam = cameras.find((c) => c.id === cameraId);
    return cam ? cam.name : "Camera không khả dụng";
  };

  const getCameraStatus = (cameraId: string) => {
    const cam = cameras.find((c) => c.id === cameraId);
    return cam?.status || "offline";
  };

  /** Đồng bộ toàn bộ zone của camera lên backend; thành công → rehydrate từ server */
  const persistCameraZones = async (cameraId: string, nextZones: typeof zones) => {
    const cameraZones = nextZones.filter((z) => z.cameraId === cameraId);
    try {
      const serverZones = await saveCameraRoiApi(cameraId, cameraZones);
      useRoiStore.getState().setZonesFromServer(serverZones, cameraId);
      return true;
    } catch (err) {
      console.error("Đồng bộ ROI lên backend thất bại:", err);
      return false;
    }
  };

  const handleToggleZone = async (zoneId: string, enabled: boolean) => {
    setEnabled(zoneId, !enabled);
    const nextZones = useRoiStore.getState().zones;
    const zone = nextZones.find((z) => z.id === zoneId);
    if (zone) {
      const ok = await persistCameraZones(zone.cameraId, nextZones);
      if (!ok) {
        // Rollback khi API thất bại
        useRoiStore.getState().setEnabled(zoneId, enabled);
        showToast("Đồng bộ lên máy chủ thất bại — đã khôi phục trạng thái cũ.", "error");
        return;
      }
    }
    showToast(`Đã ${!enabled ? "kích hoạt" : "vô hiệu hóa"} vùng nguy hiểm`, "info");
  };

  const handleDeleteConfirm = async () => {
    const zone = useRoiStore.getState().zones.find((z) => z.id === zoneToDeleteId);
    if (zone) {
      const before = useRoiStore.getState().zones.filter((z) => z.cameraId === zone.cameraId);
      deleteZone(zoneToDeleteId!);
      const ok = await persistCameraZones(zone.cameraId, useRoiStore.getState().zones);
      if (!ok) {
        // Rollback: khôi phục danh sách camera trước khi xóa
        useRoiStore.getState().setZonesFromServer(before, zone.cameraId);
        setZoneToDeleteId(null);
        showToast("Xóa thất bại trên máy chủ — vùng vẫn được giữ lại.", "error");
        return;
      }
    }
    setZoneToDeleteId(null);
    showToast("Đã xóa vùng nguy hiểm thành công", "success");
  };

  const getActiveRulesText = (rules: any) => {
    const list = [];
    if (rules?.enterZone) list.push("Đi vào vùng");
    if (rules?.stayTooLong) list.push(`Đứng lâu >${rules?.stayDurationSeconds || 5}s`);
    if (rules?.approachZone) list.push("Lại gần ranh giới");
    return list.length > 0 ? list.join(", ") : "Không có quy tắc";
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex justify-between items-center gap-4 animate-fade-in">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Vùng nguy hiểm ROI</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            {zones.length > 0
              ? `${zones.length} vùng đang được giám sát trên ${new Set(zones.map(z => z.cameraId)).size} camera.`
              : "Danh sách các khu vực rào chắn AI đang giám sát trẻ em trong ngôi nhà của bạn."}
          </p>
        </div>

        <button
          onClick={() => setShowCameraSelect(true)}
          className="py-2.5 px-4 bg-primary text-white hover:bg-primary/90 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none shrink-0 shadow-sm cursor-pointer active:scale-[0.97]"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          <span className="hidden sm:inline">Tạo vùng mới</span>
        </button>
      </div>

      {/* Stats summary */}
      {zones.length > 0 && (
        <div className="grid grid-cols-3 gap-3 animate-slide-up">
          <div className="bg-surface-container-lowest p-3.5 rounded-xl border border-outline-variant/20 text-center">
            <p className="text-2xl font-bold text-primary">{zones.length}</p>
            <p className="text-[10px] font-semibold text-on-surface-variant mt-0.5">Tổng vùng</p>
          </div>
          <div className="bg-surface-container-lowest p-3.5 rounded-xl border border-outline-variant/20 text-center">
            <p className="text-2xl font-bold text-emerald-600">{zones.filter(z => z.enabled).length}</p>
            <p className="text-[10px] font-semibold text-on-surface-variant mt-0.5">Đang hoạt động</p>
          </div>
          <div className="bg-surface-container-lowest p-3.5 rounded-xl border border-outline-variant/20 text-center">
            <p className="text-2xl font-bold text-amber-600">{zones.filter(z => z.sensitivity === "high").length}</p>
            <p className="text-[10px] font-semibold text-on-surface-variant mt-0.5">Độ nhạy cao</p>
          </div>
        </div>
      )}

      {/* ROI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {zones.map((zone, idx) => (
          <div
            key={zone.id}
            className={`bg-surface-container-lowest p-5 rounded-2xl border transition-all flex flex-col justify-between shadow-sm hover:shadow-md animate-slide-up ${
              zone.enabled ? "border-outline-variant/30" : "border-outline-variant/10 opacity-70"
            }`}
            style={{ animationDelay: `${idx * 60}ms` }}
          >
            <div>
              <div className="flex justify-between items-start mb-3">
                <div className="min-w-0 flex-1">
                  <h3 className="font-bold text-sm md:text-base text-on-surface truncate">{zone.name || `Vùng nguy hiểm ${idx + 1}`}</h3>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${getCameraStatus(zone.cameraId) === "online" ? "bg-emerald-500" : "bg-outline"}`}></span>
                    <p className="text-xs text-on-surface-variant font-medium truncate">{getCameraName(zone.cameraId)}</p>
                  </div>
                </div>

                {/* Enable toggle */}
                <button
                  onClick={() => handleToggleZone(zone.id, zone.enabled)}
                  className={`w-11 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center shrink-0 cursor-pointer ${
                    zone.enabled ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm transition-transform"></span>
                </button>
              </div>

              {/* Specs */}
              <div className="space-y-2.5 py-3 border-t border-b border-outline-variant/10 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-on-surface-variant font-medium">Trạng thái:</span>
                  {(() => {
                    const cam = cameras.find(c => c.id === zone.cameraId);
                    const isOffline = !cam || cam.status === "offline";
                    const isPaused = !zone.enabled;

                    let statusText = "Đang giám sát";
                    let statusColor = "text-emerald-500";
                    let statusIcon = "check_circle";
                    let iconClass = "";

                    if (isOffline) {
                      statusText = "Camera ngoại tuyến";
                      statusColor = "text-error";
                      statusIcon = "videocam_off";
                    } else if (cam?.streamStatus === "failed") {
                      statusText = "Lỗi kết nối video";
                      statusColor = "text-error";
                      statusIcon = "error";
                    } else if (cam?.streamStatus === "idle") {
                      statusText = "Chưa kết nối luồng";
                      statusColor = "text-outline";
                      statusIcon = "pause_circle";
                    } else if (cam?.streamStatus === "connecting" || cam?.streamStatus === "reconnecting") {
                      statusText = "Đang kết nối camera";
                      statusColor = "text-amber-500";
                      statusIcon = "sync";
                      iconClass = "animate-spin";
                    } else if (isPaused) {
                      statusText = "Đang tạm dừng";
                      statusColor = "text-outline";
                      statusIcon = "pause_circle";
                    }

                    return (
                      <span className={`font-semibold flex items-center gap-1.5 ${statusColor}`}>
                        <span className={`material-symbols-outlined text-[16px] ${iconClass}`}>{statusIcon}</span>
                        {statusText}
                      </span>
                    );
                  })()}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-on-surface-variant font-medium">Độ nhạy AI:</span>
                  <StatusBadge type={zone.sensitivity === "high" ? "danger" : zone.sensitivity === "medium" ? "warning" : "info"} label={zone.sensitivity === "high" ? "Cao" : zone.sensitivity === "medium" ? "Trung bình" : "Thấp"} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-on-surface-variant font-medium">Số điểm neo:</span>
                  <span className="font-semibold text-on-surface">{zone.points?.length || 0} điểm</span>
                </div>
                <div className="space-y-1">
                  <span className="text-on-surface-variant font-medium block">Quy tắc:</span>
                  <span className="font-semibold text-on-surface text-[11px] leading-relaxed block pl-2 border-l-2 border-primary/20">
                    {getActiveRulesText(zone.rules)}
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-4 pt-3 flex gap-2">
              <button
                onClick={() => navigate(`/roi/${zone.cameraId}?zoneId=${zone.id}`)}
                className="flex-1 py-2.5 text-xs font-bold bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-xl transition-all text-center focus:outline-none cursor-pointer flex items-center justify-center gap-1.5"
              >
                <span className="material-symbols-outlined text-[16px]">edit</span>
                Chỉnh sửa
              </button>
              <button
                onClick={() => setZoneToDeleteId(zone.id)}
                className="py-2.5 px-3.5 bg-red-500/5 hover:bg-red-500/10 text-error rounded-xl transition-all focus:outline-none flex items-center justify-center cursor-pointer"
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
            <button
              onClick={() => setShowCameraSelect(true)}
              className="py-2.5 px-6 bg-primary text-white font-bold rounded-xl text-xs shadow-sm hover:bg-primary/90 focus:outline-none cursor-pointer active:scale-[0.97] transition-all"
            >
              Tạo vùng nguy hiểm đầu tiên
            </button>
          }
        />
      )}

      {/* Camera Selection Dialog */}
      {showCameraSelect && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-2xl max-w-md w-full p-6 shadow-xl border border-outline-variant/20 animate-scale-up">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-on-surface text-lg">Chọn camera giám sát</h3>
              <button onClick={() => setShowCameraSelect(false)} className="w-8 h-8 rounded-full hover:bg-surface-container-high flex items-center justify-center text-on-surface-variant cursor-pointer">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <p className="text-sm text-on-surface-variant mb-6">Chọn một camera đang hoạt động (Online) để bắt đầu thiết lập vùng nguy hiểm mới.</p>

            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2">
              {cameras.map(cam => (
                <button
                  key={cam.id}
                  onClick={() => {
                    if (cam.status === "online" && cam.streamStatus === "connected") {
                      navigate(`/roi/${cam.id}?mode=new`);
                    }
                  }}
                  className={`w-full text-left p-4 rounded-xl border flex items-center gap-4 transition-all focus:outline-none ${
                    cam.status === "online" && cam.streamStatus === "connected"
                      ? "border-outline-variant/30 hover:border-primary bg-surface-container-lowest hover:bg-primary/5 cursor-pointer"
                      : "border-outline-variant/10 bg-surface-container-low opacity-60 cursor-not-allowed"
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    cam.status === "online" && cam.streamStatus === "connected" ? "bg-primary/10 text-primary" : "bg-outline/10 text-outline"
                  }`}>
                    <span className="material-symbols-outlined">{cam.status === "online" && cam.streamStatus === "connected" ? "videocam" : "videocam_off"}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-on-surface text-sm truncate">{cam.name}</h4>
                    <p className="text-xs text-on-surface-variant truncate mt-0.5">{cam.location}</p>
                  </div>
                  <div className="shrink-0">
                    {cam.status === "online" && cam.streamStatus === "connected" ? (
                      <span className="px-2.5 py-1 bg-emerald-500/10 text-emerald-600 font-bold text-[10px] rounded-lg">Khả dụng</span>
                    ) : (
                      <span className="px-2.5 py-1 bg-outline/10 text-outline font-bold text-[10px] rounded-lg">Không khả dụng</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
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
                className="flex-1 py-2.5 rounded-xl bg-surface-container-high text-xs font-bold text-on-surface hover:bg-surface-container-highest cursor-pointer"
              >
                Hủy bỏ
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 py-2.5 rounded-xl bg-error text-white text-xs font-bold hover:bg-error/90 cursor-pointer"
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
