import { useState, useEffect } from "react";
import { useToast } from "../components/Toast";

export const useOnlineStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const { showToast } = useToast();

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      showToast("Đã kết nối mạng internet trở lại!", "success");
    };

    const handleOffline = () => {
      setIsOnline(false);
      showToast("Mất kết nối mạng. Đang chạy ở chế độ ngoại tuyến.", "warning");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [showToast]);

  return isOnline;
};
export default useOnlineStatus;
