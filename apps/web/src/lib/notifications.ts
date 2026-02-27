/**
 * Notification types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export type NotificationType =
  | "info"
  | "warning"
  | "action_required"
  | "mention"
  | "system";

export interface NotificationResponse {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UnreadCountResponse {
  count: number;
}

// ── Query Key Factory ──────────────────────────────────────────────────────

export const notificationKeys = {
  all: ["notifications"] as const,
  list: (params?: { page?: number; type?: string; is_read?: boolean }) =>
    [...notificationKeys.all, "list", params] as const,
  unreadCount: [...["notifications"], "unread-count"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useNotifications(params?: {
  page?: number;
  page_size?: number;
  type?: NotificationType;
  is_read?: boolean;
}) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: async () => {
      const { data } = await api.get<NotificationListResponse>(
        "/notifications",
        { params }
      );
      return data;
    },
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unreadCount,
    queryFn: async () => {
      const { data } = await api.get<UnreadCountResponse>(
        "/notifications/unread-count"
      );
      return data;
    },
    refetchInterval: 60_000, // Fallback polling every 60s
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      await api.put(`/notifications/${notificationId}/read`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.put("/notifications/read-all");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function notificationTypeColor(type: NotificationType): string {
  switch (type) {
    case "info":
      return "text-blue-500";
    case "warning":
      return "text-amber-500";
    case "action_required":
      return "text-red-500";
    case "mention":
      return "text-purple-500";
    case "system":
      return "text-neutral-500";
  }
}
