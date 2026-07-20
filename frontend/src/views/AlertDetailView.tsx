import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAlertStore } from "../store/alertStore";
import { StatusBadge } from "../components/StatusBadge";
import { SecureImage } from "../components/SecureImage";
import { useToast } from "../components/Toast";

export const AlertDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { alerts, updateAlertStatus } = useAlertStore();

  const al = alerts.find((a) => a.id === id);

  const [falseAlarmReasonInput, setFalseAlarmReasonInput] = useState("");
  const [showFalseAlarmModal, setShowFalseAlarmModal] = useState(false);

  if (!al) {
    return (
      <div className="p-6">
        <div className="text-center p-8 bg-error-container/20 border border-error/20 rounded-2xl max-w-md mx-auto my-8">
          <span className="material-symbols-outlined text-error text-[48px] mb-2">warning</span>
          <h3 className="font-bold text-on-error-container">Không tìm thấy cảnh báo</h3>
          <p className="text-xs text-error mt-1">Sự kiện cảnh báo này có thể đã bị xóa hoặc không tồn tại.</p>
          <button
            onClick={() => navigate("/alerts")}
            className="mt-6 py-2 px-4 bg-error text-white font-bold rounded-lg text-xs"
          >
            Quay lại lịch sử
          </button>
        </div>
      </div>
    );
  }

  const handleResolve = () => {
    updateAlertStatus(al.id, "resolved", {
      resolvedAt: new Date().toISOString(),
      resolvedBy: "Nguyễn Văn A",
      notes: "Đã xác nhận an toàn tại màn hình chi tiết"
    });
    showToast("Đã đánh dấu cảnh báo là đã xử lý!", "success");
  };

  const handleFalseAlarmSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateAlertStatus(al.id, "false_alarm", {
      checkedBy: "Nguyễn Văn A",
      falseAlarmReason: falseAlarmReasonInput || "Gia đình sinh hoạt bình thường"
    });
    setShowFalseAlarmModal(false);
    showToast("Cảnh báo được gán nhãn báo nhầm thành công!", "info");
  };

  const triggerCallSimulate = () => {
    showToast("Đang thực hiện cuộc gọi khẩn cấp tới mẹ bé (090xxxxxxx)...", "info");
  };

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case "in_app": return "smartphone";
      case "web_push": return "notifications_active";
      case "zalo": return "chat";
      case "email": return "mail";
      case "sms": return "sms";
      default: return "send";
    }
  };

  const getChannelLabel = (channel: string) => {
    switch (channel) {
      case "in_app": return "Thông báo trong app";
      case "web_push": return "Thông báo đẩy web";
      case "zalo": return "Tin nhắn Zalo";
      case "email": return "Email báo cáo";
      case "sms": return "Tin nhắn SMS";
      default: return channel;
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      
      {/* Title & Back button */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/alerts")}
          className="w-10 h-10 rounded-full bg-surface-container-low hover:bg-surface-container-high transition-all flex items-center justify-center text-on-surface focus:outline-none"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
        </button>
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Chi tiết cảnh báo an toàn</h2>
          <p className="text-xs md:text-sm text-on-surface-variant mt-0.5">
            Mã định danh: <strong className="font-mono text-on-surface">{al.id}</strong>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Huge Alert Snapshot Image */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-md">
            
            {/* Snapshot Screen */}
            <div className="w-full relative aspect-video bg-black flex items-center justify-center">
              <SecureImage src={al.snapshotUrl} className="w-full h-full object-contain" />
              
              {/* Corner status badges */}
              <div className="absolute top-4 left-4 flex gap-2">
                <span className={`px-2.5 py-1 text-xs font-bold text-white rounded-md uppercase ${al.severity === "danger" ? "bg-red-600 animate-pulse" : al.severity === "warning" ? "bg-amber-500" : "bg-blue-500"}`}>
                  {al.severity === "danger" ? "🚨 Nguy cấp" : al.severity === "warning" ? "⚠️ Cảnh báo" : "ℹ️ Tin tức"}
                </span>
                <span className="px-2.5 py-1 bg-black/60 text-white rounded-md text-xs font-semibold">
                  Độ tin cậy: {Math.round(al.confidence * 100)}%
                </span>
              </div>
            </div>

            {/* Snapshot meta bar */}
            <div className="p-4 md:p-6 space-y-4">
              <div>
                <h3 className="font-bold text-lg md:text-xl text-on-surface leading-tight">{al.title}</h3>
                <p className="text-xs text-on-surface-variant mt-1.5">
                  Phát hiện lúc: <strong className="text-on-surface">{new Date(al.createdAt).toLocaleString("vi-VN")}</strong>
                </p>
              </div>
              
              <div className="flex flex-wrap gap-2 pt-2 border-t border-outline-variant/20">
                <button
                  onClick={() => navigate(`/cameras/${al.cameraId}`)}
                  className="py-2.5 px-4 text-xs font-bold bg-primary text-white hover:bg-primary/95 rounded-xl transition-all flex items-center gap-1.5 focus:outline-none"
                >
                  <span className="material-symbols-outlined text-[18px]">videocam</span>
                  Kiểm tra camera trực tiếp
                </button>
                <button
                  onClick={triggerCallSimulate}
                  className="py-2.5 px-4 text-xs font-bold bg-error text-white hover:bg-error/95 rounded-xl transition-all flex items-center gap-1.5 focus:outline-none"
                >
                  <span className="material-symbols-outlined text-[18px]">call</span>
                  Liên hệ khẩn cấp
                </button>
              </div>
            </div>

          </div>
        </div>

        {/* Right Column: Alert Properties & Actions */}
        <div className="space-y-6">
          
          {/* Status & Resolve Panel */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 space-y-4 shadow-sm">
            <h3 className="font-bold text-on-surface text-base">Xử lý sự cố</h3>
            
            <div className="space-y-3.5 pb-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Trạng thái hiện tại:</span>
                <StatusBadge type={al.status} />
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Camera nguồn:</span>
                <span className="font-semibold text-on-surface">{al.cameraName}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-on-surface-variant font-medium">Khu vực ROI:</span>
                <span className="font-semibold text-on-surface">{al.roiName || "Toàn cảnh"}</span>
              </div>
            </div>

            {/* Resolved audit trail */}
            {al.status === "resolved" && (
              <div className="p-3.5 bg-emerald-500/5 text-emerald-800 rounded-xl border border-emerald-500/10 text-xs space-y-1">
                <p className="font-bold">✓ Đã được xác nhận an toàn</p>
                <p className="text-[11px] text-emerald-700">Người xử lý: {al.resolvedBy}</p>
                <p className="text-[11px] text-emerald-700">Lúc: {al.resolvedAt ? new Date(al.resolvedAt).toLocaleTimeString("vi-VN") : ""}</p>
                {al.notes && <p className="text-[11px] mt-1 border-t border-emerald-500/10 pt-1 text-emerald-600 font-medium">Lưu ý: "{al.notes}"</p>}
              </div>
            )}

            {/* False Alarm audit trail */}
            {al.status === "false_alarm" && (
              <div className="p-3.5 bg-outline-variant/20 text-on-surface-variant rounded-xl border border-outline-variant/30 text-xs space-y-1">
                <p className="font-bold text-on-surface">⚠ Được đánh dấu Báo nhầm</p>
                <p className="text-[11px]">Người xác nhận: {al.checkedBy || "Hệ thống"}</p>
                {al.falseAlarmReason && (
                  <p className="text-[11px] mt-1 border-t border-outline-variant/30 pt-1 font-medium italic text-on-surface-variant">
                    Lý do: "{al.falseAlarmReason}"
                  </p>
                )}
              </div>
            )}

            {/* Action buttons (only for unresolved alerts) */}
            {(al.status === "unread" || al.status === "checking") && (
              <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/10">
                <button
                  onClick={handleResolve}
                  className="w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold rounded-xl transition-colors focus:outline-none shadow-sm flex items-center justify-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">done</span>
                  Xác nhận an toàn / Đã xử lý
                </button>
                <button
                  onClick={() => setShowFalseAlarmModal(true)}
                  className="w-full py-3 bg-surface-variant text-on-surface-variant hover:text-on-surface text-xs font-bold rounded-xl transition-all focus:outline-none flex items-center justify-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">cancel</span>
                  Báo cáo nhầm lẫn (False Alarm)
                </button>
              </div>
            )}
          </div>

          {/* Alert Notification logs */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 space-y-4 shadow-sm">
            <h3 className="font-bold text-on-surface text-base">Nhật ký kênh gửi</h3>
            
            <div className="flex flex-col gap-3">
              {al.channels.map((chan) => (
                <div key={chan} className="flex items-center gap-3 p-3 bg-surface-container-low rounded-xl">
                  <div className="w-8 h-8 rounded-full bg-primary-container/10 text-primary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[18px]">
                      {getChannelIcon(chan)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-xs text-on-surface">{getChannelLabel(chan)}</p>
                    <p className="text-[10px] text-emerald-600 mt-0.5 font-semibold flex items-center gap-0.5">
                      <span className="material-symbols-outlined text-[12px] fill">check_circle</span>
                      Đã gửi thành công
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Mock False Alarm dialog */}
      {showFalseAlarmModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-2xl max-w-sm w-full p-6 shadow-xl border border-outline-variant/20 animate-scale-up">
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-bold text-on-surface text-base">Báo cáo cảnh báo nhầm</h3>
              <button
                onClick={() => setShowFalseAlarmModal(false)}
                className="text-on-surface-variant hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <form onSubmit={handleFalseAlarmSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Lý do báo nhầm:</label>
                <textarea
                  value={falseAlarmReasonInput}
                  onChange={(e) => setFalseAlarmReasonInput(e.target.value)}
                  placeholder="Ví dụ: Bố/Mẹ bé đi ra ban công lấy đồ quần áo phơi..."
                  className="w-full p-3 border border-outline-variant rounded-xl text-xs focus:ring-1 focus:ring-primary focus:outline-none min-h-[80px]"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowFalseAlarmModal(false)}
                  className="py-2 px-4 rounded-lg bg-surface-container-high text-xs font-bold text-on-surface hover:bg-surface-container-highest"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="py-2 px-4 rounded-lg bg-primary text-white text-xs font-bold hover:bg-primary/90"
                >
                  Xác nhận
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
export default AlertDetailView;
