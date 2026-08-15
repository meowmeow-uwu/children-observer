import { create } from "zustand";

export interface InAppNotification {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "danger" | "success";
  createdAt: string;
  relatedAlertId?: string;
  snapshotUrl?: string;
  read: boolean;
}

interface NotificationState {
  notifications: InAppNotification[];
  unreadCount: number;
  addNotification: (notification: Omit<InAppNotification, "id" | "createdAt" | "read">) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  // Không seed mock data — notifications được thêm khi nhận ALERT_NEW từ backend
  notifications: [],
  unreadCount: 0,

  addNotification: (newNotif) =>
    set((state) => {
      const item: InAppNotification = {
        ...newNotif,
        id: `notif_${Date.now()}`,
        createdAt: new Date().toISOString(),
        read: false,
      };
      const nextList = [item, ...state.notifications];
      return {
        notifications: nextList,
        unreadCount: nextList.filter((n) => !n.read).length,
      };
    }),

  markAsRead: (id) =>
    set((state) => {
      const nextList = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      );
      return {
        notifications: nextList,
        unreadCount: nextList.filter((n) => !n.read).length,
      };
    }),

  markAllAsRead: () =>
    set((state) => {
      const nextList = state.notifications.map((n) => ({ ...n, read: true }));
      return { notifications: nextList, unreadCount: 0 };
    }),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),
}));
export default useNotificationStore;
