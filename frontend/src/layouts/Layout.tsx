import React, { useEffect } from "react";
import { Outlet, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Sidebar } from "../components/Sidebar";
import { Topbar } from "../components/Topbar";
import { MobileBottomNav } from "../components/MobileBottomNav";
import { PWAInstallPrompt } from "../components/PWAInstallPrompt";
import { OfflineBanner } from "../components/OfflineBanner";
import { useRealtimeAlerts } from "../hooks/useRealtimeAlerts";
import { useCameraStore } from "../store/cameraStore";
import { useRoiStore } from "../store/roiStore";

export const Layout: React.FC = () => {
  const { isAuthenticated } = useAuth();

  // Lắng nghe cảnh báo thời gian thực từ Backend
  useRealtimeAlerts();

  // Tải camera + ROI mới nhất từ backend rồi hydrate roiStore.
  useEffect(() => {
    let cancelled = false;
    const refresh = async (hydrateRoi: boolean) => {
      await useCameraStore.getState().loadCameras();
      if (!cancelled && hydrateRoi) {
        useRoiStore.getState().hydrateFromCameras();
      }
    };
    void refresh(true);
    const statusPoll = window.setInterval(() => void refresh(false), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(statusPoll);
    };
  }, []);

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex text-on-surface bg-background">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:ml-[280px] h-screen overflow-hidden pb-[72px] md:pb-0">
        {/* Top Navigation */}
        <Topbar />

        {/* Offline status notification */}
        <OfflineBanner />

        {/* Dynamic Route Canvas */}
        <main className="flex-1 overflow-y-auto bg-background">
          <div className="max-w-[1440px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />

      {/* Floating PWA Install Prompter */}
      <PWAInstallPrompt />
    </div>
  );
};
export default Layout;
