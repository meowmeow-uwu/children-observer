import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { StatusBadge } from "../components/StatusBadge";
import { ErrorState } from "../components/ErrorState";

export const CameraListView: React.FC = () => {
  const navigate = useNavigate();
  const { cameras } = useCameraStore();
  const [filter, setFilter] = useState<"all" | "online" | "offline" | "failed">("all");

  // Filter cameras
  const filteredCameras = cameras.filter((cam) => {
    if (filter === "all") return true;
    if (filter === "online") return cam.status === "online";
    if (filter === "offline") return cam.status === "offline";
    if (filter === "failed") return cam.streamStatus === "failed";
    return true;
  });

  const getSignalIcon = (quality: "good" | "fair" | "poor") => {
    switch (quality) {
      case "good":
        return "signal_cellular_4_bar";
      case "fair":
        return "signal_cellular_3_bar";
      case "poor":
      default:
        return "signal_cellular_1_bar";
    }
  };

  const getSignalColor = (quality: "good" | "fair" | "poor") => {
    switch (quality) {
      case "good": return "text-emerald-500";
      case "fair": return "text-amber-500";
      case "poor":
      default:
        return "text-error";
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Camera giám sát trực tiếp</h2>
          <p className="text-sm text-on-surface-variant mt-1">Theo dõi các luồng video và trạng thái kết nối thời gian thực.</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex border-b border-outline-variant/30 gap-6 overflow-x-auto pb-0.5">
        {(["all", "online", "offline", "failed"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
              filter === tab
                ? "border-primary text-primary"
                : "border-transparent text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {tab === "all" && `Tất cả (${cameras.length})`}
            {tab === "online" && `Đang hoạt động (${cameras.filter(c => c.status === "online").length})`}
            {tab === "offline" && `Mất kết nối (${cameras.filter(c => c.status === "offline").length})`}
            {tab === "failed" && `Lỗi kết nối (${cameras.filter(c => c.streamStatus === "failed").length})`}
          </button>
        ))}
      </div>

      {/* Camera Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredCameras.map((cam) => {
          const activeRois = cam.roiZones.filter((z) => z.enabled).length;

          return (
            <div
              key={cam.id}
              className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm flex flex-col group hover:shadow-md transition-all"
            >
              {/* Camera Preview Area */}
              <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
                {cam.status === "offline" ? (
                  <div className="text-center p-6 w-full h-full bg-stone-900/50 flex flex-col items-center justify-center">
                    <span className="material-symbols-outlined text-error text-[48px] mb-2">videocam_off</span>
                    <h4 className="text-sm font-bold text-outline">Camera Ngoại Tuyến</h4>
                    <p className="text-xs text-outline-variant mt-1">Vui lòng kiểm tra cáp nguồn thiết bị</p>
                  </div>
                ) : cam.streamStatus === "failed" ? (
                  <div className="w-full h-full bg-error-container/10 flex items-center justify-center p-4 text-center">
                    <ErrorState
                      message="Không thể kết nối camera. Vui lòng kiểm tra mạng hoặc thiết bị."
                    />
                  </div>
                ) : cam.streamStatus === "connected" ? (
                  <div className="w-full h-full relative">
                    <img
                      src="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=600&auto=format&fit=crop"
                      alt={cam.name}
                      className="w-full h-full object-cover opacity-80"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/55 to-transparent"></div>
                    <span className="absolute top-3 left-3 px-2 py-0.5 bg-red-600 text-white rounded text-[10px] font-bold tracking-wider animate-pulse uppercase z-10">Live</span>
                  </div>
                ) : cam.streamStatus === "connecting" ? (
                  <div className="text-center p-6">
                    <div className="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                    <h4 className="text-sm font-bold text-outline">Đang kết nối WebRTC...</h4>
                    <p className="text-xs text-outline-variant mt-1">Đang đàm phán tín hiệu bảo mật</p>
                  </div>
                ) : (
                  <div className="text-center p-6 text-outline">
                    <span className="material-symbols-outlined text-[48px] mb-2">pause_circle</span>
                    <h4 className="text-sm font-bold">Chưa khởi tạo kết nối</h4>
                    <p className="text-xs text-outline-variant mt-1">Nhấp xem chi tiết để kết nối luồng trực tiếp</p>
                  </div>
                )}

                {/* Overlays */}
                <div className="absolute top-3 right-3 flex flex-col gap-1.5 items-end z-10">
                  <StatusBadge type={cam.status} label={cam.status === "online" ? "Online" : "Offline"} />
                  <StatusBadge type={cam.streamStatus} />
                </div>
              </div>

              {/* Card Meta Content */}
              <div className="p-5 flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <h3 className="font-bold text-on-surface text-base group-hover:text-secondary transition-colors">
                        {cam.name}
                      </h3>
                      <p className="text-xs text-on-surface-variant mt-0.5">{cam.location}</p>
                    </div>

                    <div className="flex items-center gap-1 text-on-surface-variant font-semibold text-xs shrink-0 bg-surface-container-low px-2 py-1 rounded-lg">
                      <span className={`material-symbols-outlined text-[16px] ${getSignalColor(cam.signalQuality)}`}>
                        {getSignalIcon(cam.signalQuality)}
                      </span>
                      {cam.signalQuality === "good" ? "Tốt" : cam.signalQuality === "fair" ? "Ổn định" : "Yếu"}
                    </div>
                  </div>

                  <div className="mt-4 flex gap-4 text-xs font-semibold text-on-surface-variant">
                    <span className="flex items-center gap-1 bg-surface-container-low px-2.5 py-1 rounded-lg">
                      <span className="material-symbols-outlined text-[15px] text-primary">detector_status</span>
                      {activeRois} vùng nguy hiểm
                    </span>
                    <span className="flex items-center gap-1 bg-surface-container-low px-2.5 py-1 rounded-lg">
                      <span className="material-symbols-outlined text-[15px] text-primary">settings_system_daydream</span>
                      {cam.resolution} • {cam.fps} FPS
                    </span>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-outline-variant/30 grid grid-cols-2 gap-3">
                  <button
                    onClick={() => navigate(`/cameras/${cam.id}`)}
                    className="py-2.5 px-4 text-xs font-bold bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-xl transition-all text-center focus:outline-none"
                  >
                    Xem chi tiết
                  </button>
                  <button
                    onClick={() => navigate(`/roi/${cam.id}`)}
                    className="py-2.5 px-4 text-xs font-bold bg-primary hover:bg-primary/95 text-white rounded-xl transition-all text-center focus:outline-none shadow-sm"
                  >
                    Thiết lập ROI
                  </button>
                </div>
              </div>

            </div>
          );
        })}
      </div>

      {filteredCameras.length === 0 && (
        <div className="py-12 bg-surface-container-lowest border border-outline-variant/30 rounded-2xl text-center max-w-sm mx-auto">
          <span className="material-symbols-outlined text-[48px] text-outline mb-2">videocam_off</span>
          <h3 className="font-bold text-on-surface">Không tìm thấy camera</h3>
          <p className="text-xs text-on-surface-variant mt-1">Không có thiết bị phù hợp với bộ lọc hiện tại.</p>
        </div>
      )}
    </div>
  );
};
export default CameraListView;
