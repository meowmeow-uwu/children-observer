import React from "react";
import { Link } from "react-router-dom";

export const SubscriptionView: React.FC = () => {
  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-on-surface">Quản lý Gói dịch vụ</h2>
        <p className="text-sm text-on-surface-variant mt-1">Nâng cấp để mở khóa toàn bộ tính năng AI nâng cao.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Current Plan */}
        <div className="bg-surface-container-lowest border-2 border-outline-variant/30 rounded-3xl p-8 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-on-surface">Gói hiện tại</h3>
            <span className="px-3 py-1 bg-surface-variant text-on-surface-variant text-xs font-bold rounded-full uppercase tracking-wider">Miễn phí</span>
          </div>

          <div className="mb-8">
            <span className="text-4xl font-extrabold text-on-surface">0đ</span>
            <span className="text-on-surface-variant font-medium">/tháng</span>
          </div>

          <div className="space-y-4 mb-8">
            <div className="flex justify-between text-sm">
              <span className="text-on-surface-variant">Thiết bị đang dùng</span>
              <span className="font-bold text-on-surface">1/1 Pi, 1/1 Cam</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-on-surface-variant">Lưu trữ Cloud (3 ngày)</span>
              <span className="font-bold text-on-surface">450MB / 1GB</span>
            </div>
            {/* Storage Progress bar */}
            <div className="w-full h-2 bg-surface-variant rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full" style={{ width: '45%' }}></div>
            </div>
          </div>
        </div>

        {/* Upgrade Ad */}
        <div className="bg-primary border-2 border-primary rounded-3xl p-8 shadow-lg text-white flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white opacity-5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4 group-hover:scale-110 transition-transform duration-700"></div>

          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-white text-[24px]">verified</span>
              <h3 className="text-xl font-bold text-white">Nâng cấp Premium</h3>
            </div>
            <p className="text-primary-fixed text-sm mb-6 leading-relaxed">
              Phát hiện té ngã, bạo lực. Lưu trữ video sự cố 30 ngày. Hỗ trợ 5 thiết bị Pi & 16 Camera. Chia sẻ cho 5 người thân.
            </p>
          </div>

          <Link to="/billing/checkout" className="w-full py-3.5 bg-white text-primary text-sm font-bold rounded-xl shadow-md hover:bg-surface-container-low transition-colors text-center relative z-10 focus:outline-none">
            Nâng cấp ngay - Chỉ 99k/tháng
          </Link>
        </div>
      </div>

      {/* Invoice History Link */}
      <div className="mt-8 pt-6 border-t border-outline-variant/30 flex justify-between items-center">
        <div>
          <h4 className="font-bold text-on-surface">Lịch sử thanh toán</h4>
          <p className="text-xs text-on-surface-variant">Xem và tải xuống hóa đơn điện tử.</p>
        </div>
        <Link to="/billing/invoices" className="px-4 py-2 bg-surface-container-low text-on-surface-variant font-bold text-sm rounded-lg hover:bg-surface-variant transition-colors focus:outline-none">
          Xem lịch sử
        </Link>
      </div>
    </div>
  );
};
