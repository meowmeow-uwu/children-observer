import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useAlertStore } from "../store/alertStore";

export const MobileBottomNav: React.FC = () => {
  const { user } = useAuth();
  const alerts = useAlertStore((state) => state.alerts);
  const unreadCount = alerts.filter((a) => a.status === "unread").length;

  // Tabs layout as per strict MVP guidelines
  const navTabs = [
    { to: "/dashboard", icon: "dashboard", label: "Tổng quan", roles: ["parent", "guardian", "viewer"] },
    { to: "/cameras", icon: "videocam", label: "Camera", roles: ["parent", "guardian", "viewer"] },
    { to: "/alerts", icon: "warning", label: "Cảnh báo", roles: ["parent", "guardian"], badge: unreadCount },
    { to: "/devices", icon: "router", label: "Thiết bị", roles: ["parent", "guardian"] },
    { to: "/settings/privacy", icon: "settings", label: "Cài đặt", roles: ["parent"] }
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 rounded-t-xl bg-white dark:bg-white shadow-[0_-4px_20px_rgba(30,58,138,0.05)] border-t border-outline-variant/30 flex justify-around items-center px-4 py-3 pb-safe">
      {navTabs.map((tab) => {
        const isAllowed = tab.roles.includes(user?.role || "viewer");

        if (!isAllowed) {
          return (
            <button
              key={tab.to}
              disabled
              className="flex flex-col items-center justify-center text-outline opacity-40 cursor-not-allowed scale-90 w-16"
            >
              <span className="material-symbols-outlined text-[20px]">{tab.icon}</span>
              <span className="text-[10px] mt-1 font-medium">{tab.label}</span>
            </button>
          );
        }

        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center rounded-2xl duration-200 transition-all min-w-[52px] min-h-[48px] relative cursor-pointer ${
                isActive
                  ? "text-secondary font-bold"
                  : "text-on-surface-variant active:bg-surface-container-high"
              }`
            }
          >
            <span className="material-symbols-outlined text-[22px]">{tab.icon}</span>
            <span className="text-[10px] mt-0.5 font-medium">{tab.label}</span>
            {!!tab.badge && (
              <span className="absolute top-0.5 right-2 w-2.5 h-2.5 bg-error rounded-full ring-2 ring-white"></span>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
};
