import React, { useEffect, useState } from "react";
import { useToast } from "./Toast";

export const PWAInstallPrompt: React.FC = () => {
  const { showToast } = useToast();
  
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      // Prevent standard browser prompt
      e.preventDefault();
      // Stash the event so it can be triggered later
      setDeferredPrompt(e);
      // Show the install banner
      setIsVisible(true);
    };

    const handleAppInstalled = () => {
      // Clear stashed event and hide banner
      setDeferredPrompt(null);
      setIsVisible(false);
      showToast("Ứng dụng SafeKid Monitor đã được cài đặt thành công!", "success");
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, [showToast]);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    // Show prompt dialog
    deferredPrompt.prompt();

    // Wait for the user choice
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === "accepted") {
      showToast("Bắt đầu cài đặt ứng dụng...", "info");
    } else {
      showToast("Đã từ chối cài đặt ứng dụng.", "warning");
    }

    // Clear stashed prompt
    setDeferredPrompt(null);
    setIsVisible(false);
  };

  const handleDismissClick = () => {
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-20 md:bottom-6 right-4 left-4 md:left-auto md:max-w-sm bg-surface-container-lowest border border-outline-variant/40 rounded-2xl p-4 shadow-xl z-50 animate-scale-up flex gap-3 items-start">
      <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
        <span className="material-symbols-outlined text-[24px]">install_mobile</span>
      </div>
      
      <div className="flex-1 space-y-3">
        <div>
          <h4 className="font-bold text-xs text-on-surface">Cài đặt SafeKid Monitor</h4>
          <p className="text-[11px] text-on-surface-variant mt-0.5 leading-relaxed">
            Cài đặt ứng dụng trên màn hình chờ điện thoại/máy tính để có trải nghiệm tức thì và nhận cảnh báo nhanh hơn.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleDismissClick}
            className="flex-1 py-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container-high text-[10px] font-bold text-on-surface transition-colors"
          >
            Để sau
          </button>
          <button
            onClick={handleInstallClick}
            className="flex-1 py-1.5 rounded-lg bg-primary hover:bg-primary/95 text-[10px] font-bold text-white transition-colors shadow-sm"
          >
            Cài ứng dụng
          </button>
        </div>
      </div>
    </div>
  );
};
export default PWAInstallPrompt;
