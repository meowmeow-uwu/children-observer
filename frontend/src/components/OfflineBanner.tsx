import React from "react";
import { useOnlineStatus } from "../hooks/useOnlineStatus";

export const OfflineBanner: React.FC = () => {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="bg-error/15 border-b border-error/20 px-4 py-2.5 flex items-center justify-center gap-2 text-error text-xs animate-slide-down shadow-sm">
      <span className="material-symbols-outlined text-[18px] animate-pulse">cloud_off</span>
      <span className="font-semibold text-center leading-normal">
        Bạn đang ngoại tuyến. Một số chức năng như xem camera trực tiếp và nhận cảnh báo sẽ tạm thời không khả dụng.
      </span>
    </div>
  );
};
export default OfflineBanner;
