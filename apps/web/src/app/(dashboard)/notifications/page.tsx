"use client";

import { useState } from "react";
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  Info,
  Loader2,
  MessageSquare,
  ShieldAlert,
  AlertTriangle,
  Settings,
} from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState, cn } from "@scr/ui";
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
  notificationTypeColor,
  type NotificationType,
  type NotificationResponse,
} from "@/lib/notifications";

// ── Type icon + label ─────────────────────────────────────────────────────────

const TYPE_META: Record<
  NotificationType,
  { icon: React.ElementType; label: string; badgeVariant: string }
> = {
  info: { icon: Info, label: "Info", badgeVariant: "info" },
  warning: { icon: AlertTriangle, label: "Warning", badgeVariant: "warning" },
  action_required: { icon: ShieldAlert, label: "Action Required", badgeVariant: "error" },
  mention: { icon: MessageSquare, label: "Mention", badgeVariant: "neutral" },
  system: { icon: Settings, label: "System", badgeVariant: "neutral" },
};

// ── Notification Row ──────────────────────────────────────────────────────────

function NotificationRow({ notification }: { notification: NotificationResponse }) {
  const { mutate: markRead, isPending } = useMarkRead();
  const meta = TYPE_META[notification.type];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "flex items-start gap-4 p-4 border-b last:border-0 transition-colors",
        notification.is_read ? "bg-white" : "bg-indigo-50/40"
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "mt-0.5 p-2 rounded-full flex-shrink-0",
          notification.is_read ? "bg-gray-100" : "bg-indigo-100"
        )}
      >
        <Icon
          className={cn(
            "h-4 w-4",
            notification.is_read
              ? "text-gray-400"
              : notificationTypeColor(notification.type)
          )}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p
              className={cn(
                "text-sm",
                notification.is_read ? "text-gray-700" : "font-medium text-gray-900"
              )}
            >
              {notification.title}
            </p>
            {notification.message && (
              <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                {notification.message}
              </p>
            )}
          </div>
          <span className="text-xs text-gray-400 flex-shrink-0 pt-0.5">
            {new Date(notification.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <Badge
            variant={meta.badgeVariant as "info" | "warning" | "error" | "neutral"}
            className="text-xs"
          >
            {meta.label}
          </Badge>
          {notification.link && (
            <a
              href={notification.link}
              className="text-xs text-indigo-600 hover:underline"
            >
              View →
            </a>
          )}
          {!notification.is_read && (
            <button
              onClick={() => markRead(notification.id)}
              disabled={isPending}
              className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 ml-auto"
            >
              {isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Check className="h-3 w-3" />
              )}
              Mark read
            </button>
          )}
        </div>
      </div>

      {/* Unread dot */}
      {!notification.is_read && (
        <div className="mt-2 w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0" />
      )}
    </div>
  );
}

// ── Filter tabs ───────────────────────────────────────────────────────────────

const FILTERS: Array<{ label: string; type: NotificationType | undefined; is_read?: boolean }> = [
  { label: "All", type: undefined },
  { label: "Unread", type: undefined, is_read: false },
  { label: "Action Required", type: "action_required" },
  { label: "Mentions", type: "mention" },
  { label: "Warnings", type: "warning" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const [filterIdx, setFilterIdx] = useState(0);
  const [page, setPage] = useState(1);
  const { mutate: markAllRead, isPending: markingAll } = useMarkAllRead();

  const activeFilter = FILTERS[filterIdx];
  const { data, isLoading } = useNotifications({
    page,
    page_size: 20,
    type: activeFilter.type,
    is_read: activeFilter.is_read,
  });

  const notifications = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <Bell className="h-6 w-6 text-indigo-500" />
            Notifications
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} notification{total !== 1 ? "s" : ""}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => markAllRead()}
          disabled={markingAll}
        >
          {markingAll ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <CheckCheck className="h-4 w-4 mr-2" />
          )}
          Mark all read
        </Button>
      </div>

      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map((f, i) => (
          <button
            key={i}
            onClick={() => { setFilterIdx(i); setPage(1); }}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
              filterIdx === i
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Notification list */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : notifications.length === 0 ? (
            <EmptyState
              title="No notifications"
              description={
                filterIdx === 0
                  ? "You're all caught up! New notifications will appear here."
                  : "No notifications match this filter."
              }
            />
          ) : (
            <div>
              {notifications.map((n) => (
                <NotificationRow key={n.id} notification={n} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
