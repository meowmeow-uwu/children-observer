import React, { useEffect } from "react";
import { useBlocker } from "react-router-dom";

interface UnsavedChangesBlockerProps {
  when: boolean;
}

/**
 * Chặn điều hướng khi có ROI draft chưa lưu:
 * - useBlocker hiển thị dialog thật với nút proceed/reset (không chặn im lặng).
 * - beforeunload cảnh báo khi đóng tab.
 */
export const UnsavedChangesBlocker: React.FC<UnsavedChangesBlockerProps> = ({ when }) => {
  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    return when && currentLocation.pathname !== nextLocation.pathname;
  });

  // Cảnh báo đóng tab với draft chưa lưu
  useEffect(() => {
    if (!when) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [when]);

  if (blocker.state !== "blocked") return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-2xl max-w-sm w-full p-6 shadow-xl border border-outline-variant/20 animate-scale-up text-center" role="alertdialog" aria-modal="true" aria-labelledby="unsaved-title">
        <div className="w-14 h-14 rounded-full bg-amber-500/10 text-amber-600 flex items-center justify-center mx-auto mb-4">
          <span className="material-symbols-outlined text-[32px] fill">edit_note</span>
        </div>
        <h3 id="unsaved-title" className="font-bold text-on-surface text-base mb-2">Vùng nguy hiểm chưa được lưu</h3>
        <p className="text-xs text-on-surface-variant leading-relaxed mb-6">
          Bạn có thay đổi chưa lưu trên trang này. Rời đi sẽ làm mất vùng đang vẽ.
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => blocker.reset()}
            className="flex-1 py-2.5 rounded-xl bg-surface-container-high text-xs font-bold text-on-surface hover:bg-surface-container-highest cursor-pointer min-h-[44px]"
          >
            Ở lại chỉnh sửa
          </button>
          <button
            onClick={() => blocker.proceed()}
            className="flex-1 py-2.5 rounded-xl bg-error text-white text-xs font-bold hover:bg-error/90 cursor-pointer min-h-[44px]"
          >
            Rời đi, bỏ thay đổi
          </button>
        </div>
      </div>
    </div>
  );
};

export default UnsavedChangesBlocker;
