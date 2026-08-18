import React from "react";
import { Outlet, Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const AuthLayout: React.FC = () => {
  const { isAuthenticated } = useAuth();

  // Đã đăng nhập → vào thẳng dashboard
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="h-screen overflow-y-auto bg-surface flex flex-col md:flex-row font-sans">
      {/* Left side: Form content */}
      <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-20 xl:px-24 py-12 relative z-10 bg-surface">
        <div className="absolute top-6 left-6 sm:top-8 sm:left-8">
          <Link to="/" className="flex items-center gap-2 focus:outline-none group">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all">
              <span className="material-symbols-outlined text-[24px]">security</span>
            </div>
            <span className="text-xl font-bold tracking-tight text-on-surface">SafeKid Monitor</span>
          </Link>
        </div>

        <div className="w-full max-w-md mx-auto">
          <Outlet />
        </div>
      </div>

      {/* Right side: Branding / Image */}
      <div className="hidden md:flex flex-1 relative bg-primary items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary-container to-secondary"></div>

        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-full h-full opacity-10 pointer-events-none">
          <svg className="absolute w-[800px] h-[800px] -top-[200px] -right-[200px] text-white" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <path fill="currentColor" d="M42.7,-73.4C55.9,-67.9,67.6,-57.8,76.5,-45.3C85.4,-32.8,91.5,-17.9,91.8,-2.8C92.1,12.3,86.6,27.6,76.6,39.5C66.6,51.4,52.1,59.9,37.3,66.5C22.5,73.1,7.4,77.8,-6.9,78.2C-21.2,78.6,-34.7,74.7,-48.5,67.7C-62.3,60.7,-76.4,50.6,-84.3,37.1C-92.2,23.6,-93.9,6.7,-89.2,-8.1C-84.5,-22.9,-73.4,-35.6,-60.7,-45.5C-48,-55.4,-33.7,-62.5,-20.1,-67.5C-6.5,-72.5,6.4,-75.4,19.8,-76C33.2,-76.6,47.1,-74.9,42.7,-73.4Z" transform="translate(100 100)" />
          </svg>
        </div>

        <div className="relative z-10 p-12 max-w-lg text-white">
          <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-8 shadow-lg border border-white/20">
            <span className="material-symbols-outlined text-[36px] text-white">nest_cam_iq</span>
          </div>
          <h2 className="text-4xl font-bold mb-4 leading-tight text-white">Bảo vệ con bạn<br/>với công nghệ AI</h2>
          <p className="text-primary-fixed text-lg leading-relaxed mb-8">
            Hệ thống giám sát thông minh đầu tiên tự động phát hiện vùng nguy hiểm, té ngã và cảnh báo tức thời trên điện thoại của bạn.
          </p>

          <div className="flex items-center gap-4 text-sm font-medium bg-white/10 backdrop-blur-md w-max px-4 py-3 rounded-xl border border-white/10">
            <div className="flex -space-x-2">
              <div className="w-8 h-8 rounded-full bg-blue-400 border-2 border-primary-container"></div>
              <div className="w-8 h-8 rounded-full bg-indigo-400 border-2 border-primary-container"></div>
              <div className="w-8 h-8 rounded-full bg-purple-400 border-2 border-primary-container"></div>
            </div>
            <span className="text-white">Tin dùng bởi 10,000+ phụ huynh</span>
          </div>
        </div>
      </div>
    </div>
  );
};
