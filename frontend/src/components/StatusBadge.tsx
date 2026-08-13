import React from "react";

interface StatusBadgeProps {
  type: "online" | "offline" | "loading" | "success" | "danger" | "warning" | "info" | "unread" | "checking" | "resolved" | "false_alarm" | "connected" | "connecting" | "failed" | "idle" | "reconnecting" | "closed";
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, label }) => {
  const getBadgeStyles = () => {
    switch (type) {
      case "online":
      case "success":
      case "resolved":
      case "connected":
        return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
      case "offline":
      case "danger":
      case "failed":
        return "bg-error/10 text-error border-error/20";
      case "warning":
      case "checking":
      case "connecting":
      case "reconnecting":
        return "bg-amber-500/10 text-amber-700 border-amber-500/20";
      case "loading":
        return "bg-primary-container/10 text-primary-container border-primary-container/20 animate-pulse";
      case "unread":
        return "bg-error text-white border-transparent";
      case "false_alarm":
      case "idle":
      case "closed":
        return "bg-outline-variant/30 text-on-surface-variant border-outline-variant/50";
      case "info":
      default:
        return "bg-secondary/10 text-secondary border-secondary/20";
    }
  };

  const getDefaultLabel = () => {
    switch (type) {
      case "online":
        return "Hoạt động";
      case "offline":
        return "Ngoại tuyến";
      case "loading":
        return "Đang tải...";
      case "success":
      case "resolved":
        return "Đã xử lý";
      case "danger":
        return "Nguy hiểm";
      case "warning":
      case "checking":
        return "Cần kiểm tra";
      case "unread":
        return "Chưa xem";
      case "false_alarm":
        return "Báo nhầm";
      case "connected":
        return "Đang phát trực tiếp";
      case "connecting":
        return "Đang kết nối";
      case "reconnecting":
        return "Đang kết nối lại...";
      case "failed":
        return "Lỗi kết nối";
      case "idle":
        return "Chưa kết nối";
      case "closed":
        return "Đã ngắt kết nối";
      case "info":
      default:
        return "Thông tin";
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${getBadgeStyles()}`}
    >
      {(type === "online" || type === "connected") && (
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
      )}
      {(type === "offline" || type === "failed" || type === "closed") && (
        <span className="w-1.5 h-1.5 rounded-full bg-error mr-1.5"></span>
      )}
      {(type === "loading" || type === "connecting" || type === "reconnecting") && (
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5 animate-ping"></span>
      )}
      {label || getDefaultLabel()}
    </span>
  );
};
export default StatusBadge;
