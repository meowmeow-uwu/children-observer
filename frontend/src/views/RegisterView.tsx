import React from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const RegisterView: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const plan = searchParams.get("plan") || "free";

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    login("parent"); // Auto-login as parent for demo
    navigate("/dashboard");
  };

  return (
    <div className="w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-on-surface mb-2 tracking-tight">Tạo tài khoản</h1>
        <p className="text-on-surface-variant text-sm">Bắt đầu trải nghiệm {plan === "premium" ? "gói Premium" : "miễn phí"} hệ thống giám sát trẻ em thông minh.</p>
      </div>

      <form onSubmit={handleRegister} className="space-y-4">
        <div>
          <label className="block text-sm font-semibold text-on-surface mb-1.5">Họ và tên</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant text-[20px]">person</span>
            <input type="text" placeholder="Nguyễn Văn A" className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline" required />
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-on-surface mb-1.5">Email</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant text-[20px]">mail</span>
            <input type="email" placeholder="Nhập địa chỉ email" className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline" required />
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-on-surface mb-1.5">Mật khẩu</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant text-[20px]">lock</span>
            <input type="password" placeholder="Tạo mật khẩu (ít nhất 8 ký tự)" minLength={8} className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline" required />
          </div>
        </div>

        <label className="flex items-start gap-3 mt-6 cursor-pointer group">
          <input type="checkbox" required className="mt-1 w-4 h-4 rounded border-outline-variant/40 text-primary focus:ring-primary/20 cursor-pointer" />
          <span className="text-sm font-medium text-on-surface-variant group-hover:text-on-surface transition-colors leading-relaxed">
            Tôi đồng ý với <a href="#" className="text-primary hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-primary hover:underline">Chính sách bảo mật</a> của SafeKid Monitor.
          </span>
        </label>

        <button type="submit" className="w-full h-12 mt-6 bg-primary text-white font-bold rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-[0.98] flex items-center justify-center gap-2 focus:outline-none">
          Tạo tài khoản ngay
          <span className="material-symbols-outlined text-[18px]">person_add</span>
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
