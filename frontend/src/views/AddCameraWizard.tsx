import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export const AddCameraWizard: React.FC = () => {
  const [method, setMethod] = useState<"auto" | "manual" | null>(null);
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/cameras" className="w-10 h-10 rounded-full hover:bg-surface-variant flex items-center justify-center text-on-surface-variant transition-colors">
          <span className="material-symbols-outlined">arrow_back</span>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Thêm Camera mới</h1>
          <p className="text-sm text-on-surface-variant">Kết nối IP Camera của bạn vào hệ thống giám sát AI.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Method: Auto Scan */}
        <div
          onClick={() => setMethod("auto")}
          className={`bg-surface-container-lowest border-2 rounded-3xl p-8 cursor-pointer transition-all hover:shadow-lg relative overflow-hidden ${
            method === "auto" ? "border-primary shadow-md" : "border-outline-variant/30 hover:border-primary/50"
          }`}
        >
          {method === "auto" && (
            <div className="absolute top-4 right-4 text-primary">
              <span className="material-symbols-outlined text-[24px]">check_circle</span>
            </div>
          )}
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 transition-colors ${
            method === "auto" ? "bg-primary text-white" : "bg-primary/10 text-primary"
          }`}>
            <span className="material-symbols-outlined text-[32px]">radar</span>
          </div>
          <h3 className="text-xl font-bold text-on-surface mb-2">Quét tự động (ONVIF)</h3>
          <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
            Hệ thống sẽ tự động quét mạng LAN để tìm kiếm các Camera tương thích chuẩn ONVIF. Khuyên dùng cho người không rành kỹ thuật.
          </p>

          {method === "auto" && (
            <div className="animate-fade-in bg-surface-container-low rounded-xl p-4 mt-6">
              <button className="w-full py-3 bg-primary text-white font-bold rounded-lg shadow-sm hover:bg-primary/90 transition-transform active:scale-95 flex items-center justify-center gap-2">
                <span className="material-symbols-outlined">search</span>
                Bắt đầu quét mạng
              </button>
            </div>
          )}
        </div>

        {/* Method: Manual Setup */}
        <div
          onClick={() => setMethod("manual")}
          className={`bg-surface-container-lowest border-2 rounded-3xl p-8 cursor-pointer transition-all hover:shadow-lg relative overflow-hidden ${
            method === "manual" ? "border-primary shadow-md" : "border-outline-variant/30 hover:border-primary/50"
          }`}
        >
          {method === "manual" && (
            <div className="absolute top-4 right-4 text-primary">
              <span className="material-symbols-outlined text-[24px]">check_circle</span>
            </div>
          )}
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 transition-colors ${
            method === "manual" ? "bg-primary text-white" : "bg-secondary/10 text-secondary"
          }`}>
            <span className="material-symbols-outlined text-[32px]">settings_ethernet</span>
          </div>
          <h3 className="text-xl font-bold text-on-surface mb-2">Thêm thủ công (RTSP)</h3>
          <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
            Nhập trực tiếp địa chỉ IP, User/Pass và hãng Camera để hệ thống tự động biên dịch thành chuỗi RTSP chuẩn.
          </p>

          {method === "manual" && (
            <div className="animate-fade-in space-y-4 mt-6">
              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Địa chỉ IP / Tên miền</label>
                <input type="text" placeholder="VD: 192.168.1.100" className="w-full h-10 px-3 bg-surface rounded-lg border border-outline-variant/40 focus:border-primary text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-on-surface mb-1">Tài khoản</label>
                  <input type="text" placeholder="admin" className="w-full h-10 px-3 bg-surface rounded-lg border border-outline-variant/40 focus:border-primary text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface mb-1">Mật khẩu</label>
                  <input type="password" placeholder="***" className="w-full h-10 px-3 bg-surface rounded-lg border border-outline-variant/40 focus:border-primary text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface mb-1">Hãng Camera (Tùy chọn)</label>
                <select className="w-full h-10 px-3 bg-surface rounded-lg border border-outline-variant/40 focus:border-primary text-sm">
                  <option>Tự động phát hiện (Auto)</option>
                  <option>Hikvision</option>
                  <option>Dahua</option>
                  <option>Tapo</option>
                  <option>Ezviz</option>
                </select>
              </div>
              <button onClick={() => navigate("/cameras")} className="w-full py-3 bg-primary text-white font-bold rounded-lg shadow-sm hover:bg-primary/90 mt-2">
                Kết nối Camera
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
