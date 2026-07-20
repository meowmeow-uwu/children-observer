import React, { useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useNotificationStore } from "../store/notificationStore";

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const { notifications, markAsRead, markAllAsRead, clearAll } = useNotificationStore();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleNotificationClick = (id: string, relatedAlertId?: string) => {
    markAsRead(id);
    onClose();
    if (relatedAlertId) {
      navigate(`/alerts/${relatedAlertId}`);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "danger":
        return <span className="material-symbols-outlined text-error text-[18px]">warning</span>;
      case "warning":
        return <span className="material-symbols-outlined text-amber-500 text-[18px]">error</span>;
      case "success":
        return <span className="material-symbols-outlined text-emerald-500 text-[18px]">check_circle</span>;
      case "info":
      default:
        return <span className="material-symbols-outlined text-primary text-[18px]">info</span>;
    }
  };

  const getNotificationColorClass = (type: string) => {
    switch (type) {
      case "danger": return "bg-red-500/10";
      case "warning": return "bg-amber-500/10";
      case "success": return "bg-emerald-500/10";
      case "info":
      default:
        return "bg-primary/10";
    }
  };

  return (
    <div
      ref={dropdownRef}
      className="absolute top-14 right-4 md:right-0 w-80 max-w-sm bg-surface-container-lowest border border-outline-variant/35 rounded-2xl shadow-xl z-50 overflow-hidden animate-scale-up"
    >
      {/* Header */}
      <div className="p-4 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-low">
        <h4 className="font-bold text-xs text-on-surface">Thông báo thông minh</h4>
        <div className="flex gap-2">
          {notifications.length > 0 && (
            <>
              <button
                onClick={markAllAsRead}
                className="text-[10px] font-bold text-primary hover:underline focus:outline-none"
              >
                Đọc hết
              </button>
              <span className="text-outline/40 text-[10px]">|</span>
              <button
                onClick={clearAll}
                className="text-[10px] font-bold text-error hover:underline focus:outline-none"
              >
                Xóa hết
              </button>
            </>
          )}
        </div>
      </div>

      {/* List content */}
      <div className="max-h-[350px] overflow-y-auto divide-y divide-outline-variant/10">
        {notifications.map((item) => (
          <div
            key={item.id}
            onClick={() => handleNotificationClick(item.id, item.relatedAlertId)}
            className={`p-3.5 flex gap-3 items-start cursor-pointer hover:bg-surface-container-low transition-colors ${
              !item.read ? "bg-primary/[0.02]" : ""
            }`}
          >
            {/* Status indicator Icon */}
            <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center ${getNotificationColorClass(item.type)}`}>
              {getNotificationIcon(item.type)}
            </div>

            {/* Description */}
            <div className="flex-1 min-w-0 space-y-1">
              <div className="flex justify-between items-start gap-2">
                <span className={`text-[11px] font-bold leading-normal block truncate ${!item.read ? "text-on-surface" : "text-on-surface-variant font-medium"}`}>
                  {item.title}
                </span>
                {!item.read && (
                  <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0 mt-1.5"></span>
                )}
              </div>
              <p className="text-[10px] text-on-surface-variant leading-relaxed">
                {item.message}
              </p>
              <span className="text-[9px] text-outline block text-right mt-1.5">
                {new Date(item.createdAt).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          </div>
        ))}

        {notifications.length === 0 && (
          <div className="py-12 text-center text-outline text-xs space-y-1">
            <span className="material-symbols-outlined text-[36px] text-outline-variant">notifications_off</span>
            <p className="font-semibold text-on-surface-variant">Không có thông báo mới</p>
            <p className="text-[10px]">Hộp thư của bạn đang được làm sạch.</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 bg-surface-container-low border-t border-outline-variant/10 text-center">
        <button
          onClick={() => {
            onClose();
            navigate("/alerts");
          }}
          className="text-xs font-bold text-secondary hover:underline focus:outline-none w-full"
        >
          Xem lịch sử sự cố an toàn
        </button>
      </div>

    </div>
  );
};
export default NotificationCenter;
