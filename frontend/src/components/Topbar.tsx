import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate, useLocation } from "react-router-dom";
import { useNotificationStore } from "../store/notificationStore";
import { NotificationCenter } from "./NotificationCenter";

export const Topbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { unreadCount } = useNotificationStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  // Derive page title from route
  const getPageTitle = () => {
    const path = location.pathname;
    if (path.startsWith("/dashboard")) return "Tổng quan";
    if (path.startsWith("/cameras")) return "Camera trực tiếp";
    if (path.startsWith("/roi")) return "Vùng nguy hiểm ROI";
    if (path.startsWith("/alerts")) return "Danh sách Cảnh báo";
    if (path.startsWith("/devices")) return "Trạng thái Thiết bị";
    if (path.startsWith("/children")) return "Hồ sơ Trẻ em";
    if (path.startsWith("/settings/privacy")) return "Quyền riêng tư & Dữ liệu";
    return "SafeKid Monitor";
  };

  const getRoleLabel = () => {
    if (user?.role === "parent") return "Phụ huynh (Admin)";
    if (user?.role === "guardian") return "Người giám hộ";
    return "Người xem";
  };

  return (
    <header className="bg-surface dark:bg-surface-dim border-b border-outline-variant dark:border-outline shadow-sm flex justify-between items-center w-full px-6 py-3 shrink-0 h-[72px] sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <h2 className="font-headline-sm text-headline-sm text-primary font-bold">{getPageTitle()}</h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Role Badge Indicator */}
        <span className="hidden md:inline-flex items-center gap-2 px-3.5 py-1.5 bg-surface-container-low text-primary rounded-full font-label-sm text-[12px] font-semibold border border-primary/10">
          <span className={`w-2 h-2 rounded-full ${user?.role === "parent" ? "bg-[#10B981]" : user?.role === "guardian" ? "bg-[#F59E0B]" : "bg-outline"}`}></span>
          {getRoleLabel()}
        </span>

        {/* Notifications Icon with count */}
        {user?.role !== "viewer" && (
          <div className="relative">
            <button
              onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              className="w-10 h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-container-high transition-all relative focus:outline-none"
            >
              <span className="material-symbols-outlined">notifications</span>
              {unreadCount > 0 && (
                <span className="absolute top-2 right-2.5 px-1 min-w-[14px] h-[14px] bg-error text-white font-bold text-[8px] rounded-full flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>
            <NotificationCenter
              isOpen={isNotificationsOpen}
              onClose={() => setIsNotificationsOpen(false)}
            />
          </div>
        )}

        {/* Profile Avatar Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="w-9 h-9 rounded-full overflow-hidden border border-outline-variant focus:outline-none focus:ring-2 focus:ring-primary ml-2 flex items-center justify-center bg-surface-container-high"
          >
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt={user.name} className="w-full h-full object-cover" />
            ) : (
              <span className="material-symbols-outlined text-outline">account_circle</span>
            )}
          </button>

          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setDropdownOpen(false)}></div>
              <div className="absolute right-0 mt-2 w-56 bg-surface-container-lowest border border-outline-variant/30 rounded-xl shadow-lg py-2 z-40 animate-fade-in popover-shadow">
                <div className="px-4 py-2 border-b border-outline-variant/20">
                  <p className="font-semibold text-sm text-on-surface truncate">{user?.name}</p>
                  <p className="text-xs text-on-surface-variant truncate mt-0.5">{user?.email}</p>
                </div>
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    logout();
                    navigate("/login");
                  }}
                  className="w-full text-left px-4 py-2.5 text-sm text-error hover:bg-error-container/30 transition-colors flex items-center gap-2"
                >
                  <span className="material-symbols-outlined text-[18px]">logout</span>
                  Đăng xuất
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
