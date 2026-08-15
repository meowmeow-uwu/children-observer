import React from "react";
import { Link } from "react-router-dom";

export const PricingView: React.FC = () => {
  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h1 className="text-4xl font-bold text-on-surface mb-4">Gói dịch vụ linh hoạt</h1>
        <p className="text-lg text-on-surface-variant">Chọn gói phù hợp với nhu cầu giám sát gia đình của bạn. Nâng cấp hoặc hủy bất kỳ lúc nào.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
        {/* Free Tier */}
        <div className="bg-surface-container-lowest rounded-3xl p-8 border border-outline-variant/30 flex flex-col hover:shadow-md transition-shadow">
          <div className="mb-6">
            <h3 className="text-2xl font-bold text-on-surface mb-2">Miễn phí</h3>
            <p className="text-on-surface-variant text-sm h-10">Giải pháp cơ bản cho một phòng với 1 camera.</p>
          </div>
          <div className="mb-8">
            <span className="text-4xl font-extrabold text-on-surface">0đ</span>
            <span className="text-on-surface-variant font-medium">/tháng</span>
          </div>

          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-emerald-500 text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">1 Thiết bị Raspberry Pi & 1 Camera</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-emerald-500 text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Cảnh báo Xâm nhập vùng cấm (ROI)</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-emerald-500 text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Lưu lịch sử cảnh báo 3 ngày</span>
            </li>
            <li className="flex items-start gap-3 opacity-50">
              <span className="material-symbols-outlined text-outline text-[20px]">cancel</span>
              <span className="text-sm font-medium text-on-surface-variant line-through">Phát hiện Té ngã & Bạo lực</span>
            </li>
            <li className="flex items-start gap-3 opacity-50">
              <span className="material-symbols-outlined text-outline text-[20px]">cancel</span>
              <span className="text-sm font-medium text-on-surface-variant line-through">Chia sẻ quyền xem cho người thân</span>
            </li>
          </ul>

          <Link to="/register" className="w-full py-3.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-sm font-bold rounded-xl transition-colors text-center focus:outline-none">
            Bắt đầu Miễn phí
          </Link>
        </div>

        {/* Premium Tier */}
        <div className="bg-surface-container-lowest rounded-3xl p-8 border-2 border-primary relative flex flex-col shadow-xl animate-scale-up">
          <div className="absolute top-0 right-8 transform -translate-y-1/2">
            <span className="bg-primary text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-sm">Khuyên dùng</span>
          </div>
          <div className="mb-6">
            <h3 className="text-2xl font-bold text-primary mb-2">Premium</h3>
            <p className="text-on-surface-variant text-sm h-10">Bảo vệ toàn diện ngôi nhà với AI nâng cao.</p>
          </div>
          <div className="mb-8">
            <span className="text-4xl font-extrabold text-on-surface">99.000đ</span>
            <span className="text-on-surface-variant font-medium">/tháng</span>
          </div>

          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Tối đa 5 Thiết bị Pi & 16 Camera</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Full AI: Xâm nhập ROI, Té ngã, Bạo lực</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Lưu trữ Video sự cố 30 ngày trên Cloud</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Chia sẻ quyền cho tối đa 5 người thân</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
              <span className="text-sm font-medium text-on-surface">Ưu tiên băng thông TURN Server chống nghẽn</span>
            </li>
          </ul>

          <Link to="/register?plan=premium" className="w-full py-3.5 bg-primary hover:bg-primary/90 text-white text-sm font-bold rounded-xl transition-transform active:scale-95 shadow-md text-center focus:outline-none">
            Nâng cấp Premium
          </Link>
        </div>
      </div>
    </div>
  );
};
