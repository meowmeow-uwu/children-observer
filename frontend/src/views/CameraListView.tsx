import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { StatusBadge } from "../components/StatusBadge";

export const CameraListView: React.FC = () => {
  const navigate = useNavigate();
  const { cameras } = useCameraStore();
  const [filter, setFilter] = useState<"all" | "online" | "offline" | "failed">("all");

  // Filter bằng status thật từ backend (không dùng demoCameraState)
  const filteredCameras = cameras.filter((cam) => {
    if (filter === "all") return true;
    if (filter === "online") return cam.status === "online";
    if (filter === "offline") return cam.status === "offline";
    if (filter === "failed") return cam.streamStatus === "failed";
    return true;
  });

  const countByStatus = (s: typeof filter) =>
    s === "all"
      ? cameras.length
      : cameras.filter((c) => c.status === s).length;

  const getSignalIcon = (quality: "good" | "fair" | "poor") => {
    switch (quality) {
      case "good": return "signal_cellular_4_bar";
      case "fair": return "signal_cellular_3_bar";
      case "poor":
      default: return "signal_cellular_1_bar";
    }
  };

  const getSignalColor = (quality: "good" | "fair" | "poor") => {
    switch (quality) {
      case "good": return "text-emerald-500";
      case "fair": return "text-amber-500";
      case "poor":
      default: return "text-error";
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-on-surface">Camera giám sát trực tiếp</h1>
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
            {tab === "all" && `Tất cả (${countByStatus("all")})`}
            {tab === "online" && `Đang hoạt động (${countByStatus("online")})`}
            {tab === "offline" && `Mất kết nối (${countByStatus("offline")})`}
            {tab === "failed" && `Lỗi kết nối (${countByStatus("failed")})`}
          </button>
        ))}
      </div>

      {/* Camera Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredCameras.map((cam) => {
          const activeRois = cam.roiZones.filter((z) => z.enabled).length;
          const isOnline = cam.status === "online";

          return (
            <div
              key={cam.id}
              className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm flex flex-col group hover:shadow-md transition-all"
            >
              {/* Camera Preview Area */}
              <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
                {cam.status === "offline" || cam.streamStatus === "failed" ? (
                  <div className="text-center p-6 w-full h-full bg-error-container/10 flex flex-col items-center justify-center">
                    <span className="material-symbols-outlined text-error text-[48px] mb-2">
                      {cam.status === "offline" ? "videocam_off" : "signal_disconnected"}
                    </span>
                    <h4 className="text-sm font-bold text-error">
                      {cam.status === "offline" ? "Camera Ngoại Tuyến" : "Lỗi kết nối camera"}
                    </h4>
                    <p className="text-xs text-outline-variant mt-1">Vui lòng kiểm tra mạng hoặc thiết bị</p>
                  </div>
                ) : cam.streamStatus === "connected" ? (
                  <div className="w-full h-full relative">
                    <img
                      src="/test_video_thumb.jpg"
                      alt={cam.name}
                      className="w-full h-full object-cover opacity-80"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/55 to-transparent"></div>
                  </div>
                ) : cam.streamStatus === "connecting" ? (
                  <div className="text-center p-6">
                    <div className="w-10 h-10 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                    <h4 className="text-sm font-bold text-outline">Đang kết nối WebRTC...</h4>
                    <p className="text-xs text-outline-variant mt-1">Đang đàm phán tín hiệu bảo mật</p>
                  </div>
                ) : (
                  <div className="text-center p-6 w-full h-full flex flex-col items-center justify-center">
                    <span className="material-symbols-outlined text-outline text-[48px] mb-2">videocam</span>
                    <h4 className="text-sm font-bold text-outline">Sẵn sàng</h4>
                    <p className="text-xs text-outline-variant mt-1">Nhấn "Xem chi tiết" để bắt đầu xem</p>
                  </div>
                )}

                {/* Overlays */}
                <div className="absolute top-3 right-3 flex flex-col gap-1.5 items-end z-10">
                  <StatusBadge
                    type={cam.streamStatus === "connected" ? "connected" : cam.status === "online" && cam.streamStatus !== "failed" ? "online" : cam.streamStatus === "failed" ? "failed" : "offline"}
                    label={cam.streamStatus === "connected" ? "Đang xem Live" : cam.status === "online" && cam.streamStatus !== "failed" ? "Sẵn sàng" : undefined}
                  />
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
                    disabled={!isOnline}
                    className={`py-2.5 px-4 text-xs font-bold rounded-xl transition-all text-center focus:outline-none ${
                      isOnline
                        ? "bg-primary hover:bg-primary/95 text-white shadow-sm"
                        : "bg-outline-variant/30 text-on-surface-variant cursor-not-allowed opacity-70"
                    }`}
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
