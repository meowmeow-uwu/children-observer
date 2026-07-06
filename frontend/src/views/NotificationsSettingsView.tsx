import React, { useState } from "react";
import { useToast } from "../components/Toast";
import { useBrowserNotification } from "../hooks/useBrowserNotification";
import { useNotificationStore } from "../store/notificationStore";

export const NotificationsSettingsView: React.FC = () => {
  const { showToast } = useToast();
  const { permission, requestPermission, showNotification } = useBrowserNotification();
  const { addNotification } = useNotificationStore();

  const [channels, setChannels] = useState({
    in_app: true,
    web_push: true,
    zalo: true,
    email: false,
    sms: false
  });

  const [emergencyContact, setEmergencyContact] = useState({
    name: "Trần Thị B (Mẹ)",
    phone: "0901234567"
  });

  const [silentHours, setSilentHours] = useState({
    enabled: false,
    start: "22:00",
    end: "06:00"
  });

  const [priority, setPriority] = useState<"all" | "danger">("all");
  const [isSoundEnabled, setIsSoundEnabled] = useState(true);

  const playAlertSound = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, ctx.currentTime); // 880 Hz beep sound
      
      gain.gain.setValueAtTime(0.15, ctx.currentTime); // Volume
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3); // Fade out
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch {
      // Audio context blocked or unsupported
    }
  };

  const handleRequestPermission = async () => {
    const result = await requestPermission();
    if (result === "granted") {
      showToast("Đã cho phép thông báo trên trình duyệt thành công!", "success");
      showNotification("SafeKid Monitor ⚠️", {
        body: "Đã bật quyền nhận thông báo an toàn thành công!"
      });
    } else if (result === "denied") {
      showToast("Quyền thông báo bị từ chối.", "error");
    }
  };

  const handleSendTestNotification = () => {
    // 1. Dispatch in-app notification
    addNotification({
      title: "Cảnh báo xâm phạm ranh giới",
      message: "Bé Vy được phát hiện lại gần rào chắn Ban công.",
      type: "danger",
      relatedAlertId: "alert_002"
    });

    // 2. Play Audio if enabled
    if (isSoundEnabled) {
      playAlertSound();
    }

    // 3. Dispatch system browser popups
    if (permission === "granted") {
      showNotification("Cảnh báo vùng nguy hiểm! ⚠️", {
        body: "Bé Vy đang tiếp cận rào chắn Ban công.",
        tag: "safekid-test-alert",
        requireInteraction: true
      });
    }

    showToast("Đã gửi cảnh báo thử nghiệm (in-app và browser notification)!", "success");
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    showToast("Cấu hình cài đặt thông báo đã được lưu thành công!", "success");
  };

  const toggleChannel = (key: keyof typeof channels) => {
    setChannels((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Cài đặt kênh thông báo</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Lựa chọn cách thức nhận thông báo khẩn cấp và thiết lập thông tin người giám hộ liên hệ.
          </p>
        </div>

        {/* Demo Dispatch Action */}
        <button
          type="button"
          onClick={handleSendTestNotification}
          className="py-2.5 px-4 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none shrink-0 shadow-md"
        >
          <span className="material-symbols-outlined text-[18px]">cell_tower</span>
          Gửi cảnh báo thử (Demo Alert)
        </button>
      </div>

      <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Notification Channels & Priority */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Browser Notification Permissions UI */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Thông báo trên trình duyệt</h3>
            <p className="text-xs text-on-surface-variant">
              Nhận cảnh báo hệ thống ngay lập tức trên màn hình thiết bị kể cả khi đang thu nhỏ ứng dụng.
            </p>

            <div className="pt-2">
              {permission === "unsupported" && (
                <div className="p-4 bg-surface-container-low border border-outline-variant/20 rounded-xl text-xs text-outline flex items-start gap-2">
                  <span className="material-symbols-outlined text-outline text-[20px]">error</span>
                  <div>
                    <span className="font-bold block text-on-surface">Trình duyệt không hỗ trợ</span>
                    <span className="text-[10px] block mt-0.5">Vui lòng sử dụng các trình duyệt hiện đại như Chrome, Safari hoặc Edge.</span>
                  </div>
                </div>
              )}

              {permission === "granted" && (
                <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl text-xs text-emerald-600 flex items-start gap-2.5">
                  <span className="material-symbols-outlined text-[20px]">verified</span>
                  <div>
                    <span className="font-bold block">Đã cho phép thông báo</span>
                    <span className="text-[10px] text-on-surface-variant block mt-0.5">Ứng dụng đã được cấp quyền hiển thị cảnh báo đẩy trên hệ thống.</span>
                  </div>
                </div>
              )}

              {permission === "denied" && (
                <div className="p-4 bg-error/5 border border-error/20 rounded-xl text-xs text-error flex items-start gap-2.5">
                  <span className="material-symbols-outlined text-[20px]">block</span>
                  <div className="space-y-1">
                    <span className="font-bold block">Đã bị chặn thông báo</span>
                    <p className="text-[10px] text-on-surface-variant leading-relaxed">
                      Thông báo đã bị chặn trong trình duyệt. Vui lòng mở biểu tượng ổ khóa bên cạnh thanh địa chỉ URL để cấp lại quyền nhận tin.
                    </p>
                  </div>
                </div>
              )}

              {permission === "default" && (
                <div className="p-4 bg-surface-container-low border border-outline-variant/20 rounded-xl flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                  <div className="text-xs">
                    <span className="font-bold text-on-surface block">Chưa cấp quyền thông báo</span>
                    <span className="text-[10px] text-on-surface-variant block mt-0.5">Bấm nút cấp quyền bên cạnh để nhận tin khẩn AI của bé.</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRequestPermission}
                    className="py-2 px-4 bg-primary text-white hover:bg-primary/95 text-xs font-bold rounded-lg transition-colors focus:outline-none shadow-sm align-middle shrink-0"
                  >
                    Cho phép thông báo
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* Notification Channels */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Kênh truyền tải thông báo</h3>
            
            <div className="space-y-4">
              {/* In App */}
              <div className="flex justify-between items-center p-3 bg-surface-container-low rounded-xl">
                <div>
                  <h4 className="font-bold text-xs text-on-surface">Thông báo trong ứng dụng (In-app)</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Hiện thông báo đẩy tức thời khi ứng dụng đang mở</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleChannel("in_app")}
                  className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                    channels.in_app ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
                </button>
              </div>

              {/* Web Push */}
              <div className="flex justify-between items-center p-3 bg-surface-container-low rounded-xl">
                <div>
                  <h4 className="font-bold text-xs text-on-surface">Thông báo trình duyệt (Web Push)</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Hiện thông báo trên màn hình khóa điện thoại/máy tính</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleChannel("web_push")}
                  className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                    channels.web_push ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
                </button>
              </div>

              {/* Zalo */}
              <div className="flex justify-between items-center p-3 bg-surface-container-low rounded-xl">
                <div>
                  <h4 className="font-bold text-xs text-on-surface font-semibold text-[#0068FF] flex items-center gap-1">
                    Tin nhắn Zalo OT
                    <span className="px-1.5 py-0.5 bg-[#0068FF]/10 text-[#0068FF] text-[8px] font-bold rounded">Recommended</span>
                  </h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Gửi tin nhắn ảnh kèm nút bấm xử lý qua Official Account của gia đình</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleChannel("zalo")}
                  className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                    channels.zalo ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
                </button>
              </div>

              {/* Email */}
              <div className="flex justify-between items-center p-3 bg-surface-container-low rounded-xl">
                <div>
                  <h4 className="font-bold text-xs text-on-surface">Thư điện tử (Email)</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Gửi email tổng hợp báo cáo sự cố an toàn định kỳ</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleChannel("email")}
                  className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                    channels.email ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
                </button>
              </div>

              {/* SMS */}
              <div className="flex justify-between items-center p-3 bg-surface-container-low rounded-xl">
                <div>
                  <h4 className="font-bold text-xs text-on-surface">Mạng viễn thông (SMS)</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Gửi tin nhắn văn bản khi không có kết nối internet mạng</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleChannel("sms")}
                  className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                    channels.sms ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                  }`}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
                </button>
              </div>

            </div>
          </div>

          {/* Alert priority settings */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Độ ưu tiên gửi cảnh báo</h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                onClick={() => setPriority("all")}
                className={`p-4 rounded-xl border cursor-pointer flex items-start gap-3 transition-all ${
                  priority === "all"
                    ? "bg-primary/5 border-primary text-primary"
                    : "bg-surface-container-low border-outline-variant/20 hover:border-outline-variant"
                }`}
              >
                <input
                  type="radio"
                  name="priority"
                  checked={priority === "all"}
                  onChange={() => {}}
                  className="mt-1"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Gửi tất cả cảnh báo</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Thông báo mọi chuyển động xâm phạm vùng nguy hiểm, kể cả cảnh báo nhẹ.</span>
                </div>
              </label>

              <label
                onClick={() => setPriority("danger")}
                className={`p-4 rounded-xl border cursor-pointer flex items-start gap-3 transition-all ${
                  priority === "danger"
                    ? "bg-red-500/5 border-error text-error"
                    : "bg-surface-container-low border-outline-variant/20 hover:border-outline-variant"
                }`}
              >
                <input
                  type="radio"
                  name="priority"
                  checked={priority === "danger"}
                  onChange={() => {}}
                  className="mt-1"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Chỉ gửi nguy cấp (Danger)</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Chỉ thông báo khi phát hiện trẻ leo trèo khu vực có rủi ro chấn thương nặng.</span>
                </div>
              </label>
            </div>
          </div>

        </div>

        {/* Right Column: Emergency Contacts & Silent Hours */}
        <div className="space-y-6">
          
          {/* Alarm sound demo trigger */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-on-surface text-base">Âm thanh cảnh báo</h3>
              <button
                type="button"
                onClick={() => setIsSoundEnabled(!isSoundEnabled)}
                className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                  isSoundEnabled ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                }`}
              >
                <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
              </button>
            </div>

            <p className="text-[10px] text-on-surface-variant leading-relaxed">
              Phát âm thanh bíp lớn trên trình duyệt khi phát hiện hành vi nguy cấp của trẻ để thu hút sự chú ý.
            </p>

            <button
              type="button"
              onClick={playAlertSound}
              disabled={!isSoundEnabled}
              className="w-full py-2.5 rounded-xl border border-outline-variant bg-surface-container-low hover:bg-surface-container-high transition-all text-xs font-bold text-on-surface flex items-center justify-center gap-1.5 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[18px]">volume_up</span>
              Phát thử âm thanh
            </button>
          </div>

          {/* Emergency Contacts */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Liên hệ khẩn cấp</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Tên người nhận cuộc gọi:</label>
                <input
                  type="text"
                  value={emergencyContact.name}
                  onChange={(e) => setEmergencyContact(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full p-3 border border-outline-variant rounded-xl text-xs bg-surface-container-low focus:ring-1 focus:ring-primary focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Số điện thoại liên hệ:</label>
                <input
                  type="text"
                  value={emergencyContact.phone}
                  onChange={(e) => setEmergencyContact(prev => ({ ...prev, phone: e.target.value }))}
                  className="w-full p-3 border border-outline-variant rounded-xl text-xs bg-surface-container-low focus:ring-1 focus:ring-primary focus:outline-none"
                  required
                />
              </div>
            </div>
          </div>

          {/* Silent Hours settings */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-on-surface text-base">Khung giờ yên lặng</h3>
              <button
                type="button"
                onClick={() => setSilentHours(prev => ({ ...prev, enabled: !prev.enabled }))}
                className={`w-10 h-6 rounded-full p-0.5 transition-colors focus:outline-none flex items-center ${
                  silentHours.enabled ? "bg-primary justify-end" : "bg-outline-variant justify-start"
                }`}
              >
                <span className="w-5 h-5 rounded-full bg-white shadow-sm"></span>
              </button>
            </div>

            {silentHours.enabled && (
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-[10px] font-semibold text-on-surface-variant mb-1">Bắt đầu:</label>
                  <input
                    type="time"
                    value={silentHours.start}
                    onChange={(e) => setSilentHours(prev => ({ ...prev, start: e.target.value }))}
                    className="w-full p-2.5 border border-outline-variant rounded-xl text-xs bg-surface-container-low focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-on-surface-variant mb-1">Kết thúc:</label>
                  <input
                    type="time"
                    value={silentHours.end}
                    onChange={(e) => setSilentHours(prev => ({ ...prev, end: e.target.value }))}
                    className="w-full p-2.5 border border-outline-variant rounded-xl text-xs bg-surface-container-low focus:outline-none"
                  />
                </div>
              </div>
            )}
            
            <p className="text-[10px] text-on-surface-variant leading-relaxed">
              * Khi bật khung giờ yên lặng, các thông báo không khẩn cấp sẽ bị giữ lại và chỉ gửi báo cáo vào buổi sáng.
            </p>
          </div>

          {/* Submit Action */}
          <button
            type="submit"
            className="w-full py-3 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl transition-all shadow-md focus:outline-none"
          >
            Lưu tất cả cài đặt
          </button>
        </div>

      </form>
    </div>
  );
};
export default NotificationsSettingsView;
