import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { useAlertStore } from "../store/alertStore";
import { useRoiStore } from "../store/roiStore";
import { StatusBadge } from "../components/StatusBadge";
import { ErrorState } from "../components/ErrorState";
import { useToast } from "../components/Toast";
import { useCameraStream } from "../hooks/useCameraStream";

export const CameraDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const { cameras } = useCameraStore();
  const { alerts } = useAlertStore();
  const { zones, setEnabled } = useRoiStore();

  const cam = cameras.find((c) => c.id === id);
  const cameraZones = zones.filter((z) => z.cameraId === id);
  const [isAlertsPaused, setIsAlertsPaused] = useState(false);

  const {
    videoRef,
    streamStatus,
    errorMessage,
    startStream,
    stopStream,
    retryStream,
    isStreaming
  } = useCameraStream(id || "");

  // Tự động kết nối/duy trì luồng video khi mở hoặc quay lại trang chi tiết Camera
  React.useEffect(() => {
    if (cam && cam.status === "online") {
      startStream();
    }
    // eslint-disable-next-deps
  }, [id, cam?.status]);

  if (!cam) {
    return (
      <div className="p-6">
        <ErrorState message={`Không tìm thấy camera với ID: ${id}`} onRetry={() => navigate("/cameras")} />
      </div>
    );
  }

  // Filter alerts for this camera
  const cameraAlerts = alerts.filter((a) => a.cameraId === cam.id);
  const lastCameraAlert = cameraAlerts.length > 0 ? cameraAlerts[0] : null;

  const handleToggleZone = (zoneId: string) => {
    const zone = zones.find((z) => z.id === zoneId);
    if (zone) {
      setEnabled(zoneId, !zone.enabled);
      showToast(
        `Đã ${!zone.enabled ? "bật" : "tắt"} vùng nguy hiểm "${zone.name}"`,
        "info"
      );
    }
  };

  const handlePauseAlerts = () => {
    setIsAlertsPaused(!isAlertsPaused);
    showToast(
      isAlertsPaused ? "Hệ thống cảnh báo đã hoạt động trở lại" : "Đã tạm dừng cảnh báo từ camera này",
      isAlertsPaused ? "success" : "warning"
    );
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Back link & title */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/cameras")}
          className="w-10 h-10 rounded-full bg-surface-container-low hover:bg-surface-container-high transition-all flex items-center justify-center text-on-surface"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
        </button>
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface flex items-center gap-2">
            {cam.name}
            <StatusBadge type={cam.status} label={cam.status === "online" ? "Online" : "Offline"} />
          </h2>
          <p className="text-xs md:text-sm text-on-surface-variant mt-0.5">{cam.location}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Big Stream Player */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-black aspect-video rounded-2xl overflow-hidden border border-outline-variant/30 relative flex items-center justify-center shadow-md">
            
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-contain absolute inset-0 z-0 ${streamStatus === "connected" ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            />

            {cam.status === "offline" ? (
              <div className="text-center p-6 text-outline">
                <span className="material-symbols-outlined text-[56px] text-error mb-2">videocam_off</span>
                <h3 className="font-bold text-lg">Mất tín hiệu camera</h3>
                <p className="text-sm mt-1">Không thể tải luồng video trực tiếp từ thiết bị này.</p>
              </div>
            ) : streamStatus === "failed" ? (
              <div className="w-full h-full bg-error-container/15 flex items-center justify-center p-6 text-center">
                <ErrorState
                  message={errorMessage || "Không thể kết nối camera. Vui lòng kiểm tra thiết bị hoặc kết nối mạng."}
                  onRetry={retryStream}
                />
              </div>
            ) : streamStatus === "connecting" ? (
              <div className="text-center p-6">
                <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <h3 className="font-bold text-lg text-outline">Đang kết nối WebRTC...</h3>
                <p className="text-sm text-outline-variant mt-1">Thiết lập kết nối trực tiếp đầu-cuối an toàn</p>
              </div>
            ) : streamStatus === "reconnecting" ? (
              <div className="text-center p-6 relative z-30">
                <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <h3 className="font-bold text-lg text-outline">Đang kết nối lại...</h3>
                <p className="text-sm text-outline-variant mt-1">Thử kết nối lại tự động (1s, 2s, 4s)</p>
              </div>
            ) : streamStatus === "idle" ? (
              <div className="w-full h-full relative">
                <img
                  src="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1200&auto=format&fit=crop"
                  alt={cam.name}
                  className="w-full h-full object-cover opacity-60"
                />
                <div className="absolute inset-0 bg-black/45 flex flex-col items-center justify-center gap-4 z-20">
                  <button
                    onClick={startStream}
                    className="w-16 h-16 rounded-full bg-primary hover:bg-primary/90 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-105 active:scale-95 focus:outline-none"
                    title="Bắt đầu xem trực tiếp"
                  >
                    <span className="material-symbols-outlined text-[36px] fill ml-1">play_arrow</span>
                  </button>
                  <span className="text-sm text-white font-bold tracking-wide">Nhấp để kết nối truyền phát camera</span>
                </div>
              </div>
            ) : (
              // Active stream (connected)
              <div className="w-full h-full relative">
                {/* SVG ROI overlay scaled to 100x100 viewBox */}
                <svg
                  className="absolute inset-0 w-full h-full z-10 pointer-events-none"
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                >
                  {cameraZones
                    .filter((zone) => zone.enabled)
                    .map((zone) => {
                      const pointsStr = zone.points
                        .map((p) => `${p.x * 100},${p.y * 100}`)
                        .join(" ");
                      
                      return (
                        <g key={zone.id}>
                          {/* Thin, elegant ROI zone polygon */}
                          <polygon
                            points={pointsStr}
                            className="fill-error/15 stroke-error stroke-[0.4]"
                          />
                        </g>
                      );
                    })}
                </svg>

                {/* Video element is now rendered absolutely at the top level to preserve ref */}

                <div className="absolute top-4 left-4 z-20 flex gap-2">
                  <span className="px-2.5 py-1 bg-red-600 text-white rounded-md text-xs font-bold tracking-wider animate-pulse uppercase">LIVE</span>
                  {isAlertsPaused && (
                    <span className="px-2.5 py-1 bg-amber-600 text-white rounded-md text-xs font-bold flex items-center gap-1">
                      <span className="material-symbols-outlined text-[14px]">pause_circle</span>
                      Cảnh báo tạm dừng
                    </span>
                  )}
                </div>

                <div className="absolute bottom-4 left-4 z-20 text-white drop-shadow bg-black/40 px-3 py-1.5 rounded-lg text-xs font-semibold">
                  {cam.resolution} • {cam.fps} FPS
                </div>
              </div>
            )}
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => navigate(`/roi/${cam.id}`)}
              className="py-3 px-5 text-sm font-bold bg-primary text-white hover:bg-primary/95 rounded-xl transition-all flex items-center gap-2 shadow-sm focus:outline-none"
            >
              <span className="material-symbols-outlined text-[20px]">detector_status</span>
              Thiết lập vùng nguy hiểm (ROI)
            </button>
            
            <button
              onClick={handlePauseAlerts}
              className={`py-3 px-5 text-sm font-bold rounded-xl transition-all flex items-center gap-2 border focus:outline-none ${
                isAlertsPaused
                  ? "bg-amber-500/10 text-amber-700 border-amber-500/20 hover:bg-amber-500/20"
                  : "bg-surface-container-high text-on-surface hover:bg-surface-container-highest border-outline-variant/30"
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">
                {isAlertsPaused ? "play_circle" : "pause_circle"}
              </span>
              {isAlertsPaused ? "Kích hoạt lại cảnh báo" : "Tạm dừng cảnh báo"}
            </button>

            {isStreaming && (
              <button
                onClick={stopStream}
                className="py-3 px-5 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-xl transition-all flex items-center gap-2 shadow-sm focus:outline-none"
              >
                <span className="material-symbols-outlined text-[20px]">videocam_off</span>
                Ngắt xem trực tiếp
              </button>
            )}
          </div>
        </div>

        {/* Right Column: Information & Management */}
        <div className="space-y-6">
          
          {/* Stream Status info */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 space-y-4 shadow-sm">
            <h3 className="font-bold text-on-surface text-base">Thông số kết nối</h3>
            
            <div className="space-y-3.5">
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Trạng thái luồng:</span>
                <StatusBadge type={streamStatus} />
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Chất lượng mạng:</span>
                <span className="font-semibold text-on-surface flex items-center gap-1">
                  <span className="material-symbols-outlined text-emerald-500 text-[18px]">
                    {cam.signalQuality === "good" ? "signal_cellular_4_bar" : cam.signalQuality === "fair" ? "signal_cellular_3_bar" : "signal_cellular_1_bar"}
                  </span>
                  {cam.signalQuality === "good" ? "Tốt (94ms)" : cam.signalQuality === "fair" ? "Trung bình" : "Yếu"}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Cảnh báo gần nhất:</span>
                <span className="font-semibold text-on-surface text-right">
                  {lastCameraAlert ? new Date(lastCameraAlert.createdAt).toLocaleTimeString("vi-VN") : "Chưa ghi nhận"}
                </span>
              </div>
            </div>
          </div>

          {/* Active ROI list in Right Panel */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 space-y-4 shadow-sm">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-on-surface text-base">Vùng đang giám sát</h3>
              <span className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-bold rounded-full">
                {cameraZones.length} vùng
              </span>
            </div>

            <div className="flex flex-col gap-3">
              {cameraZones.map((zone) => (
                <div key={zone.id} className="flex justify-between items-center p-3 bg-surface-container-low rounded-xl">
                  <div>
                    <h4 className="font-bold text-xs text-on-surface">{zone.name}</h4>
                    <p className="text-[10px] text-on-surface-variant mt-0.5 capitalize">Độ nhạy: {zone.sensitivity === "high" ? "Cao" : zone.sensitivity === "medium" ? "Trung bình" : "Thấp"}</p>
                  </div>
                  
                  <button
                    onClick={() => handleToggleZone(zone.id)}
                    className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                      zone.enabled ? "bg-emerald-500 justify-end" : "bg-outline-variant justify-start"
                    }`}
                  >
                    <span className="w-5 h-5 rounded-full bg-white shadow-sm transition-transform"></span>
                  </button>
                </div>
              ))}

              {cameraZones.length === 0 && (
                <div className="text-center p-4 text-xs text-outline">
                  Chưa có vùng ROI nào được thiết lập.
                </div>
              )}
            </div>
          </div>

          {/* Last alerts log for this camera */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 space-y-4 shadow-sm">
            <h3 className="font-bold text-on-surface text-base">Lịch sử cảnh báo gần đây</h3>
            
            <div className="flex flex-col gap-3">
              {cameraAlerts.slice(0, 3).map((al) => (
                <div
                  key={al.id}
                  onClick={() => navigate(`/alerts/${al.id}`)}
                  className="p-3 bg-surface-container-low hover:bg-surface-container-high rounded-xl cursor-pointer transition-colors flex justify-between items-center gap-3 text-xs"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-on-surface truncate">{al.title}</p>
                    <p className="text-[10px] text-on-surface-variant mt-0.5">
                      {new Date(al.createdAt).toLocaleTimeString("vi-VN")} • {al.roiName}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase shrink-0 ${al.severity === "danger" ? "bg-red-500/10 text-error" : al.severity === "warning" ? "bg-amber-500/10 text-amber-700" : "bg-blue-50/10 text-secondary"}`}>
                    {al.severity === "danger" ? "Nguy cấp" : al.severity === "warning" ? "Cảnh báo" : "Tin"}
                  </span>
                </div>
              ))}

              {cameraAlerts.length === 0 && (
                <div className="text-center p-4 text-xs text-outline">
                  Chưa có cảnh báo nào từ camera này.
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
export default CameraDetailView;
