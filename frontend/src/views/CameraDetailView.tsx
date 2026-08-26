import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { useAlertStore } from "../store/alertStore";
import { useRoiStore } from "../store/roiStore";
import { StatusBadge } from "../components/StatusBadge";
import { ErrorState } from "../components/ErrorState";
import { useToast } from "../components/Toast";
import { VideoStage } from "../components/VideoStage";
import { DetectionOverlay } from "../components/DetectionOverlay";
import { useTrackSync } from "../hooks/useTrackSync";
import { setCameraAlertsPausedApi, saveCameraRoiApi } from "../services/api";

export const CameraDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const { cameras, updateCameraAlertsPaused } = useCameraStore();
  const { alerts } = useAlertStore();
  const { zones, setEnabled } = useRoiStore();

  const cam = cameras.find((c) => c.id === id);
  const cameraZones = zones.filter((z) => z.cameraId === id);
  const [isPausing, setIsPausing] = useState(false);

  // Ref ổn định để useTrackSync gắn rVFC vào video element của VideoStage
  const stageVideoRef = React.useRef<HTMLVideoElement | null>(null);
  const [stageVideoElement, setStageVideoElement] = React.useState<HTMLVideoElement | null>(null);
  const { tracks, poses, aiState, latencyMs } = useTrackSync(stageVideoRef, id || "", stageVideoElement);

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

  const handleToggleZone = async (zoneId: string) => {
    const zone = zones.find((z) => z.id === zoneId);
    if (!zone) return;
    const previousEnabled = zone.enabled;
    setEnabled(zoneId, !previousEnabled);
    showToast(
      `Đã ${!previousEnabled ? "bật" : "tắt"} vùng nguy hiểm "${zone.name}"`,
      "info"
    );

    // Đồng bộ lên backend (replace-whole-list cho camera); rollback khi thất bại
    const nextZones = useRoiStore.getState().zones;
    const cameraZones = nextZones.filter((z) => z.cameraId === zone.cameraId);
    try {
      const serverZones = await saveCameraRoiApi(zone.cameraId, cameraZones);
      useRoiStore.getState().setZonesFromServer(serverZones, zone.cameraId);
    } catch (err) {
      console.error("Đồng bộ ROI thất bại:", err);
      // Rollback: UI và DB không được âm thầm khác nhau
      useRoiStore.getState().setEnabled(zoneId, previousEnabled);
      showToast("Đồng bộ lên máy chủ thất bại — đã khôi phục trạng thái cũ.", "error");
    }
  };

  const handlePauseAlerts = async () => {
    if (isPausing) return;
    setIsPausing(true);
    const nextPaused = !cam.alertsPaused;
    try {
      const updated = await setCameraAlertsPausedApi(cam.id, nextPaused);
      updateCameraAlertsPaused(cam.id, updated?.alertsPaused ?? nextPaused);
      showToast(
        nextPaused ? "Đã tạm dừng cảnh báo từ camera này" : "Hệ thống cảnh báo đã hoạt động trở lại",
        nextPaused ? "warning" : "success"
      );
    } catch (err) {
      console.error("Pause alerts failed:", err);
      showToast("Không thể cập nhật trạng thái cảnh báo — kiểm tra kết nối backend.", "error");
    } finally {
      setIsPausing(false);
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Back link & title */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/cameras")}
          className="w-10 h-10 rounded-full bg-surface-container-low hover:bg-surface-container-high transition-all flex items-center justify-center text-on-surface cursor-pointer active:scale-95 focus:outline-none"
          aria-label="Quay lại danh sách camera"
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
            <VideoStage
              cameraId={cam.id}
              autoStart
              onVideoElement={(el) => setStageVideoElement(el)}
            >
              {({ videoRef: stageVideo, streamStatus }) => {
                stageVideoRef.current = stageVideo.current;
                const isConnected = streamStatus === "connected" && cam.status === "online";
                const aiTracks = isConnected ? tracks : [];
                const aiPoses = isConnected ? poses : [];
                return (
                  <>
                    {/* ROI overlay — map lên vùng video thật (không letterbox) */}
                    <svg
                      className="absolute inset-0 w-full h-full z-10 pointer-events-none"
                      viewBox="0 0 1000 1000"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                    >
                      {cameraZones
                        .filter((zone) => zone.enabled)
                        .map((zone) => {
                          const pointsStr = zone.points
                            .map((p) => `${p.x * 1000},${p.y * 1000}`)
                            .join(" ");

                          return (
                            <g key={zone.id}>
                              <polygon
                                points={pointsStr}
                                fill="rgba(234, 179, 8, 0.08)"
                                stroke="#eab308"
                                strokeWidth="2"
                                strokeLinejoin="round"
                                strokeDasharray="8 4"
                              />
                              {zone.name && (
                                <text
                                  x={zone.points[0]?.x ? zone.points[0].x * 1000 : 0}
                                  y={(zone.points[0]?.y || 0) * 1000 - 8}
                                  fontSize="13"
                                  fontWeight="700"
                                  fill="#eab308"
                                  fontFamily="Be Vietnam Pro, Inter, sans-serif"
                                >
                                  {zone.name}
                                </text>
                              )}
                            </g>
                          );
                        })}
                    </svg>

                    {/* AI Detection Bounding Boxes Overlay */}
                    <DetectionOverlay
                      tracks={aiTracks}
                      poses={aiPoses}
                      aiState={isConnected ? aiState : "offline"}
                      latencyMs={latencyMs}
                    />
                  </>
                );
              }}
            </VideoStage>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => navigate(`/roi/${cam.id}`)}
              disabled={cam.status !== "online"}
              className={`py-3 px-5 text-sm font-bold rounded-xl transition-all flex items-center gap-2 shadow-sm focus:outline-none ${
                cam.status === "online"
                  ? "bg-primary text-white hover:bg-primary/90 cursor-pointer active:scale-[0.97]"
                  : "bg-outline-variant/30 text-on-surface-variant cursor-not-allowed opacity-70"
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">detector_status</span>
              Thiết lập vùng nguy hiểm (ROI)
            </button>

            <button
              onClick={handlePauseAlerts}
              disabled={isPausing}
              className={`py-3 px-5 text-sm font-bold rounded-xl transition-all flex items-center gap-2 border focus:outline-none ${
                cam.alertsPaused
                  ? "bg-amber-500/10 text-amber-700 border-amber-500/20 hover:bg-amber-500/20"
                  : "bg-surface-container-high text-on-surface hover:bg-surface-container-highest border-outline-variant/30"
              } disabled:opacity-60`}
            >
              <span className="material-symbols-outlined text-[20px]">
                {cam.alertsPaused ? "play_circle" : "pause_circle"}
              </span>
              {cam.alertsPaused ? "Kích hoạt lại cảnh báo" : "Tạm dừng cảnh báo"}
            </button>
          </div>
        </div>

        {/* Right Column: Information & Management */}
        <div className="space-y-6">

          {/* Stream Status info */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 space-y-4 shadow-sm">
            <h3 className="font-bold text-on-surface text-base">Thông số kết nối</h3>

            <div className="space-y-3.5">
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Trạng thái cảnh báo:</span>
                <span className={`font-semibold flex items-center gap-1 ${cam.alertsPaused ? "text-amber-600" : "text-emerald-600"}`}>
                  <span className="material-symbols-outlined text-[18px]">
                    {cam.alertsPaused ? "pause_circle" : "notifications_active"}
                  </span>
                  {cam.status === "offline"
                    ? "Chờ camera kết nối lại"
                    : cam.alertsPaused
                    ? "Đã tạm dừng"
                    : "Đang hoạt động"}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Chất lượng mạng:</span>
                <span className="font-semibold text-on-surface flex items-center gap-1">
                  <span className="material-symbols-outlined text-emerald-500 text-[18px]">
                    {cam.signalQuality === "good" ? "signal_cellular_4_bar" : cam.signalQuality === "fair" ? "signal_cellular_3_bar" : "signal_cellular_1_bar"}
                  </span>
                  {cam.status === "online" ? "Đã kết nối" : "Mất tín hiệu"}
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
                    className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center cursor-pointer ${
                      zone.enabled ? "bg-emerald-500 justify-end" : "bg-outline-variant justify-start"
                    }`}
                    role="switch"
                    aria-checked={zone.enabled}
                    aria-label={`Bật/tắt vùng ${zone.name}`}
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
