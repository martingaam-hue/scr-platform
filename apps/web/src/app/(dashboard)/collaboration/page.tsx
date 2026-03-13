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
import { InfoBanner } from "@/components/info-banner";
import {
  useActivityFeed,
  timeAgo,
  type ActivityResponse,
} from "@/lib/collaboration";

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_ACTIVITY_FEED: ActivityResponse[] = [
  { id: "act-01", org_id: "org-pamp", user_id: "u-martin", user_name: "Martin Gaam", user_avatar: null, entity_type: "document", entity_id: "doc-q4nav", action: "uploaded", description: "Q4 2025 NAV Report", created_at: "2026-03-13T09:00:00Z", changes: {} },
  { id: "act-02", org_id: "org-pamp", user_id: "u-jonas", user_name: "Jonas Eriksson", user_avatar: null, entity_type: "project", entity_id: "p2", action: "updated", description: "Nordvik Wind Farm II technical specifications", created_at: "2026-03-12T14:30:00Z", changes: { turbine_model: true, capacity_mw: true } },
  { id: "act-03", org_id: "org-pamp", user_id: null, user_name: "Nordic Pension Fund", user_avatar: null, entity_type: "document", entity_id: "dr-helios", action: "viewed", description: "Helios Solar data room (12 documents)", created_at: "2026-03-11T11:15:00Z", changes: {} },
  { id: "act-04", org_id: "org-pamp", user_id: "u-helena", user_name: "Helena Strand", user_avatar: null, entity_type: "document", entity_id: "doc-q1fin", action: "created", description: "Q1 2026 financial projections published", created_at: "2026-03-10T10:00:00Z", changes: {} },
  { id: "act-05", org_id: "org-pamp", user_id: "u-anders", user_name: "Anders Nyström", user_avatar: null, entity_type: "risk", entity_id: "p4", action: "completed", description: "Baltic BESS Grid Storage risk assessment", created_at: "2026-03-09T16:45:00Z", changes: {} },
  { id: "act-06", org_id: "org-pamp", user_id: null, user_name: "EIB Co-Investment", user_avatar: null, entity_type: "portfolio", entity_id: "p1", action: "created", description: "co-investment term request for Helios Solar", created_at: "2026-03-08T13:20:00Z", changes: {} },
  { id: "act-07", org_id: "org-pamp", user_id: "u-karl", user_name: "Karl Bergström", user_avatar: null, entity_type: "document", entity_id: "doc-alpine-agr", action: "signed", description: "Alpine Hydro Partners investment agreement executed", created_at: "2026-03-05T09:30:00Z", changes: {} },
  { id: "act-08", org_id: "org-pamp", user_id: "u-maja", user_name: "Maja Lindqvist", user_avatar: null, entity_type: "document", entity_id: "doc-esg-q1", action: "created", description: "ESG monitoring report published for Q1 2026", created_at: "2026-03-03T11:00:00Z", changes: {} },
  { id: "act-09", org_id: "org-pamp", user_id: null, user_name: "Sofia Bergman (SCR Capital)", user_avatar: null, entity_type: "portfolio", entity_id: "p8", action: "created", description: "term sheet sent for Thames Clean Energy Hub", created_at: "2026-03-01T15:00:00Z", changes: {} },
  { id: "act-10", org_id: "org-pamp", user_id: null, user_name: "Dutch Infrastructure Trust", user_avatar: null, entity_type: "document", entity_id: "doc-helios-nda", action: "signed", description: "Helios Solar Portfolio Iberia NDA", created_at: "2026-02-28T10:45:00Z", changes: {} },
  { id: "act-11", org_id: "org-pamp", user_id: "u-martin", user_name: "Martin Gaam", user_avatar: null, entity_type: "project", entity_id: "p6", action: "completed", description: "Sahara CSP Development feasibility study", created_at: "2026-02-25T17:00:00Z", changes: {} },
  { id: "act-12", org_id: "org-pamp", user_id: "u-jonas", user_name: "Jonas Eriksson", user_avatar: null, entity_type: "project", entity_id: "p8", action: "created", description: "Thames Clean Energy Hub grid connection application submitted", created_at: "2026-02-20T09:15:00Z", changes: {} },
];

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

  const items = data?.items ?? (page === 1 ? MOCK_ACTIVITY_FEED : []);
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Activity className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Activity Feed</h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              All actions across your organisation — projects, documents, and people
            </p>
          </div>
        </div>
        {data && (
          <span className="text-xs text-neutral-400 border border-neutral-200 rounded-full px-3 py-1">
            {data.total} event{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <InfoBanner>
        The <strong>Activity Feed</strong> gives you a real-time view of every action taken across
        your organisation — project updates, document uploads, deal changes, risk flags, and team
        activity. Use this feed to stay informed and maintain a full audit trail.
      </InfoBanner>

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
