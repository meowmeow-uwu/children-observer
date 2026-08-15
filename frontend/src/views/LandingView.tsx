import React from "react";
import { Link } from "react-router-dom";

export const LandingView: React.FC = () => {
  return (
    <div className="flex-1">
      {/* Hero Section */}
      <section className="pt-20 pb-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-on-surface mb-6">
          Bảo vệ tương lai của bạn <br className="hidden md:block" />
          <span className="text-primary">với sức mạnh AI</span>
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-on-surface-variant mx-auto mb-10">
          SafeKid Monitor là giải pháp giám sát an toàn thông minh, tự động phát hiện vùng nguy hiểm (ROI), té ngã và bạo lực, cảnh báo tức thời tới điện thoại của bạn.
        </p>
        <div className="flex justify-center gap-4">
          <Link to="/register" className="px-8 py-3.5 text-base font-bold bg-primary text-white rounded-xl shadow-md hover:bg-primary/90 transition-transform active:scale-95 focus:outline-none">
            Bắt đầu miễn phí
          </Link>
          <Link to="/pricing" className="px-8 py-3.5 text-base font-bold bg-surface-container-high text-on-surface hover:bg-surface-container-highest rounded-xl transition-colors focus:outline-none">
            Xem bảng giá
          </Link>
        </div>
      </section>

      {/* ROI Feature Highlight */}
      <section className="py-24 bg-surface-container-low border-y border-outline-variant/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col lg:flex-row items-center gap-12">
          <div className="flex-1 text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-bold mb-4">
              <span className="material-symbols-outlined text-[16px]">detector_status</span>
              Tính năng nổi bật
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-on-surface mb-6">Khoanh vùng nguy hiểm (ROI) linh hoạt</h2>
            <p className="text-lg text-on-surface-variant mb-6 leading-relaxed">
              Dễ dàng vẽ các ranh giới ảo xung quanh khu vực ban công, hồ bơi, bếp hoặc cầu thang trực tiếp trên màn hình camera. AI sẽ tự động kích hoạt cảnh báo nếu trẻ tiến vào vùng cấm.
            </p>
            <ul className="space-y-4">
              <li className="flex items-center gap-3 text-on-surface-variant font-medium">
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                </span>
                Nhận diện chính xác ranh giới đa giác phức tạp.
              </li>
              <li className="flex items-center gap-3 text-on-surface-variant font-medium">
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                </span>
                Cảnh báo ngay lập tức qua Telegram.
              </li>
              <li className="flex items-center gap-3 text-on-surface-variant font-medium">
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                </span>
                Tùy chỉnh độ nhạy AI (Thấp / Trung bình / Cao).
              </li>
            </ul>
          </div>
          <div className="flex-1 w-full">
            <div className="aspect-video bg-black rounded-2xl border border-outline-variant/30 shadow-2xl overflow-hidden relative">
              <img src="/test_video_thumb.jpg" alt="Demo AI Child Observer" className="absolute inset-0 w-full h-full object-cover opacity-50" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="material-symbols-outlined text-[64px] text-white opacity-50">play_circle</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
