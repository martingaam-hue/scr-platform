"use client";

import React, { useEffect, useRef, useState } from "react";
import { Bell, Check, Info, AlertTriangle, AtSign, Cog } from "lucide-react";
import { cn } from "@scr/ui";
import { useNotificationStore } from "@/lib/store";
import {
  useNotifications,
  useUnreadCount,
  useMarkRead,
  useMarkAllRead,
  notificationTypeColor,
  type NotificationType,
} from "@/lib/notifications";
import { timeAgo } from "@/lib/collaboration";
import { useQueryClient } from "@tanstack/react-query";
import { notificationKeys } from "@/lib/notifications";

function notificationTypeIcon(type: NotificationType) {
  switch (type) {
    case "info":
      return <Info className="h-4 w-4" />;
    case "warning":
      return <AlertTriangle className="h-4 w-4" />;
    case "action_required":
      return <AlertTriangle className="h-4 w-4" />;
    case "mention":
      return <AtSign className="h-4 w-4" />;
    case "system":
      return <Cog className="h-4 w-4" />;
  }
}

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  const { unreadCount, setUnreadCount, increment } = useNotificationStore();
  const { data: unreadData } = useUnreadCount();
  const { data: notifData } = useNotifications({ page_size: 10 });
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  // Sync unread count from API
  useEffect(() => {
    if (unreadData) {
      setUnreadCount(unreadData.count);
    }
  }, [unreadData, setUnreadCount]);

  // SSE connection
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const eventSource = new EventSource(`${apiUrl}/notifications/stream`, {
      withCredentials: true,
    });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "notification") {
          increment();
          qc.invalidateQueries({ queryKey: notificationKeys.all });
        }
      } catch {
        // Ignore heartbeats and parse errors
      }
    };

    eventSource.onerror = () => {
      // EventSource will auto-reconnect
    };

    return () => {
      eventSource.close();
    };
  }, [increment, qc]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleMarkAllRead = () => {
    markAllRead.mutate();
  };

  const handleNotificationClick = (notif: {
    id: string;
    link: string | null;
    is_read: boolean;
  }) => {
    if (!notif.is_read) {
      markRead.mutate(notif.id);
    }
    if (notif.link) {
      window.location.href = notif.link;
    }
    setIsOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-md p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-error-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-error-500" />
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-96 overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
              >
                <Check className="h-3 w-3" />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-96 overflow-y-auto">
            {!notifData?.items.length ? (
              <div className="px-4 py-8 text-center text-sm text-neutral-400">
                No notifications yet
              </div>
            ) : (
              notifData.items.map((notif) => (
                <button
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={cn(
                    "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800",
                    !notif.is_read && "bg-primary-50/50 dark:bg-primary-950/20"
                  )}
                >
                  <div
                    className={cn(
                      "mt-0.5 shrink-0",
                      notificationTypeColor(notif.type)
                    )}
                  >
                    {notificationTypeIcon(notif.type)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {notif.title}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-neutral-500 dark:text-neutral-400">
                      {notif.message}
                    </p>
                    <p className="mt-1 text-xs text-neutral-400 dark:text-neutral-500">
                      {timeAgo(notif.created_at)}
                    </p>
                  </div>
                  {!notif.is_read && (
                    <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary-500" />
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
