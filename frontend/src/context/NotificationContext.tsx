"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  ReactNode,
} from "react";
import { AppNotification } from "../app/types";
import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification as apiDeleteNotification,
  clearAllNotifications as apiClearAllNotifications,
  BACKEND_URL,
} from "../services/api";

interface NotificationContextType {
  notifications: AppNotification[];
  unreadCount: number;
  isLoading: boolean;
  isConnected: boolean;
  fetchNotifications: () => Promise<void>;
  markAsRead: (id: number) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  deleteNotification: (id: number) => Promise<void>;
  clearAll: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef<boolean>(true);

  // Fetch initial notifications and count
  const fetchNotifications = useCallback(async () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("versus_ai_jwt");
    if (!token) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    try {
      setIsLoading(true);
      const res = await getNotifications(undefined, 50, 0);
      if (isMountedRef.current && res.success) {
        setNotifications(res.notifications || []);
        setUnreadCount(res.unread_count ?? (res.notifications || []).filter((n) => n.status === "unread").length);
      }
    } catch (err) {
      console.warn("Failed to fetch notifications:", err);
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  // Mark single as read
  const markAsRead = useCallback(async (id: number) => {
    // Optimistic update
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, status: "read", read_at: new Date().toISOString() } : n))
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));

    try {
      await markNotificationRead(id);
    } catch (err) {
      console.error(`Failed to mark notification #${id} as read:`, err);
    }
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(async () => {
    const nowIso = new Date().toISOString();
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, status: "read", read_at: nowIso }))
    );
    setUnreadCount(0);

    try {
      await markAllNotificationsRead();
    } catch (err) {
      console.error("Failed to mark all notifications as read:", err);
    }
  }, []);

  // Delete notification
  const deleteNotification = useCallback(async (id: number) => {
    setNotifications((prev) => {
      const target = prev.find((n) => n.id === id);
      if (target && target.status === "unread") {
        setUnreadCount((c) => Math.max(0, c - 1));
      }
      return prev.filter((n) => n.id !== id);
    });

    try {
      await apiDeleteNotification(id);
    } catch (err) {
      console.error(`Failed to delete notification #${id}:`, err);
    }
  }, []);

  // Clear all
  const clearAll = useCallback(async () => {
    setNotifications([]);
    setUnreadCount(0);

    try {
      await apiClearAllNotifications();
    } catch (err) {
      console.error("Failed to clear all notifications:", err);
    }
  }, []);

  // Establish real-time WebSocket connection
  useEffect(() => {
    isMountedRef.current = true;
    let ws: WebSocket | null = null;
    let sseSource: EventSource | null = null;

    const connectRealtime = () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("versus_ai_jwt");
      if (!token) {
        setIsConnected(false);
        return;
      }

      // Convert BACKEND_URL to ws:// or wss://
      const wsBase = BACKEND_URL.replace(/^https?:\/\//i, (match) =>
        match.toLowerCase().startsWith("https") ? "wss://" : "ws://"
      );
      const wsUrl = `${wsBase}/ws/notifications?token=${encodeURIComponent(token)}`;

      try {
        ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          if (isMountedRef.current) {
            setIsConnected(true);
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === "NEW_NOTIFICATION" && data.notification) {
              const newNotif: AppNotification = data.notification;
              setNotifications((prev) => [newNotif, ...prev.filter((n) => n.id !== newNotif.id)]);
              setUnreadCount((prev) => prev + 1);

              // Native browser desktop notification if enabled
              if (
                typeof window !== "undefined" &&
                "Notification" in window &&
                Notification.permission === "granted"
              ) {
                try {
                  new Notification(newNotif.title, {
                    body: newNotif.message,
                    icon: "/favicon.ico",
                  });
                } catch {
                  // Ignore notification errors in restricted browser frames
                }
              }
            }
          } catch (e) {
            console.warn("[NotificationWS] Error parsing message:", e);
          }
        };

        ws.onclose = () => {
          if (isMountedRef.current) {
            setIsConnected(false);
            // Schedule reconnect after 5 seconds
            reconnectTimeoutRef.current = setTimeout(connectRealtime, 5000);
          }
        };

        ws.onerror = () => {
          // If WebSocket fails, fallback gracefully to SSE stream
          if (isMountedRef.current && !sseSource) {
            try {
              const sseUrl = `${BACKEND_URL}/api/notifications/stream?token=${encodeURIComponent(token)}`;
              sseSource = new EventSource(sseUrl);
              sseSource.addEventListener("notification", (e) => {
                try {
                  const payload = JSON.parse(e.data);
                  if (payload.notification) {
                    const newNotif: AppNotification = payload.notification;
                    setNotifications((prev) => [newNotif, ...prev.filter((n) => n.id !== newNotif.id)]);
                    setUnreadCount((prev) => prev + 1);
                  }
                } catch {}
              });
              sseSource.onopen = () => {
                if (isMountedRef.current) setIsConnected(true);
              };
              sseSource.onerror = () => {
                if (isMountedRef.current) setIsConnected(false);
              };
            } catch {}
          }
        };
      } catch (err) {
        console.warn("WebSocket init error:", err);
      }
    };

    fetchNotifications();
    connectRealtime();

    // Listen for storage changes (e.g. login/logout in other tabs)
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "versus_ai_jwt") {
        fetchNotifications();
        if (socketRef.current) {
          const s = socketRef.current;
          s.onopen = null;
          s.onmessage = null;
          s.onerror = null;
          s.onclose = null;
          if (s.readyState === WebSocket.OPEN) s.close();
        }
        connectRealtime();
      }
    };
    window.addEventListener("storage", handleStorage);

    return () => {
      isMountedRef.current = false;
      window.removeEventListener("storage", handleStorage);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        const s = socketRef.current;
        s.onopen = null;
        s.onmessage = null;
        s.onerror = null;
        s.onclose = null;
        if (s.readyState === WebSocket.OPEN) {
          s.close();
        } else if (s.readyState === WebSocket.CONNECTING) {
          s.addEventListener("open", () => s.close(), { once: true });
        }
      }
      if (sseSource) sseSource.close();
    };
  }, [fetchNotifications]);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        isLoading,
        isConnected,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
        deleteNotification,
        clearAll,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return context;
};
