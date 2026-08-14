import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export const AddDeviceWizard: React.FC = () => {
  const [step, setStep] = useState(1);
  const navigate = useNavigate();

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
    else navigate("/devices");
  };

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/devices" className="w-10 h-10 rounded-full hover:bg-surface-variant flex items-center justify-center text-on-surface-variant transition-colors">
          <span className="material-symbols-outlined">arrow_back</span>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Thêm Trạm Edge AI (Raspberry Pi)</h1>
          <p className="text-sm text-on-surface-variant">Kết nối thiết bị xử lý trung tâm vào mạng của bạn.</p>
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-8 shadow-sm">
        {/* Stepper Header */}
        <div className="flex items-center justify-between mb-12 relative">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-outline-variant/30 -z-10 rounded-full">
            <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: `${((step - 1) / 3) * 100}%` }}></div>
          </div>

          {[
            { id: 1, label: "Cấp nguồn" },
            { id: 2, label: "Tìm thiết bị" },
            { id: 3, label: "Kết nối Wi-Fi" },
            { id: 4, label: "Hoàn tất" }
          ].map((s) => (
            <div key={s.id} className="flex flex-col items-center gap-2 bg-surface-container-lowest px-2">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors border-2 ${
                step >= s.id ? "bg-primary border-primary text-white" : "bg-surface border-outline-variant/50 text-outline"
              }`}>
                {step > s.id ? <span className="material-symbols-outlined text-[20px]">check</span> : s.id}
              </div>
              <span className={`text-xs font-semibold ${step >= s.id ? "text-primary" : "text-outline"}`}>{s.label}</span>
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="min-h-[300px] flex flex-col items-center justify-center text-center animate-fade-in">
          {step === 1 && (
            <div className="max-w-md w-full">
              <div className="w-24 h-24 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="material-symbols-outlined text-[48px] text-primary">power</span>
              </div>
              <h3 className="text-xl font-bold text-on-surface mb-2">Cắm nguồn thiết bị</h3>
              <p className="text-on-surface-variant mb-6">
                Vui lòng cắm cáp nguồn Type-C vào cổng nguồn của bo mạch Raspberry Pi. Đợi khoảng 1 phút cho đến khi đèn LED xanh lục nhấp nháy chậm.
              </p>
            </div>
          )}

          {step === 2 && (
            <div className="max-w-md w-full">
              <div className="w-24 h-24 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-6 relative">
                <span className="material-symbols-outlined text-[48px] text-blue-500 relative z-10">bluetooth_searching</span>
                <div className="absolute inset-0 border-4 border-blue-500 rounded-full animate-ping opacity-20"></div>
              </div>
              <h3 className="text-xl font-bold text-on-surface mb-2">Đang tìm kiếm...</h3>
              <p className="text-on-surface-variant mb-6">
                Đảm bảo điện thoại/máy tính của bạn đã bật Bluetooth và ở gần thiết bị trong phạm vi 5 mét.
              </p>
              <div className="bg-surface-variant/50 border border-outline-variant/30 rounded-xl p-4 flex items-center gap-4 text-left cursor-pointer hover:bg-surface-variant transition-colors group">
                <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center text-primary shadow-sm group-hover:scale-105 transition-transform">
                  <span className="material-symbols-outlined">developer_board</span>
                </div>
                <div>
                  <h4 className="font-bold text-on-surface text-sm">SafeKid_Edge_A1B2</h4>
                  <p className="text-xs text-emerald-600 font-medium">Sẵn sàng ghép nối</p>
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="max-w-md w-full text-left">
              <div className="flex items-center gap-3 mb-6 justify-center">
                <span className="material-symbols-outlined text-[32px] text-primary">wifi</span>
                <h3 className="text-xl font-bold text-on-surface">Cài đặt mạng Wi-Fi</h3>
              </div>
              <p className="text-on-surface-variant text-sm text-center mb-6">
                Chọn mạng Wi-Fi (2.4GHz) tại nhà bạn để thiết bị có thể kết nối Internet.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-on-surface mb-1.5">Tên mạng (SSID)</label>
                  <select className="w-full h-12 px-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none text-sm text-on-surface">
                    <option>Home_Network_2.4G</option>
                    <option>Viettel_A823</option>
                    <option>Mạng khác...</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-on-surface mb-1.5">Mật khẩu Wi-Fi</label>
                  <div className="relative">
                    <input type="password" placeholder="Nhập mật khẩu" className="w-full h-12 px-4 bg-surface rounded-xl border border-outline-variant/40 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none text-sm text-on-surface" />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant cursor-pointer">visibility_off</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="max-w-md w-full">
              <div className="w-24 h-24 bg-emerald-500 text-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-emerald-500/30 animate-scale-up">
                <span className="material-symbols-outlined text-[48px]">verified</span>
              </div>
              <h3 className="text-xl font-bold text-on-surface mb-2">Cài đặt hoàn tất!</h3>
              <p className="text-on-surface-variant mb-6">
                Thiết bị Edge AI đã được liên kết với tài khoản của bạn và đang hoạt động. Bạn có thể bắt đầu thêm Camera ngay bây giờ.
              </p>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="mt-8 pt-6 border-t border-outline-variant/20 flex justify-between">
          <button
            onClick={() => step > 1 ? setStep(step - 1) : navigate(-1)}
            className="px-6 py-2.5 rounded-xl font-bold text-on-surface-variant hover:bg-surface-variant transition-colors focus:outline-none"
          >
            {step === 1 ? "Hủy bỏ" : "Quay lại"}
          </button>
          <button
            onClick={handleNext}
            className="px-8 py-2.5 rounded-xl font-bold bg-primary text-white hover:bg-primary/90 transition-transform active:scale-[0.98] shadow-md flex items-center gap-2 focus:outline-none"
          >
            {step === 4 ? "Đến quản lý thiết bị" : "Tiếp tục"}
            {step < 4 && <span className="material-symbols-outlined text-[18px]">arrow_forward</span>}
          </button>
        </div>
      </div>
    </div>
  );
};
