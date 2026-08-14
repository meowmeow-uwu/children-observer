import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export const TelegramCallbackView: React.FC = () => {
  const [status, setStatus] = useState<"loading" | "success">("loading");

  useEffect(() => {
    // Simulate linking process
    const timer = setTimeout(() => {
      setStatus("success");
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="w-full text-center">
      {status === "loading" ? (
        <div className="flex flex-col items-center justify-center animate-fade-in">
          <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center mb-6">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h2 className="text-2xl font-bold text-on-surface mb-2">Đang xử lý liên kết...</h2>
          <p className="text-sm text-on-surface-variant">Vui lòng đợi trong giây lát để hệ thống xác thực tài khoản Telegram của bạn.</p>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center animate-scale-up">
          <div className="w-20 h-20 bg-blue-500 text-white rounded-full flex items-center justify-center mb-6 shadow-lg shadow-blue-500/30">
            <span className="material-symbols-outlined text-[40px]">send</span>
          </div>
          <h2 className="text-2xl font-bold text-on-surface mb-4">Đã liên kết Telegram thành công!</h2>
          <p className="text-sm text-on-surface-variant mb-8 leading-relaxed max-w-sm mx-auto">
            Hệ thống sẽ gửi cảnh báo khẩn cấp (té ngã, bạo lực, vùng nguy hiểm) trực tiếp đến tin nhắn Telegram của bạn ngay từ bây giờ.
          </p>
          <Link to="/dashboard" className="px-8 py-3.5 bg-primary text-white font-bold rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-[0.98] focus:outline-none">
            Trở về Bảng điều khiển
          </Link>
        </div>
      )}
    </div>
  );
};
