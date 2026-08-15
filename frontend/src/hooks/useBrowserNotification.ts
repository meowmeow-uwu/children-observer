import { useState, useEffect, useCallback } from "react";

export type NotificationPermissionState = "default" | "granted" | "denied" | "unsupported";

export const useBrowserNotification = () => {
  const [permission, setPermission] = useState<NotificationPermissionState>("default");

  useEffect(() => {
    if (!("Notification" in window)) {
      setPermission("unsupported");
    } else {
      setPermission(Notification.permission as NotificationPermissionState);
    }
  }, []);

  const requestPermission = async (): Promise<NotificationPermissionState> => {
    if (!("Notification" in window)) {
      return "unsupported";
    }

    try {
      const result = await Notification.requestPermission();
      const nextPermission = result as NotificationPermissionState;
      setPermission(nextPermission);
      return nextPermission;
    } catch {
      // Fallback for older browsers
      const result = Notification.permission;
      const nextPermission = result as NotificationPermissionState;
      setPermission(nextPermission);
      return nextPermission;
    }
  };

  const showNotification = useCallback((title: string, options?: NotificationOptions) => {
    if (!("Notification" in window) || Notification.permission !== "granted") {
      return;
    }

    try {
      const defaultOptions: NotificationOptions = {
        icon: "icons/icon-192.png",
        badge: "icons/icon-192.png",
        dir: "auto",
        lang: "vi",
        ...options
      };
      
      new Notification(title, defaultOptions);
    } catch {
      // Handle older/mobile browsers failure to build constructor
    }
  }, []);

  return {
    permission,
    requestPermission,
    showNotification
  };
};
export default useBrowserNotification;
