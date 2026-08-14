import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

export const CheckoutView: React.FC = () => {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("yearly");
  const [status, setStatus] = useState<"pending" | "success">("pending");
  const navigate = useNavigate();

  const price = billingCycle === "monthly" ? 99000 : 99000 * 12 * 0.8; // 20% off for yearly

  useEffect(() => {
    // Simulate webhook polling for payment success after 5 seconds
    const timer = setTimeout(() => {
      setStatus("success");
    }, 5000);
    return () => clearTimeout(timer);
  }, []);

  if (status === "success") {
    return (
      <div className="max-w-xl mx-auto py-20 text-center animate-scale-up">
        <div className="w-24 h-24 bg-emerald-500 text-white rounded-full flex items-center justify-center mx-auto mb-8 shadow-lg shadow-emerald-500/30">
          <span className="material-symbols-outlined text-[48px]">check_circle</span>
        </div>
        <h2 className="text-3xl font-bold text-on-surface mb-4">Thanh toán thành công!</h2>
        <p className="text-on-surface-variant mb-8 leading-relaxed">
          Cảm ơn bạn đã nâng cấp gói Premium. Toàn bộ các tính năng AI nâng cao và lưu trữ 30 ngày đã được mở khóa.
        </p>
        <button
          onClick={() => navigate("/dashboard")}
          className="px-8 py-3.5 bg-primary text-white font-bold rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-95 focus:outline-none"
        >
          Trở về Bảng điều khiển
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/billing" className="w-10 h-10 rounded-full hover:bg-surface-variant flex items-center justify-center text-on-surface-variant transition-colors">
          <span className="material-symbols-outlined">arrow_back</span>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Nâng cấp Premium</h1>
          <p className="text-sm text-on-surface-variant">Thanh toán an toàn qua mã QR tự động.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Left: Summary */}
        <div>
          <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-6 shadow-sm mb-6">
            <h3 className="font-bold text-on-surface mb-4">Chọn chu kỳ thanh toán</h3>
            <div className="flex bg-surface-variant p-1 rounded-xl mb-6">
              <button
                onClick={() => setBillingCycle("monthly")}
                className={`flex-1 py-2 text-sm font-bold rounded-lg transition-colors focus:outline-none ${billingCycle === "monthly" ? "bg-white text-on-surface shadow-sm" : "text-on-surface-variant hover:text-on-surface"}`}
              >
                Tháng
              </button>
              <button
                onClick={() => setBillingCycle("yearly")}
                className={`flex-1 py-2 text-sm font-bold rounded-lg transition-colors focus:outline-none flex items-center justify-center gap-2 ${billingCycle === "yearly" ? "bg-white text-on-surface shadow-sm" : "text-on-surface-variant hover:text-on-surface"}`}
              >
                Năm <span className="bg-emerald-100 text-emerald-700 text-[10px] px-2 py-0.5 rounded-full">-20%</span>
              </button>
            </div>

            <div className="space-y-3 mb-6 pb-6 border-b border-outline-variant/30">
              <div className="flex justify-between text-sm">
                <span className="text-on-surface-variant">Gói SafeKid Premium</span>
                <span className="font-semibold text-on-surface">99.000đ / tháng</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-on-surface-variant">Chu kỳ</span>
                <span className="font-semibold text-on-surface">{billingCycle === "monthly" ? "1 tháng" : "12 tháng"}</span>
              </div>
              {billingCycle === "yearly" && (
                <div className="flex justify-between text-sm text-emerald-600 font-semibold">
                  <span>Giảm giá (20%)</span>
                  <span>-237.600đ</span>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-on-surface">Tổng cộng</span>
              <span className="text-2xl font-extrabold text-primary">{price.toLocaleString("vi-VN")}đ</span>
            </div>
            <p className="text-right text-xs text-on-surface-variant">Đã bao gồm VAT</p>
          </div>
        </div>

        {/* Right: Payment QR */}
        <div>
          <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-8 shadow-sm flex flex-col items-center text-center">
            <h3 className="font-bold text-on-surface mb-2">Quét mã QR để thanh toán</h3>
            <p className="text-xs text-on-surface-variant mb-6">Mở ứng dụng ngân hàng hoặc MoMo để quét. Hệ thống sẽ tự động xác nhận sau khi chuyển khoản thành công.</p>

            <div className="w-48 h-48 bg-white border-2 border-outline-variant/30 rounded-2xl p-2 mb-6 shadow-inner relative overflow-hidden flex items-center justify-center">
              {/* Mock QR Code */}
              <div className="grid grid-cols-4 grid-rows-4 gap-1 w-full h-full opacity-80">
                {Array.from({ length: 16 }).map((_, i) => (
                  <div key={i} className={`bg-black ${Math.random() > 0.5 ? 'rounded-tl-lg' : ''} ${Math.random() > 0.5 ? 'rounded-br-lg' : ''} ${Math.random() > 0.7 ? 'opacity-0' : ''}`}></div>
                ))}
              </div>
              {/* Overlay scanning line */}
              <div className="absolute top-0 left-0 w-full h-1 bg-emerald-400 shadow-[0_0_10px_2px_#34d399] animate-[slide-up_2s_ease-in-out_infinite_alternate]"></div>
            </div>

            <div className="w-full bg-surface-container-low p-4 rounded-xl border border-outline-variant/20 mb-6">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-on-surface-variant">Ngân hàng:</span>
                <span className="font-bold text-on-surface">Vietcombank</span>
              </div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-on-surface-variant">Số TK:</span>
                <span className="font-bold text-on-surface">1029384756</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-on-surface-variant">Nội dung:</span>
                <span className="font-bold text-primary bg-primary/10 px-2 py-0.5 rounded">SKM 89231</span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-amber-600 text-xs font-semibold bg-amber-50 px-4 py-2 rounded-lg w-full justify-center">
              <span className="material-symbols-outlined text-[16px] animate-spin">sync</span>
              Đang chờ thanh toán...
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
