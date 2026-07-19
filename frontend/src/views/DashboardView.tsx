import React from "react";
import { useNavigate } from "react-router-dom";
import { useCameraStore } from "../store/cameraStore";
import { useAlertStore } from "../store/alertStore";
import { useSystemStatusStore } from "../store/systemStatusStore";
import { StatusBadge } from "../components/StatusBadge";
import { SecureImage } from "../components/SecureImage";
import { useToast } from "../components/Toast";

export const DashboardView: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const { cameras } = useCameraStore();
  const { alerts, updateAlertStatus } = useAlertStore();
  const { deviceInfo } = useSystemStatusStore();

  // Computations
  const totalCameras = cameras.length;
  const onlineCameras = cameras.filter((c) => c.status === "online").length;
  const offlineCameras = cameras.filter((c) => c.status === "offline" || c.status === "loading").length;
  
  // Count ROI active
  const totalRoiActive = cameras.reduce((acc, cam) => acc + cam.roiZones.filter(r => r.enabled).length, 0);
  
  // Count alerts today
  const alertsToday = alerts.filter(a => {
    const alertDate = new Date(a.createdAt);
    const today = new Date();
    return alertDate.toDateString() === today.toDateString();
  }).length;

  // Last alert details
  const lastAlert = alerts.length > 0 ? alerts[0] : null;

  // Format relative time helper
  const getRelativeTime = (isoString: string) => {
    const date = new Date(isoString);
    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return "Vừa xong";
    if (diffMins < 60) return `${diffMins} phút trước`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} giờ trước`;
    
    return date.toLocaleDateString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  };

  const handleResolve = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation(); // Prevent card navigation click
    updateAlertStatus(alertId, "resolved", {
      resolvedAt: new Date().toISOString(),
      resolvedBy: "Nguyễn Văn A",
      notes: "Đã xử lý từ Dashboard"
    });
    showToast("Cảnh báo đã được đánh dấu đã xử lý!", "success");
  };

  const handleFalseAlarm = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation();
    updateAlertStatus(alertId, "false_alarm", {
      checkedBy: "Nguyễn Văn A",
      falseAlarmReason: "Báo nhầm từ Dashboard"
    });
    showToast("Đã ghi nhận báo cáo báo nhầm cho cảnh báo này", "info");
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      
      {/* Bento Grid Header / Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        
        {/* System Health Card */}
        <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 flex items-start gap-4 shadow-sm hover:shadow-md transition-shadow">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${offlineCameras > 0 ? 'bg-amber-50 text-amber-500' : 'bg-emerald-50 text-emerald-500'}`}>
            <span className="material-symbols-outlined text-[28px] fill">
              {offlineCameras > 0 ? 'warning' : 'check_circle'}
            </span>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-on-surface-variant">Trạng thái hệ thống</h4>
            <p className="font-bold text-sm text-on-surface mt-1 leading-tight">
              {offlineCameras > 0 
                ? `Phát hiện ${offlineCameras} thiết bị gián đoạn` 
                : "Hoạt động bình thường"
              }
            </p>
            <span className="text-[10px] text-on-surface-variant block mt-0.5">
              {offlineCameras > 0 ? "Vui lòng kiểm tra thiết bị cầu thang" : "Tất cả camera đều online"}
            </span>
          </div>
        </div>

        {/* Devices Count Card */}
        <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 flex items-start gap-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-secondary flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[28px]">router</span>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-on-surface-variant">Thiết bị hoạt động</h4>
            <p className="font-bold text-headline-sm text-on-surface mt-0.5">
              {onlineCameras}/{totalCameras}
            </p>
            <span className="text-[10px] text-on-surface-variant block">
              IP Hub: {deviceInfo?.ipAddress || "192.168.1.15"}
            </span>
          </div>
        </div>

        {/* Alerts count Card */}
        <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 flex items-start gap-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="w-12 h-12 rounded-xl bg-red-50 text-error flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[28px]">notifications_active</span>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-on-surface-variant">Cảnh báo hôm nay</h4>
            <p className="font-bold text-headline-sm text-on-surface mt-0.5">{alertsToday}</p>
            <span className="text-[10px] text-error font-semibold block">
              {alerts.filter(a => a.status === "unread").length} cảnh báo chưa xem
            </span>
          </div>
        </div>

        {/* Active ROI Card */}
        <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 flex items-start gap-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="w-12 h-12 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[28px]">detector_status</span>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-on-surface-variant">Vùng đang bật ROI</h4>
            <p className="font-bold text-headline-sm text-on-surface mt-0.5">{totalRoiActive}</p>
            <span className="text-[10px] text-on-surface-variant block">Giám sát nguy hiểm AI</span>
          </div>
        </div>

        {/* Last Warning Card */}
        <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 flex items-start gap-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-500 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[28px]">warning</span>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-on-surface-variant">Cảnh báo gần nhất</h4>
            <p className="font-bold text-xs text-on-surface mt-1 leading-tight truncate max-w-[120px]">
              {lastAlert ? lastAlert.cameraName : "Không có"}
            </p>
            <span className="text-[10px] text-on-surface-variant block mt-0.5 truncate max-w-[120px]">
              {lastAlert ? getRelativeTime(lastAlert.createdAt) : "Chưa có dữ liệu"}
            </span>
          </div>
        </div>

      </div>

      {/* Main Grid: Cameras & Alerts Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Camera Preview Cards */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-on-surface">Camera trực tiếp</h3>
            <button 
              onClick={() => navigate("/cameras")} 
              className="text-xs font-bold text-secondary hover:underline flex items-center gap-1"
            >
              Xem tất cả <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {cameras.map((cam) => {
              const activeRois = cam.roiZones.filter((z) => z.enabled).length;
              return (
                <div key={cam.id} className="bg-surface-container-lowest rounded-2xl border border-outline-variant/30 overflow-hidden shadow-sm flex flex-col group hover:shadow-md transition-all">
                  
                  {/* Mock Video Placeholder */}
                  <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
                    {cam.status === "offline" ? (
                      <div className="text-center p-4">
                        <span className="material-symbols-outlined text-error text-[40px] mb-2">videocam_off</span>
                        <p className="text-xs font-medium text-outline">Mất kết nối tín hiệu</p>
                      </div>
                    ) : cam.streamStatus === "connected" ? (
                      <div className="w-full h-full relative">
                        {/* Mock stream visual */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10"></div>
                        <img 
                          src="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=500&auto=format&fit=crop" 
                          alt={cam.name} 
                          className="w-full h-full object-cover opacity-80" 
                        />
                        <span className="absolute top-2 left-2 z-10 px-2 py-0.5 bg-red-600 text-white rounded text-[10px] font-bold tracking-wider animate-pulse uppercase">Live</span>
                      </div>
                    ) : cam.streamStatus === "connecting" ? (
                      <div className="text-center p-4">
                        <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                        <p className="text-xs text-outline">Đang kết nối luồng WebRTC...</p>
                      </div>
                    ) : (
                      <div className="text-center p-4 text-outline flex flex-col items-center">
                        <span className="material-symbols-outlined text-[36px] mb-1">pause_circle</span>
                        <p className="text-xs">Chưa kết nối</p>
                      </div>
                    )}
                    
                    {/* Corner badges */}
                    <div className="absolute top-2 right-2 flex flex-col gap-1 items-end z-10">
                      <StatusBadge type={cam.status} label={cam.status === "online" ? "Online" : "Offline"} />
                      <StatusBadge type={cam.streamStatus} />
                    </div>
                  </div>

                  {/* Camera Details */}
                  <div className="p-4 flex-1 flex flex-col justify-between">
                    <div>
                      <h4 className="font-bold text-on-surface text-sm group-hover:text-secondary transition-colors">{cam.name}</h4>
                      <p className="text-xs text-on-surface-variant mt-0.5 truncate">{cam.location}</p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-outline-variant/30 flex items-center justify-between text-[11px] text-on-surface-variant">
                      <span className="flex items-center gap-1 font-medium">
                        <span className="material-symbols-outlined text-[14px]">detector_status</span>
                        {activeRois} vùng ROI
                      </span>
                      <span>
                        {cam.lastAlertTime ? `Báo gần nhất: ${getRelativeTime(cam.lastAlertTime)}` : "Chưa có cảnh báo"}
                      </span>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <button
                        onClick={() => navigate(`/cameras/${cam.id}`)}
                        className="py-2 px-3 text-xs font-semibold bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg transition-all text-center focus:outline-none"
                      >
                        Xem camera
                      </button>
                      <button
                        onClick={() => navigate(`/roi/${cam.id}`)}
                        className="py-2 px-3 text-xs font-semibold bg-primary text-white hover:bg-primary/90 rounded-lg transition-all text-center focus:outline-none"
                      >
                        Thiết lập ROI
                      </button>
                    </div>
                  </div>

                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Recent Alerts Panel */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-on-surface">Cảnh báo gần đây</h3>
            <button 
              onClick={() => navigate("/alerts")} 
              className="text-xs font-bold text-secondary hover:underline"
            >
              Lịch sử cảnh báo
            </button>
          </div>

          <div className="flex flex-col gap-3">
            {alerts.slice(0, 3).map((al) => {
              const borderStyles = al.status === "unread" 
                ? "border-l-4 border-l-error bg-red-500/[0.02]" 
                : al.status === "checking"
                ? "border-l-4 border-l-amber-500 bg-amber-500/[0.02]"
                : "border-l-4 border-l-outline-variant";

              return (
                <div
                  key={al.id}
                  onClick={() => navigate(`/alerts/${al.id}`)}
                  className={`bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/30 flex gap-4 cursor-pointer hover:border-primary/40 hover:shadow-sm transition-all relative ${borderStyles}`}
                >
                  {/* Alert Snapshot */}
                  <div className="w-16 h-16 rounded-lg overflow-hidden shrink-0 border border-outline-variant/20 bg-surface-container-low">
                    <SecureImage src={al.snapshotUrl} className="w-full h-full object-cover" />
                  </div>

                  {/* Alert details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start">
                      <span className={`text-[10px] font-bold uppercase tracking-wider ${al.severity === "danger" ? "text-error" : al.severity === "warning" ? "text-amber-600" : "text-secondary"}`}>
                        {al.severity === "danger" ? "Nguy cấp" : al.severity === "warning" ? "Cảnh báo" : "Thông tin"}
                      </span>
                      <span className="text-[10px] text-on-surface-variant font-medium">
                        {getRelativeTime(al.createdAt)}
                      </span>
                    </div>
                    
                    <h4 className="font-semibold text-xs text-on-surface truncate mt-1">{al.title}</h4>
                    <p className="text-[10px] text-on-surface-variant truncate mt-0.5">
                      Cam: {al.cameraName} • Vùng: {al.roiName || "Không có"}
                    </p>

                    <div className="mt-2.5 flex items-center justify-between">
                      <StatusBadge type={al.status} />

                      {/* Action buttons (only if unread/checking) */}
                      {(al.status === "unread" || al.status === "checking") && (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            onClick={(e) => handleResolve(e, al.id)}
                            className="px-2 py-1 text-[9px] font-bold bg-emerald-500 text-white rounded hover:bg-emerald-600 focus:outline-none"
                          >
                            Đã xử lý
                          </button>
                          <button
                            onClick={(e) => handleFalseAlarm(e, al.id)}
                            className="px-2 py-1 text-[9px] font-bold bg-surface-container-highest text-on-surface-variant rounded hover:text-on-surface focus:outline-none"
                          >
                            Báo nhầm
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {alerts.length === 0 && (
              <div className="p-8 text-center text-outline text-sm">
                <span className="material-symbols-outlined text-[32px] mb-1">done_all</span>
                <p>Không có cảnh báo chưa xử lý</p>
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
};
export default DashboardView;
