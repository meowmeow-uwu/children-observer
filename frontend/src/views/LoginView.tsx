import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const LoginView: React.FC = () => {
  const { loginWithCredentials, loginError, isLoggingIn } = useAuth();
  const navigate = useNavigate();
  const [showDemo, setShowDemo] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // ---- Task 1.1: Form submit gọi API thật ----
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const ok = await loginWithCredentials(email, password);
    if (ok) navigate("/dashboard");
  };

  return (
    <div className="w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-on-surface mb-2 tracking-tight">Chào mừng trở lại!</h1>
        <p className="text-on-surface-variant text-sm">Đăng nhập để theo dõi và bảo vệ sự an toàn của con bạn.</p>
      </div>

      <form onSubmit={handleLogin} className="space-y-5">
        <div>
          <label className="block text-sm font-semibold text-on-surface mb-1.5">Email</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant text-[20px]">mail</span>
            <input
              type="email"
              placeholder="Nhập địa chỉ email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-on-surface mb-1.5">Mật khẩu</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant text-[20px]">lock</span>
            <input
              type="password"
              placeholder="Nhập mật khẩu"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 cursor-pointer group">
            <input type="checkbox" className="w-4 h-4 rounded border-outline-variant/40 text-primary focus:ring-primary/20 cursor-pointer" />
            <span className="text-sm font-medium text-on-surface-variant group-hover:text-on-surface transition-colors">Ghi nhớ đăng nhập</span>
          </label>
          <Link to="/forgot-password" className="text-sm font-bold text-primary hover:text-primary/80 transition-colors">Quên mật khẩu?</Link>
        </div>

        {/* Hiển thị lỗi từ backend */}
        {loginError && (
          <div className="flex items-center gap-2 p-3 bg-error/5 border border-error/20 rounded-xl text-xs text-error font-medium animate-fade-in">
            <span className="material-symbols-outlined text-[16px]">error</span>
            {loginError}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoggingIn}
          className="w-full h-12 bg-primary text-white font-bold rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-[0.98] flex items-center justify-center gap-2 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoggingIn ? (
            <>
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Đang xác thực…
            </>
          ) : (
            <>
              Đăng nhập hệ thống
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </>
          )}
        </button>
      </form>

      <div className="mt-8 pt-6 border-t border-outline-variant/20">
        <p className="text-center text-sm text-on-surface-variant mb-4">
          Chưa có tài khoản? <Link to="/register" className="font-bold text-primary hover:underline">Đăng ký ngay</Link>
        </p>

        {/* Quick Demo Access — dùng tài khoản được seed trong Docker. */}
        {!showDemo ? (
          <button
            onClick={() => setShowDemo(true)}
            className="w-full py-2 text-xs font-semibold text-outline hover:text-on-surface-variant transition-colors underline focus:outline-none"
          >
            Mở bảng Đăng nhập Demo (Phân quyền)
          </button>
        ) : (
          <div className="flex flex-col gap-2 mt-4 animate-fade-in bg-surface-container-low p-4 rounded-xl border border-outline-variant/20">
            <p className="text-xs font-bold text-on-surface mb-1">Quick Demo Access <span className="text-outline font-normal">(backend thật)</span></p>
            <button
              onClick={async () => {
                const ok = await loginWithCredentials("demo@childrenobserver.org", "demo12345");
                if (ok) navigate("/dashboard");
              }}
              className="py-2.5 px-4 bg-primary/10 text-primary text-xs font-bold rounded-lg hover:bg-primary/20 text-left flex justify-between items-center"
            >
              Phụ huynh (Admin) <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
