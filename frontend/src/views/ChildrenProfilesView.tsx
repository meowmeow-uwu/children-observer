import React, { useState } from "react";
import { useChildStore } from "../store/childStore";
import { useToast } from "../components/Toast";
import { SecureImage } from "../components/SecureImage";

export const ChildrenProfilesView: React.FC = () => {
  const { showToast } = useToast();
  const { children, addChild } = useChildStore();

  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState<"nam" | "nữ">("nam");
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !age) {
      showToast("Vui lòng điền đầy đủ Tên và Tuổi của bé", "error");
      return;
    }

    const newChild = {
      id: `child_${Date.now()}`,
      name,
      age: parseInt(age),
      gender,
      notes,
      avatarUrl: undefined // Mock default placeholder icon
    };

    addChild(newChild);
    setShowAddModal(false);
    showToast(`Đã thêm thành công hồ sơ của bé ${name}`, "success");
    
    // Reset form
    setName("");
    setAge("");
    setGender("nam");
    setNotes("");
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Hồ sơ trẻ em</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Đăng ký và quản lý thông tin các bé để hệ thống AI nhận diện khuôn mặt và hành vi cá nhân hóa.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="py-2.5 px-4 bg-primary text-white hover:bg-primary/95 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 focus:outline-none shrink-0 shadow-sm"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          Thêm hồ sơ trẻ
        </button>
      </div>

      {/* Children Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {children.map((child) => (
          <div
            key={child.id}
            className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-5 shadow-sm flex gap-4 items-start"
          >
            {/* Avatar */}
            <div className="w-16 h-16 rounded-2xl bg-surface-container-high border border-outline-variant/20 overflow-hidden shrink-0 flex items-center justify-center">
              {child.avatarUrl ? (
                <SecureImage src={child.avatarUrl} className="w-full h-full object-cover" />
              ) : (
                <span className="material-symbols-outlined text-[36px] text-outline">child_care</span>
              )}
            </div>

            {/* Meta */}
            <div className="flex-1 min-w-0 space-y-2">
              <div>
                <h3 className="font-bold text-on-surface text-base truncate">{child.name}</h3>
                <p className="text-xs text-on-surface-variant mt-0.5 font-medium capitalize">
                  {child.gender} • {child.age} tuổi
                </p>
              </div>

              {child.notes && (
                <div className="p-3 bg-surface-container-low border border-outline-variant/10 rounded-xl">
                  <p className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">Lưu ý an toàn</p>
                  <p className="text-xs text-on-surface-variant font-medium mt-1 leading-relaxed">{child.notes}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {children.length === 0 && (
        <div className="py-16 text-center text-outline max-w-sm mx-auto bg-surface-container-lowest border border-outline-variant/30 rounded-2xl">
          <span className="material-symbols-outlined text-[48px] mb-2">child_care</span>
          <h3 className="font-bold text-on-surface">Chưa đăng ký bé nào</h3>
          <p className="text-xs text-on-surface-variant mt-1">Đăng ký thông tin của bé để bắt đầu theo dõi an toàn.</p>
        </div>
      )}

      {/* Add Child Dialog */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-2xl max-w-md w-full p-6 shadow-xl border border-outline-variant/20 animate-scale-up">
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-bold text-on-surface text-base">Thêm hồ sơ trẻ mới</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-on-surface-variant hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Họ tên của bé:</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ví dụ: Nguyễn Minh Hải"
                  className="w-full p-3 border border-outline-variant rounded-xl text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Tuổi:</label>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    placeholder="Ví dụ: 3"
                    min="1"
                    max="15"
                    className="w-full p-3 border border-outline-variant rounded-xl text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Giới tính:</label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value as "nam" | "nữ")}
                    className="w-full p-3 border border-outline-variant rounded-xl text-xs bg-surface-container-lowest focus:ring-1 focus:ring-primary focus:outline-none"
                  >
                    <option value="nam">Nam</option>
                    <option value="nữ">Nữ</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Ghi chú an toàn / Đặc điểm:</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Ví dụ: Thường hay lại gần khu vực ổ điện ban công..."
                  className="w-full p-3 border border-outline-variant rounded-xl text-xs focus:ring-1 focus:ring-primary focus:outline-none min-h-[80px]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="py-2 px-4 rounded-lg bg-surface-container-high text-xs font-bold text-on-surface hover:bg-surface-container-highest"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="py-2 px-4 rounded-lg bg-primary text-white text-xs font-bold hover:bg-primary/90"
                >
                  Lưu hồ sơ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
export default ChildrenProfilesView;
