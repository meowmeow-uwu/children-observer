import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../types";

export const LoginView: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleRoleSelect = async (role: Role) => {
    const success = await login(role);
    if (success) {
      navigate("/dashboard");
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center items-center p-4">
      <div className="bg-surface-container-lowest w-full max-w-[400px] p-8 rounded-2xl shadow-[0_8px_30px_rgba(30,58,138,0.06)] border border-outline-variant/30 text-center">
        {/* Logo */}
        <div className="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center mx-auto mb-4 text-white shadow-sm">
          <span className="material-symbols-outlined text-[36px] fill">child_care</span>
        </div>
        <h1 className="text-2xl font-bold text-on-surface tracking-tight mb-2">SafeKid Monitor</h1>
        <p className="text-on-surface-variant text-sm mb-8">Hệ thống Giám sát &amp; Bảo vệ Trẻ em AI</p>
        
        <p className="text-on-surface font-medium text-left mb-4">Đăng nhập Demo dưới vai trò:</p>
        <div className="flex flex-col gap-3">
          <button
            onClick={() => handleRoleSelect("parent")}
            className="w-full py-4 px-6 rounded-xl border border-outline-variant hover:border-secondary hover:bg-secondary/5 font-semibold text-on-surface hover:text-secondary flex items-center gap-4 transition-all text-left group"
          >
            <div className="w-10 h-10 rounded-full bg-primary-container text-primary flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined">admin_panel_settings</span>
            </div>
            <div>
              <span className="block text-sm">Phụ huynh (Admin)</span>
              <span className="block text-[11px] text-on-surface-variant font-normal mt-0.5">Toàn quyền cấu hình ROI và cài đặt hệ thống.</span>
            </div>
          </button>

          <button
            onClick={() => handleRoleSelect("guardian")}
            className="w-full py-4 px-6 rounded-xl border border-outline-variant hover:border-secondary hover:bg-secondary/5 font-semibold text-on-surface hover:text-secondary flex items-center gap-4 transition-all text-left group"
          >
            <div className="w-10 h-10 rounded-full bg-secondary-container/20 text-secondary flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined">family_home</span>
            </div>
            <div>
              <span className="block text-sm">Người giám hộ</span>
              <span className="block text-[11px] text-on-surface-variant font-normal mt-0.5">Xem trực tiếp, nhận cảnh báo. Không có quyền cài đặt.</span>
            </div>
          </button>

          <button
            onClick={() => handleRoleSelect("viewer")}
            className="w-full py-4 px-6 rounded-xl border border-outline-variant hover:border-secondary hover:bg-secondary/5 font-semibold text-on-surface hover:text-secondary flex items-center gap-4 transition-all text-left group"
          >
            <div className="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined">visibility</span>
            </div>
            <div>
              <span className="block text-sm">Người xem tạm thời</span>
              <span className="block text-[11px] text-on-surface-variant font-normal mt-0.5">Chỉ xem luồng trực tiếp, không xem được cảnh báo/cài đặt.</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
