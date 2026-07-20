import React, { useState } from "react";
import { useToast } from "../components/Toast";

export const PrivacySettingsView: React.FC = () => {
  const { showToast } = useToast();

  const [retention, setRetention] = useState<"7_days" | "30_days" | "view_once">("7_days");
  const [showClearModal, setShowClearModal] = useState(false);

  // Mock access logs
  const accessLogs = [
    { id: "log_1", user: "Nguyễn Văn A", role: "parent", action: "Xem camera trực tiếp", camera: "Ban công", time: "15:30:22 - Hôm nay" },
    { id: "log_2", user: "Trần Thị B", role: "guardian", action: "Xem camera trực tiếp", camera: "Phòng khách", time: "14:15:05 - Hôm nay" },
    { id: "log_3", user: "Nguyễn Văn A", role: "parent", action: "Tải ảnh snapshot cảnh báo", camera: "Ban công", time: "11:24:45 - Hôm nay" },
    { id: "log_4", user: "Guest Viewer", role: "viewer", action: "Xem camera trực tiếp", camera: "Phòng khách", time: "09:05:12 - Hôm nay" },
    { id: "log_5", user: "Trần Thị B", role: "guardian", action: "Xem camera trực tiếp", camera: "Nhà bếp", time: "18:42:00 - Hôm qua" }
  ];

  const handleClearSnapshots = () => {
    setShowClearModal(false);
    showToast("Đã xóa toàn bộ ảnh chụp cảnh báo đã lưu trên thiết bị Hub!", "success");
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case "parent": return "Phụ huynh";
      case "guardian": return "Giám hộ";
      case "viewer":
      default:
        return "Người xem";
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-on-surface">Quyền riêng tư &amp; Dữ liệu</h2>
        <p className="text-sm text-on-surface-variant mt-1">
          Cấu hình lưu trữ ảnh chụp sự cố và kiểm tra nhật ký truy cập vào thiết bị camera.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Storage & Roles */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Retention configuration */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Thời gian lưu trữ ảnh cảnh báo</h3>
            <p className="text-xs text-on-surface-variant">
              Các bức ảnh snapshot ghi nhận sự cố vùng nguy hiểm được lưu trữ trực tiếp trên thẻ nhớ Edge Hub.
            </p>

            <div className="space-y-3 pt-2">
              <label
                onClick={() => {
                  setRetention("7_days");
                  showToast("Đã chuyển thời gian lưu trữ thành 7 ngày", "info");
                }}
                className={`p-4 rounded-xl border cursor-pointer flex items-start gap-3 transition-all ${
                  retention === "7_days"
                    ? "bg-primary/5 border-primary text-primary"
                    : "bg-surface-container-low border-outline-variant/20 hover:border-outline-variant"
                }`}
              >
                <input
                  type="radio"
                  name="retention"
                  checked={retention === "7_days"}
                  onChange={() => {}}
                  className="mt-0.5"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Tiêu chuẩn (7 ngày)</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Tối ưu dung lượng bộ nhớ. Tự động xóa sau 1 tuần.</span>
                </div>
              </label>

              <label
                onClick={() => {
                  setRetention("30_days");
                  showToast("Đã chuyển thời gian lưu trữ thành 30 ngày", "info");
                }}
                className={`p-4 rounded-xl border cursor-pointer flex items-start gap-3 transition-all ${
                  retention === "30_days"
                    ? "bg-primary/5 border-primary text-primary"
                    : "bg-surface-container-low border-outline-variant/20 hover:border-outline-variant"
                }`}
              >
                <input
                  type="radio"
                  name="retention"
                  checked={retention === "30_days"}
                  onChange={() => {}}
                  className="mt-0.5"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Lưu trữ lâu dài (30 ngày)</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Lưu trữ nhiều hơn để đối chiếu lịch sử sự kiện của tháng.</span>
                </div>
              </label>

              <label
                onClick={() => {
                  setRetention("view_once");
                  showToast("Đã cấu hình tự hủy ảnh sau khi xem", "info");
                }}
                className={`p-4 rounded-xl border cursor-pointer flex items-start gap-3 transition-all ${
                  retention === "view_once"
                    ? "bg-primary/5 border-primary text-primary"
                    : "bg-surface-container-low border-outline-variant/20 hover:border-outline-variant"
                }`}
              >
                <input
                  type="radio"
                  name="retention"
                  checked={retention === "view_once"}
                  onChange={() => {}}
                  className="mt-0.5"
                />
                <div>
                  <span className="font-bold text-xs block text-on-surface">Tự hủy sau khi xem</span>
                  <span className="text-[10px] text-on-surface-variant block mt-0.5">Xóa ngay lập tức ảnh snapshot trên Hub sau khi phụ huynh nhấp xem chi tiết cảnh báo.</span>
                </div>
              </label>
            </div>
          </div>

          {/* Access permissions summary */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Phân quyền vai trò camera</h3>
            
            <div className="space-y-3 text-xs">
              <div className="flex items-start gap-3 p-3 bg-surface-container-low rounded-xl">
                <span className="material-symbols-outlined text-primary text-[20px] shrink-0 mt-0.5">admin_panel_settings</span>
                <div>
                  <h4 className="font-bold text-on-surface">Phụ huynh (Admin)</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Toàn quyền xem trực tiếp, cấu hình vẽ vùng ROI, chỉnh sửa cài đặt lưu trữ và quản lý người dùng.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-surface-container-low rounded-xl">
                <span className="material-symbols-outlined text-secondary text-[20px] shrink-0 mt-0.5">family_home</span>
                <div>
                  <h4 className="font-bold text-on-surface">Người giám hộ</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Xem luồng camera trực tiếp, nhận và đánh dấu xử lý cảnh báo. Không thể sửa cấu hình vùng vẽ ROI hay cài đặt hệ thống.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-surface-container-low rounded-xl">
                <span className="material-symbols-outlined text-outline text-[20px] shrink-0 mt-0.5">visibility</span>
                <div>
                  <h4 className="font-bold text-on-surface">Người xem</h4>
                  <p className="text-[10px] text-on-surface-variant mt-0.5">Chỉ xem trực tiếp camera khi được cấp quyền tạm thời. Không xem được lịch sử cảnh báo hay hồ sơ của bé.</p>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Right Column: Access History Logs */}
        <div className="space-y-6">
          
          {/* Access Logs */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
            <h3 className="font-bold text-on-surface text-base">Lịch sử truy cập camera</h3>
            
            <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-1">
              {accessLogs.map((log) => (
                <div key={log.id} className="p-3 bg-surface-container-low rounded-xl text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-on-surface">{log.user}</span>
                    <span className="text-[9px] font-bold text-outline uppercase">{getRoleLabel(log.role)}</span>
                  </div>
                  <p className="text-on-surface-variant text-[11px]">
                    {log.action}: <strong className="text-on-surface-variant font-semibold">{log.camera}</strong>
                  </p>
                  <p className="text-[9px] text-outline text-right">{log.time}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Secure Trust Note */}
          <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-primary font-bold text-sm">
              <span className="material-symbols-outlined text-[18px]">verified_user</span>
              Cam kết bảo mật dữ liệu
            </div>
            <p className="text-[10px] text-on-surface-variant leading-relaxed">
              Hệ thống SafeKid Monitor hoạt động theo cơ chế biên mạng (Edge Computing). <strong>Chúng tôi không lưu video trực tiếp lên cloud.</strong> Chỉ ảnh chụp snapshot khi có sự cố được lưu trên thiết bị gia đình theo đúng thời hạn cấu hình ở trên.
            </p>
          </div>

          {/* Clear Cache Card */}
          <div className="bg-red-500/[0.02] p-5 rounded-2xl border border-error/20 shadow-sm space-y-3 text-center">
            <h4 className="font-bold text-xs text-error">Vùng nguy hiểm dữ liệu</h4>
            <p className="text-[10px] text-on-surface-variant leading-relaxed">
              Hành động này sẽ giải phóng toàn bộ thẻ nhớ và xóa vĩnh viễn các snapshot cảnh báo của trẻ.
            </p>
            <button
              onClick={() => setShowClearModal(true)}
              className="w-full py-2.5 bg-error text-white font-bold text-xs rounded-xl hover:bg-error/95 transition-all focus:outline-none shadow-sm"
            >
              Xóa tất cả ảnh cảnh báo
            </button>
          </div>

        </div>

      </div>

      {/* Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-2xl max-w-sm w-full p-6 shadow-xl border border-outline-variant/20 animate-scale-up text-center">
            <div className="w-14 h-14 rounded-full bg-error/10 text-error flex items-center justify-center mx-auto mb-4">
              <span className="material-symbols-outlined text-[32px] fill">warning</span>
            </div>
            
            <h3 className="font-bold text-on-surface text-base mb-2">Xác nhận xóa toàn bộ dữ liệu?</h3>
            <p className="text-xs text-on-surface-variant leading-relaxed mb-6">
              Bạn có chắc chắn muốn xóa vĩnh viễn toàn bộ ảnh chụp sự cố đã ghi nhận trên thiết bị Edge Hub không? Hành động này không thể hoàn tác.
            </p>

            <div className="flex gap-2">
              <button
                onClick={() => setShowClearModal(false)}
                className="flex-1 py-2.5 rounded-lg bg-surface-container-high text-xs font-bold text-on-surface hover:bg-surface-container-highest"
              >
                Hủy bỏ
              </button>
              <button
                onClick={handleClearSnapshots}
                className="flex-1 py-2.5 rounded-lg bg-error text-white text-xs font-bold hover:bg-error/90"
              >
                Đúng, xóa hết
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
export default PrivacySettingsView;
