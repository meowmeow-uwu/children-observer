import React from "react";
import { Link } from "react-router-dom";

export const InvoiceListView: React.FC = () => {
  const invoices = [
    { id: "INV-2023-08-01", date: "01/08/2023", amount: 99000, status: "paid", plan: "Premium (1 tháng)" },
    { id: "INV-2023-07-01", date: "01/07/2023", amount: 99000, status: "paid", plan: "Premium (1 tháng)" },
    { id: "INV-2023-06-01", date: "01/06/2023", amount: 99000, status: "paid", plan: "Premium (1 tháng)" },
  ];

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/billing" className="w-10 h-10 rounded-full hover:bg-surface-variant flex items-center justify-center text-on-surface-variant transition-colors">
          <span className="material-symbols-outlined">arrow_back</span>
        </Link>
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-on-surface">Lịch sử thanh toán</h2>
          <p className="text-sm text-on-surface-variant mt-1">Quản lý hóa đơn và biên lai điện tử của bạn.</p>
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/30 bg-surface-container-low/50">
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Mã hóa đơn</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Ngày lập</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Gói dịch vụ</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Số tiền</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Trạng thái</th>
                <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider text-right">Tải về</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/10">
              {invoices.map(inv => (
                <tr key={inv.id} className="hover:bg-surface-variant/20 transition-colors">
                  <td className="px-6 py-4 font-semibold text-sm text-on-surface">{inv.id}</td>
                  <td className="px-6 py-4 text-sm text-on-surface-variant">{inv.date}</td>
                  <td className="px-6 py-4 text-sm text-on-surface-variant">{inv.plan}</td>
                  <td className="px-6 py-4 font-bold text-sm text-on-surface">{inv.amount.toLocaleString("vi-VN")}đ</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      inv.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {inv.status === 'paid' ? 'Đã thanh toán' : 'Đang xử lý'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-2 text-primary hover:bg-primary/10 rounded-full transition-colors focus:outline-none">
                      <span className="material-symbols-outlined text-[20px]">download</span>
                    </button>
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
