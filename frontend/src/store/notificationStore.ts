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

const mockNotifications: InAppNotification[] = [
  {
    id: "notif_1",
    title: "Cảnh báo vùng nguy hiểm",
    message: "Bé Vy được phát hiện lại gần rào chắn Ban công.",
    type: "danger",
    createdAt: new Date(Date.now() - 600000).toISOString(), // 10 mins ago
    relatedAlertId: "alert_002",
    read: false
  },
  {
    id: "notif_2",
    title: "Cảnh báo khẩn cấp",
    message: "Bé Bo leo trèo khu vực ổ điện Phòng khách.",
    type: "danger",
    createdAt: new Date(Date.now() - 3600000 * 3).toISOString(), // 3 hours ago
    relatedAlertId: "alert_001",
    read: false
  },
  {
    id: "notif_3",
    title: "Thông báo bảo mật",
    message: "Thiết bị Edge Hub Gateway của gia đình đã kết nối trực tiếp thành công.",
    type: "success",
    createdAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    read: true
  }
];

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: mockNotifications,
  unreadCount: mockNotifications.filter((n) => !n.read).length,

  addNotification: (newNotif) =>
    set((state) => {
      const item: InAppNotification = {
        ...newNotif,
        id: `notif_${Date.now()}`,
        createdAt: new Date().toISOString(),
        read: false
      };
      const nextList = [item, ...state.notifications];
      return {
        notifications: nextList,
        unreadCount: nextList.filter((n) => !n.read).length
      };
    }),

  markAsRead: (id) =>
    set((state) => {
      const nextList = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      );
      return {
        notifications: nextList,
        unreadCount: nextList.filter((n) => !n.read).length
      };
    }),

  markAllAsRead: () =>
    set((state) => {
      const nextList = state.notifications.map((n) => ({ ...n, read: true }));
      return {
        notifications: nextList,
        unreadCount: 0
      };
    }),

  clearAll: () =>
    set({
      notifications: [],
      unreadCount: 0
    })
}));
export default useNotificationStore;
