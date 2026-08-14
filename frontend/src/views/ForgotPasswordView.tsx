import React, { useState } from "react";
import { Link } from "react-router-dom";

export const ForgotPasswordView: React.FC = () => {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="w-full">
      <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-medium text-on-surface-variant hover:text-primary transition-colors mb-8 focus:outline-none">
        <span className="material-symbols-outlined text-[18px]">arrow_back</span>
        Quay lại Đăng nhập
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-on-surface mb-2 tracking-tight">Khôi phục mật khẩu</h1>
        <p className="text-on-surface-variant text-sm">Nhập email của bạn và chúng tôi sẽ gửi hướng dẫn đặt lại mật khẩu.</p>
      </div>

      {!submitted ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">Email liên kết</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant text-[20px]">mail</span>
              <input type="email" placeholder="Nhập địa chỉ email" className="w-full h-12 pl-10 pr-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all outline-none text-sm text-on-surface placeholder:text-outline" required />
            </div>
          </div>

          <button type="submit" className="w-full h-12 bg-primary text-white font-bold rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-[0.98] flex items-center justify-center focus:outline-none">
            Gửi liên kết khôi phục
          </button>
        </form>
      ) : (
        <div className="bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-2xl text-center animate-fade-in">
          <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center mx-auto mb-4">
            <span className="material-symbols-outlined text-[24px]">mark_email_read</span>
          </div>
          <h3 className="text-lg font-bold text-emerald-800 mb-2">Đã gửi email khôi phục!</h3>
          <p className="text-sm text-emerald-700 leading-relaxed mb-6">
            Vui lòng kiểm tra hộp thư đến (và thư mục rác) để nhận liên kết đặt lại mật khẩu của bạn.
          </p>
          <button onClick={() => setSubmitted(false)} className="text-sm font-bold text-emerald-700 hover:text-emerald-800 focus:outline-none underline">
            Thử một email khác
          </button>
        </div>
      )}
    </div>
  );
};
