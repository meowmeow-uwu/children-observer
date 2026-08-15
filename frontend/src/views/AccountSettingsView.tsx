import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNotificationStore } from "../store/notificationStore";

export const AccountSettingsView: React.FC = () => {
  const { user, updateProfile } = useAuth();
  const addNotification = useNotificationStore((state) => state.addNotification);

  const [fullName, setFullName] = useState(user?.name || "");
  const [telegramChatId, setTelegramChatId] = useState(user?.telegramChatId?.toString() || "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const parsedChatId = telegramChatId.trim() !== "" ? parseInt(telegramChatId, 10) : null;
    
    if (telegramChatId.trim() !== "" && isNaN(parsedChatId as number)) {
      addNotification({ title: "Lỗi hợp lệ", message: "Telegram Chat ID phải là một số hợp lệ", type: "danger" });
      setIsSubmitting(false);
      return;
    }

    const success = await updateProfile({
      full_name: fullName,
      telegram_chat_id: parsedChatId,
    });

    if (success) {
      addNotification({ title: "Thành công", message: "Đã lưu thông tin tài khoản thành công", type: "success" });
    } else {
      addNotification({ title: "Lỗi", message: "Lỗi khi lưu thông tin. Vui lòng thử lại.", type: "danger" });
    }
    
    setIsSubmitting(false);
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-on-surface">Cài đặt tài khoản</h1>
        <p className="text-on-surface-variant mt-2">
          Quản lý thông tin cá nhân và cấu hình nhận thông báo qua ứng dụng thứ ba.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Cột trái: Avatar & Info cơ bản */}
        <div className="col-span-1">
          <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/30 p-6 shadow-sm flex flex-col items-center">
            <div className="relative group mb-4">
              <div className="w-24 h-24 rounded-full bg-primary/10 overflow-hidden border-4 border-surface shadow-md">
                {user?.avatarUrl ? (
                  <img src={user.avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-primary text-3xl font-bold">
                    {user?.name?.[0]?.toUpperCase() || "U"}
                  </div>
                )}
              </div>
              <button className="absolute bottom-0 right-0 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center shadow-lg hover:bg-primary/90 transition-colors">
                <span className="material-symbols-outlined text-[18px]">edit</span>
              </button>
            </div>
            <h3 className="text-lg font-bold text-on-surface">{user?.name}</h3>
            <p className="text-sm text-on-surface-variant bg-surface-variant/50 px-3 py-1 rounded-full mt-2 inline-flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
              {user?.role === "parent" ? "Phụ huynh" : "Người dùng"}
            </p>
          </div>
        </div>

        {/* Cột phải: Form */}
        <div className="col-span-1 md:col-span-2">
          <form onSubmit={handleSave} className="bg-surface-container-lowest rounded-2xl border border-outline-variant/30 shadow-sm overflow-hidden">
            <div className="p-6 md:p-8 space-y-6">
              
              {/* Thông tin cơ bản */}
              <div>
                <h4 className="text-lg font-semibold text-on-surface mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">person</span>
                  Thông tin cá nhân
                </h4>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-on-surface-variant mb-1.5">
                      Địa chỉ Email (Đăng nhập)
                    </label>
                    <input
                      type="email"
                      value={user?.email || ""}
                      disabled
                      className="w-full h-12 px-4 rounded-xl border border-outline-variant/50 bg-surface-variant/30 text-on-surface-variant cursor-not-allowed focus:outline-none"
                    />
                    <p className="text-xs text-on-surface-variant mt-1.5">Không thể thay đổi email đã đăng ký.</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-on-surface-variant mb-1.5">
                      Họ và tên hiển thị
                    </label>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full h-12 px-4 rounded-xl border border-outline-variant focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all text-on-surface"
                      placeholder="Nhập họ và tên..."
                      required
                    />
                  </div>
                </div>
              </div>

              <hr className="border-outline-variant/20" />

              {/* Telegram Linking */}
              <div>
                <h4 className="text-lg font-semibold text-on-surface mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[#0088cc]">send</span>
                  Liên kết Telegram
                </h4>
                <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 mb-5 flex gap-4">
                  <div className="text-blue-500 mt-0.5">
                    <span className="material-symbols-outlined">info</span>
                  </div>
                  <div>
                    <p className="text-sm text-on-surface font-medium mb-1">
                      Nhận thông báo sự cố tức thì qua Telegram
                    </p>
                    <p className="text-xs text-on-surface-variant leading-relaxed mb-3">
                      Lấy Chat ID bằng cách nhắn tin cho bot <a href="https://t.me/RawDataBot" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline font-semibold">@RawDataBot</a> hoặc bot của hệ thống. Dán dải số ID (ví dụ: 123456789) vào ô bên dưới.
                    </p>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-on-surface-variant mb-1.5">
                    Telegram Chat ID
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={telegramChatId}
                      onChange={(e) => setTelegramChatId(e.target.value)}
                      className="w-full h-12 pl-12 pr-4 rounded-xl border border-outline-variant focus:border-[#0088cc] focus:ring-2 focus:ring-[#0088cc]/20 outline-none transition-all text-on-surface"
                      placeholder="VD: 541234567"
                    />
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline-variant">
                      tag
                    </span>
                  </div>
                </div>
              </div>

            </div>
            
            {/* Footer / Submit */}
            <div className="bg-surface-variant/30 px-6 py-4 flex items-center justify-end gap-3 border-t border-outline-variant/30">
              <button 
                type="button" 
                className="px-5 py-2.5 rounded-xl font-medium text-on-surface-variant hover:bg-surface-variant transition-colors"
                onClick={() => {
                  setFullName(user?.name || "");
                  setTelegramChatId(user?.telegramChatId?.toString() || "");
                }}
              >
                Hủy bỏ
              </button>
              <button 
                type="submit" 
                disabled={isSubmitting}
                className="px-6 py-2.5 rounded-xl font-medium bg-primary text-white hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    Đang lưu...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[20px]">save</span>
                    Lưu thay đổi
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
