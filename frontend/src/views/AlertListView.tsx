import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAlertStore } from "../store/alertStore";
import { StatusBadge } from "../components/StatusBadge";
import { SecureImage } from "../components/SecureImage";
import { useToast } from "../components/Toast";
import type { AlertStatus } from "../types";

export const AlertListView: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { alerts, updateAlertStatus } = useAlertStore();

  const [activeTab, setActiveTab] = useState<AlertStatus | "all" | "danger">("all");

  // Filter alerts based on activeTab selection
  const filteredAlerts = alerts.filter((al) => {
    if (activeTab === "all") return true;
    if (activeTab === "danger") return al.severity === "danger";
    return al.status === activeTab;
  });

  const getRelativeTime = (isoString: string) => {
    const date = new Date(isoString);
    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return "Vừa xong";
    if (diffMins < 60) return `${diffMins} phút trước`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} giờ trước`;
    
    return date.toLocaleDateString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const handleResolve = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation();
    updateAlertStatus(alertId, "resolved", {
      resolvedAt: new Date().toISOString(),
      resolvedBy: "Nguyễn Văn A",
      notes: "Đã đánh dấu xử lý từ danh sách cảnh báo"
    });
    showToast("Đã đánh dấu cảnh báo là đã xử lý!", "success");
  };

  const handleFalseAlarm = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation();
    updateAlertStatus(alertId, "false_alarm", {
      checkedBy: "Nguyễn Văn A",
      falseAlarmReason: "Hành vi an toàn thông thường của gia đình"
    });
    showToast("Cảnh báo được gắn nhãn báo nhầm thành công", "info");
  };

  const getChannelLabel = (channel: string) => {
    switch (channel) {
      case "in_app": return "App";
      case "web_push": return "Push Web";
      case "zalo": return "Zalo";
      case "email": return "Email";
      case "sms": return "SMS";
      default: return channel;
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-on-surface">Cảnh báo an toàn</h2>
        <p className="text-sm text-on-surface-variant mt-1">
          Theo dõi các sự cố đã phát hiện bởi trí tuệ nhân tạo và lưu trữ lịch sử xử lý.
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex border-b border-outline-variant/30 gap-6 overflow-x-auto pb-0.5">
        <button
          onClick={() => setActiveTab("all")}
          className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
            activeTab === "all" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Tất cả ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab("unread")}
          className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
            activeTab === "unread" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Chưa xem ({alerts.filter((a) => a.status === "unread").length})
        </button>
        <button
          onClick={() => setActiveTab("checking")}
          className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
            activeTab === "checking" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Đang kiểm tra ({alerts.filter((a) => a.status === "checking").length})
        </button>
        <button
          onClick={() => setActiveTab("resolved")}
          className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
            activeTab === "resolved" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Đã xử lý ({alerts.filter((a) => a.status === "resolved").length})
        </button>
        <button
          onClick={() => setActiveTab("false_alarm")}
          className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
            activeTab === "false_alarm" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Báo nhầm ({alerts.filter((a) => a.status === "false_alarm").length})
        </button>
        <button
          onClick={() => setActiveTab("danger")}
          className={`py-3 px-1 text-sm font-semibold border-b-2 transition-all focus:outline-none whitespace-nowrap ${
            activeTab === "danger" ? "border-error text-error" : "border-transparent text-on-surface-variant hover:text-on-surface"
          }`}
        >
          🔥 Nguy cấp ({alerts.filter((a) => a.severity === "danger").length})
        </button>
      </div>

      {/* Alerts List */}
      <div className="flex flex-col gap-4">
        {filteredAlerts.map((al) => {
          const borderStyles = al.status === "unread" 
            ? "border-l-4 border-l-error bg-red-500/[0.01]" 
            : al.status === "checking"
            ? "border-l-4 border-l-amber-500 bg-amber-500/[0.01]"
            : "border-l-4 border-l-outline-variant";

          return (
            <div
              key={al.id}
              onClick={() => navigate(`/alerts/${al.id}`)}
              className={`bg-surface-container-lowest p-4 md:p-5 rounded-2xl border border-outline-variant/30 flex flex-col md:flex-row gap-5 cursor-pointer hover:border-primary/40 hover:shadow-md transition-all relative ${borderStyles}`}
            >
              {/* Snapshot thumbnail */}
              <div className="w-full md:w-36 h-40 md:h-24 rounded-xl overflow-hidden shrink-0 border border-outline-variant/20 bg-surface-container-low relative">
                <SecureImage src={al.snapshotUrl} className="w-full h-full object-cover" />
                <div className="absolute bottom-1 right-1 bg-black/60 px-1.5 py-0.5 rounded text-[9px] text-white font-bold">
                  {Math.round(al.confidence * 100)}% Match
                </div>
              </div>

              {/* Information */}
              <div className="flex-1 flex flex-col justify-between min-w-0">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-[10px] font-bold uppercase tracking-wider ${al.severity === "danger" ? "text-error" : al.severity === "warning" ? "text-amber-600" : "text-secondary"}`}>
                      {al.severity === "danger" ? "Nguy hiểm" : al.severity === "warning" ? "Cảnh báo" : "Thông báo"}
                    </span>
                    <span className="text-outline-variant text-xs">•</span>
                    <span className="text-xs text-on-surface-variant font-medium">
                      {getRelativeTime(al.createdAt)}
                    </span>
                    <span className="text-outline-variant text-xs">•</span>
                    <span className="text-xs text-on-surface-variant font-medium">
                      Camera: <strong className="text-on-surface">{al.cameraName}</strong>
                    </span>
                  </div>

                  <h3 className="font-bold text-sm md:text-base text-on-surface line-clamp-2 md:line-clamp-1">{al.title}</h3>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Khu vực giám sát: <strong className="text-on-surface-variant font-semibold">{al.roiName || "Toàn màn hình"}</strong>
                  </p>
                </div>

                {/* Badges footer */}
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-outline-variant/10">
                  <div className="flex items-center gap-4">
                    <StatusBadge type={al.status} />
                    
                    {/* Notification channel indicators */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-medium text-outline mr-0.5">Kênh đã gửi:</span>
                      {al.channels.map((chan) => (
                        <span key={chan} className="px-2 py-0.5 bg-surface-container-low text-on-surface-variant text-[9px] rounded font-bold border border-outline-variant/20">
                          {getChannelLabel(chan)}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/alerts/${al.id}`);
                      }}
                      className="py-1.5 px-3.5 text-xs font-bold bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg transition-all focus:outline-none"
                    >
                      Xem chi tiết
                    </button>

                    {(al.status === "unread" || al.status === "checking") && (
                      <>
                        <button
                          onClick={(e) => handleResolve(e, al.id)}
                          className="py-1.5 px-3.5 text-xs font-bold bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-all focus:outline-none shadow-sm"
                        >
                          Đã xử lý
                        </button>
                        <button
                          onClick={(e) => handleFalseAlarm(e, al.id)}
                          className="py-1.5 px-3.5 text-xs font-bold bg-surface-variant hover:bg-outline-variant/40 text-on-surface-variant hover:text-on-surface rounded-lg transition-all focus:outline-none"
                        >
                          Báo nhầm
                        </button>
                      </>
                    )}
                  </div>
                </div>

              </div>

            </div>
          );
        })}

        {filteredAlerts.length === 0 && (
          <div className="py-16 bg-surface-container-lowest border border-outline-variant/30 rounded-2xl text-center max-w-sm mx-auto my-8">
            <span className="material-symbols-outlined text-[48px] text-outline mb-2">done_all</span>
            <h3 className="font-bold text-on-surface">Không có cảnh báo</h3>
            <p className="text-xs text-on-surface-variant mt-1">Mọi thứ đều an toàn, không có cảnh báo nào trong bộ lọc này.</p>
          </div>
        )}
      </div>
    </div>
  );
};
export default AlertListView;
