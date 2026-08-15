import React, { useState } from "react";


export const FamilySharingView: React.FC = () => {
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [members] = useState([
    { id: 1, name: "Nguyễn Văn A", email: "nguyen.vana@gmail.com", role: "admin", status: "active", joinedAt: "2023-01-15" },
    { id: 2, name: "Trần Thị B (Vợ)", email: "tranthib@gmail.com", role: "admin", status: "active", joinedAt: "2023-01-16" },
    { id: 3, name: "Bà Nội", email: "banoi1960@gmail.com", role: "viewer", status: "active", joinedAt: "2023-05-20" },
    { id: 4, name: "Cô giúp việc", email: "cogiupviec@gmail.com", role: "viewer", status: "pending", joinedAt: "" },
  ]);

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Chia sẻ người thân</h2>
          <p className="text-sm text-on-surface-variant mt-1">Cấp quyền cho các thành viên trong gia đình cùng giám sát (Đã dùng {members.length}/5).</p>
        </div>
        <button
          onClick={() => setShowInviteForm(!showInviteForm)}
          className="px-5 py-2.5 bg-primary text-white font-bold rounded-xl shadow-sm hover:bg-primary/90 flex items-center justify-center gap-2 focus:outline-none transition-transform active:scale-95"
          disabled={members.length >= 5}
        >
          <span className="material-symbols-outlined text-[20px]">person_add</span>
          Thêm thành viên
        </button>
      </div>

      {showInviteForm && (
        <div className="bg-surface-container-low border border-primary/30 p-6 rounded-2xl animate-slide-up">
          <h3 className="font-bold text-on-surface mb-4">Gửi lời mời tham gia</h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-on-surface mb-1">Email người nhận</label>
              <input type="email" placeholder="VD: nguoithan@gmail.com" className="w-full h-10 px-3 bg-surface rounded-lg border border-outline-variant/40 focus:border-primary text-sm outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-on-surface mb-1">Phân quyền</label>
              <select className="w-full h-10 px-3 bg-surface rounded-lg border border-outline-variant/40 focus:border-primary text-sm outline-none">
                <option value="viewer">Người xem (Chỉ xem camera)</option>
                <option value="admin">Quản trị viên (Toàn quyền)</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => setShowInviteForm(false)}
                className="w-full h-10 bg-emerald-500 text-white font-bold rounded-lg shadow-sm hover:bg-emerald-600 focus:outline-none transition-colors"
              >
                Gửi lời mời
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/30 bg-surface-container-low/50">
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Thành viên</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Quyền hạn</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Trạng thái</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/10">
              {members.map(member => (
                <tr key={member.id} className="hover:bg-surface-variant/20 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">
                        {member.name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-bold text-sm text-on-surface">{member.name} {member.id === 1 && "(Bạn)"}</div>
                        <div className="text-xs text-on-surface-variant">{member.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      member.role === 'admin' ? 'bg-primary-container text-on-primary-container' : 'bg-surface-variant text-on-surface-variant'
                    }`}>
                      {member.role === 'admin' ? 'Quản trị viên' : 'Chỉ xem'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-2 h-2 rounded-full ${member.status === 'active' ? 'bg-emerald-500' : 'bg-amber-500'}`}></div>
                      <span className="text-xs font-semibold text-on-surface-variant">
                        {member.status === 'active' ? 'Đã tham gia' : 'Đang chờ xác nhận'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    {member.id !== 1 && (
                      <button className="p-2 text-on-surface-variant hover:text-error hover:bg-error/10 rounded-full transition-colors focus:outline-none">
                        <span className="material-symbols-outlined text-[20px]">person_remove</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
