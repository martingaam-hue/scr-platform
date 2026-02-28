"use client";

import { useState } from "react";
import {
  Activity,
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  FolderKanban,
  Loader2,
  MessageSquare,
  Shield,
  Users,
} from "lucide-react";
import { Badge, Card, CardContent, EmptyState, cn } from "@scr/ui";
import {
  useActivityFeed,
  timeAgo,
  type ActivityResponse,
} from "@/lib/collaboration";

// ── Entity icon + colour ──────────────────────────────────────────────────────

const ENTITY_META: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  project: { icon: FolderKanban, color: "text-indigo-500 bg-indigo-50", label: "Project" },
  document: { icon: FileText, color: "text-amber-500 bg-amber-50", label: "Document" },
  comment: { icon: MessageSquare, color: "text-green-500 bg-green-50", label: "Comment" },
  user: { icon: Users, color: "text-purple-500 bg-purple-50", label: "User" },
  portfolio: { icon: Building2, color: "text-blue-500 bg-blue-50", label: "Portfolio" },
  risk: { icon: Shield, color: "text-red-500 bg-red-50", label: "Risk" },
};

function entityMeta(entityType: string) {
  return ENTITY_META[entityType] ?? { icon: Activity, color: "text-gray-500 bg-gray-50", label: entityType };
}

// ── Action colour ─────────────────────────────────────────────────────────────

function actionColor(action: string): string {
  if (action.includes("creat") || action.includes("add")) return "text-green-700 bg-green-100";
  if (action.includes("delet") || action.includes("remov")) return "text-red-700 bg-red-100";
  if (action.includes("updat") || action.includes("edit") || action.includes("modif")) return "text-amber-700 bg-amber-100";
  if (action.includes("approv") || action.includes("complet") || action.includes("sign")) return "text-indigo-700 bg-indigo-100";
  return "text-gray-700 bg-gray-100";
}

// ── Activity Item ─────────────────────────────────────────────────────────────

function ActivityItem({ item }: { item: ActivityResponse }) {
  const meta = entityMeta(item.entity_type);
  const Icon = meta.icon;

  return (
    <div className="flex items-start gap-4 py-4 px-5 border-b last:border-0">
      {/* Entity type icon */}
      <div className={cn("p-2 rounded-lg flex-shrink-0 mt-0.5", meta.color.split(" ")[1])}>
        <Icon className={cn("h-4 w-4", meta.color.split(" ")[0])} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-gray-800 leading-snug">
            {item.user_name ? (
              <span className="font-medium">{item.user_name}</span>
            ) : (
              <span className="text-gray-400">System</span>
            )}{" "}
            <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium mx-1", actionColor(item.action))}>
              {item.action}
            </span>{" "}
            <span className="text-gray-500">{item.description}</span>
          </p>
          <span className="text-xs text-gray-400 flex-shrink-0 whitespace-nowrap pt-0.5">
            {timeAgo(item.created_at)}
          </span>
        </div>

        <div className="flex items-center gap-2 mt-1.5">
          <Badge variant="neutral" className="text-xs">
            {meta.label}
          </Badge>
          {/* Changes summary */}
          {item.changes && Object.keys(item.changes).length > 0 && (
            <span className="text-xs text-gray-400">
              Changed: {Object.keys(item.changes).join(", ")}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CollaborationPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useActivityFeed(page);

  const items = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-indigo-500" />
            Activity Feed
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            All actions across your organisation — projects, documents, and people
          </p>
        </div>
        {data && (
          <span className="text-sm text-gray-400">
            {data.total} event{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Feed */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              title="No activity yet"
              description="Actions taken by your team will appear here — project updates, document uploads, deal changes, and more."
            />
          ) : (
            <div>
              {items.map((item) => (
                <ActivityItem key={item.id} item={item} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-40"
          >
            <ChevronLeft className="h-5 w-5 text-gray-500" />
          </button>
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-40"
          >
            <ChevronRight className="h-5 w-5 text-gray-500" />
          </button>
        </div>
      )}
    </div>
  );
}
