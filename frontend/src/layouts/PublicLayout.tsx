import React from "react";
import { Outlet, Link } from "react-router-dom";

export const PublicLayout: React.FC = () => {
  return (
    <div className="h-screen overflow-y-auto bg-surface flex flex-col font-sans">
      {/* Public Navbar */}
      <header className="sticky top-0 z-50 bg-surface/80 backdrop-blur-md border-b border-outline-variant/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 focus:outline-none">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white">
              <span className="material-symbols-outlined text-[20px]">security</span>
            </div>
            <span className="text-xl font-bold tracking-tight text-on-surface">SafeKid Monitor</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            <Link to="/" className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors">Trang chủ</Link>
            <Link to="/pricing" className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors">Bảng giá</Link>
            <a href="#features" className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors">Tính năng</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login" className="px-4 py-2 text-sm font-bold text-primary hover:bg-primary/5 rounded-xl transition-colors focus:outline-none hidden sm:block">Đăng nhập</Link>
            <Link to="/register" className="px-5 py-2 text-sm font-bold bg-primary text-white hover:bg-primary/90 rounded-xl shadow-sm transition-transform active:scale-95 focus:outline-none">Dùng thử ngay</Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>

      {/* Public Footer */}
      <footer className="bg-surface-container-low py-12 mt-auto border-t border-outline-variant/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2 opacity-80">
            <span className="material-symbols-outlined text-[20px] text-primary">security</span>
            <span className="font-bold text-on-surface">SafeKid Monitor © {new Date().getFullYear()}</span>
          </div>
          <div className="flex gap-6 text-sm text-on-surface-variant">
            <Link to="/privacy" className="hover:text-primary transition-colors">Bảo mật</Link>
            <a href="#" className="hover:text-primary transition-colors">Điều khoản</a>
            <a href="#" className="hover:text-primary transition-colors">Trợ giúp</a>
          </div>
        </div>
      </footer>
    </div>
  );
};
