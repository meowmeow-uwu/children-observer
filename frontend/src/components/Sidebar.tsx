import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  
  const menuItems = [
    { to: "/dashboard", icon: "dashboard", label: "Tổng quan", roles: ["parent", "guardian", "viewer"] },
    { to: "/cameras", icon: "videocam", label: "Camera trực tiếp", roles: ["parent", "guardian", "viewer"] },
    { to: "/roi", icon: "detector_status", label: "Vùng nguy hiểm ROI", roles: ["parent"] },
    { to: "/alerts", icon: "notifications_active", label: "Cảnh báo", roles: ["parent", "guardian"] },
    { to: "/devices", icon: "router", label: "Thiết bị", roles: ["parent", "guardian"] },
    { to: "/children", icon: "child_care", label: "Hồ sơ trẻ em", roles: ["parent", "guardian"] },
  ];

  const allowedMenuItems = menuItems.filter(item => item.roles.includes(user?.role || "viewer"));

  return (
    <aside className="hidden md:flex bg-primary dark:bg-on-primary-fixed fixed left-0 top-0 h-screen w-[280px] flex-col gap-2 py-6 shadow-md z-20">
      <div className="px-6 mb-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-surface-container-lowest flex items-center justify-center">
          <span className="material-symbols-outlined text-primary text-2xl filled-icon">security</span>
        </div>
        <div>
          <h1 className="font-headline-md text-[20px] font-bold text-white leading-tight">SafeKid Monitor</h1>
          <p className="text-secondary-fixed dark:text-primary-fixed-dim text-xs">Giám sát an toàn</p>
        </div>
      </div>
      
      <nav className="flex-1 overflow-y-auto mt-4 px-2">
        <ul className="space-y-1">
          {allowedMenuItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `rounded-lg mx-2 px-4 py-3 flex items-center gap-3 transition-all ${
                    isActive
                      ? "bg-secondary-container text-on-secondary-container shadow-sm scale-95"
                      : "text-on-primary-container hover:bg-on-primary-fixed-variant"
                  }`
                }
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span className="text-sm font-medium">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {user?.role === "parent" && (
        <div className="px-2 mt-auto">
          <NavLink
            to="/settings/privacy"
            className={({ isActive }) =>
              `rounded-lg mx-2 px-4 py-3 flex items-center gap-3 transition-all ${
                isActive
                  ? "bg-secondary-container text-on-secondary-container shadow-sm scale-95"
                  : "text-on-primary-container hover:bg-on-primary-fixed-variant"
              }`
            }
          >
            <span className="material-symbols-outlined">settings</span>
            <span className="text-sm font-medium">Cài đặt</span>
          </NavLink>
        </div>
      )}
    </aside>
  );
};
