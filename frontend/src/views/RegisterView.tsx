import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const RegisterView: React.FC = () => {
  const { registerWithCredentials, loginError, isLoggingIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const plan = searchParams.get("plan") || "free";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const ok = await registerWithCredentials(email, password);
    if (ok) navigate("/dashboard");
  };

  return (
    <div className="w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-on-surface mb-2 tracking-tight">Tạo tài khoản</h1>
        <p className="text-on-surface-variant text-sm">Bắt đầu trải nghiệm {plan === "premium" ? "gói Premium" : "miễn phí"} hệ thống giám sát trẻ em thông minh.</p>
      </div>

      <form onSubmit={handleRegister} className="space-y-4">
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
              placeholder="Tạo mật khẩu (ít nhất 8 ký tự)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline"
            />
          </div>
        </div>

        <label className="flex items-start gap-3 mt-6 cursor-pointer group">
          <input type="checkbox" required className="mt-1 w-4 h-4 rounded border-outline-variant/40 text-primary focus:ring-primary/20 cursor-pointer" />
          <span className="text-sm font-medium text-on-surface-variant group-hover:text-on-surface transition-colors leading-relaxed">
            Tôi đồng ý với <a href="#" className="text-primary hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-primary hover:underline">Chính sách bảo mật</a> của SafeKid Monitor.
          </span>
        </label>

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
          className="w-full h-12 mt-6 bg-primary text-white font-bold rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-[0.98] flex items-center justify-center gap-2 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoggingIn ? (
            <>
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Đang tạo tài khoản…
            </>
          ) : (
            <>
              Tạo tài khoản ngay
              <span className="material-symbols-outlined text-[18px]">person_add</span>
            </>
          )}
        </button>
      </form>

      <div className="mt-8 pt-6 border-t border-outline-variant/20 text-center">
        <p className="text-sm text-on-surface-variant">
          Đã có tài khoản? <Link to="/login" className="font-bold text-primary hover:underline">Đăng nhập</Link>
        </p>
      </div>
    </div>
  );
};
