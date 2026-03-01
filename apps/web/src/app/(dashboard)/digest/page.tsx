"use client";

import { useState } from "react";
import {
  Bell,
  BookOpen,
  CalendarClock,
  Clock,
  History,
  Loader2,
  Mail,
  Play,
  Send,
  Settings,
  Sparkles,
} from "lucide-react";
import { Badge, Button, Card, CardContent, cn, EmptyState, Tabs } from "@scr/ui";
import {
  useDigestPreview,
  useDigestHistory,
  useDigestPreferences,
  useUpdateDigestPreferences,
  useTriggerDigest,
  type DigestFrequency,
  type DigestSummary,
} from "@/lib/digest";
import { useSCRUser } from "@/lib/auth";

// ── Helpers ───────────────────────────────────────────────────────────────────

const SUMMARY_LABELS: Record<string, string> = {
  new_projects: "New Projects",
  new_documents: "New Documents",
  new_matches: "New Matches",
  new_alerts: "Watchlist Alerts",
  signal_score_updates: "Signal Score Updates",
  new_deals: "New Deals",
  new_risks: "New Risks",
  new_comments: "New Comments",
  ai_tasks_completed: "AI Tasks Completed",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function weekOf(iso: string) {
  const d = new Date(iso);
  return `Week of ${d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded bg-gray-100", className)} />;
}

// ── Summary stat card ─────────────────────────────────────────────────────────

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between border rounded-lg p-3 text-sm">
      <span className="text-gray-600">{label}</span>
      <Badge variant="info">{value}</Badge>
    </div>
  );
}

function DigestSummaryPanel({ summary }: { summary: DigestSummary }) {
  const entries = Object.entries(summary).filter(
    ([, v]) => v != null && v > 0
  ) as Array<[string, number]>;

  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        No activity in this period — your organisation is quiet.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {entries.map(([key, val]) => (
        <StatCard
          key={key}
          label={SUMMARY_LABELS[key] ?? key.replace(/_/g, " ")}
          value={val}
        />
      ))}
    </div>
  );
}

// ── AI Narrative panel ────────────────────────────────────────────────────────

function NarrativePanel({ text }: { text: string }) {
  return (
    <div className="prose prose-sm max-w-none text-gray-700 bg-gray-50 rounded-lg p-4 border text-sm leading-relaxed whitespace-pre-wrap">
      {text}
    </div>
  );
}

// ── Preview tab ───────────────────────────────────────────────────────────────

function PreviewTab({ isAdmin }: { isAdmin: boolean }) {
  const [days, setDays] = useState(7);
  const { data: preview, isLoading: loadingPreview } = useDigestPreview(days);
  const {
    mutate: trigger,
    isPending: generating,
    data: generated,
    reset,
  } = useTriggerDigest();

  const periodStart = preview?.summary?.period_start
    ? weekOf(preview.summary.period_start as unknown as string)
    : null;

  return (
    <div className="space-y-5">
      {/* Period selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <CalendarClock className="h-4 w-4 text-gray-400 shrink-0" />
        <span className="text-sm text-gray-600">Look-back window:</span>
        {[7, 14, 30].map((d) => (
          <button
            key={d}
            onClick={() => {
              setDays(d);
              reset();
            }}
            className={cn(
              "px-3 py-1 rounded-full text-sm font-medium transition-colors",
              days === d
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {d === 7 ? "7 days" : d === 14 ? "2 weeks" : "30 days"}
          </button>
        ))}
      </div>

      {/* Digest preview card */}
      <Card>
        <CardContent className="p-5 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-indigo-500" />
                Weekly Digest —{" "}
                {periodStart ?? `Last ${days} days`}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                Platform activity aggregated for your organisation
              </p>
            </div>
            {loadingPreview && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400 shrink-0 mt-1" />
            )}
          </div>

          {loadingPreview ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-3/4" />
            </div>
          ) : preview ? (
            <DigestSummaryPanel summary={preview.summary} />
          ) : (
            <p className="text-sm text-gray-400">No data available.</p>
          )}
        </CardContent>
      </Card>

      {/* AI Narrative card */}
      <Card>
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-500" />
              AI Narrative
            </p>
            <div className="flex items-center gap-2">
              {isAdmin && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => trigger(days)}
                  disabled={generating}
                  title="Send digest now (admin only)"
                >
                  {generating ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Send className="h-4 w-4 mr-2" />
                  )}
                  Send Now
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => trigger(days)}
                disabled={generating}
              >
                {generating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Generating…
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Generate
                  </>
                )}
              </Button>
            </div>
          </div>

          {generating && (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-full" />
              <p className="text-xs text-gray-400 pt-1">
                AI is generating your digest narrative…
              </p>
            </div>
          )}

          {generated && !generating ? (
            <div className="space-y-3">
              <NarrativePanel text={generated.narrative} />
              <p className="text-xs text-gray-400">
                Generated for the last {generated.days} days ·{" "}
                <button onClick={() => reset()} className="underline hover:text-gray-600">
                  Clear
                </button>
              </p>
            </div>
          ) : !generating ? (
            <p className="text-sm text-gray-400 italic">
              Click "Generate" to create an AI-written narrative summarising recent activity.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

// ── History tab ───────────────────────────────────────────────────────────────

function HistoryTab() {
  const { data, isLoading } = useDigestHistory();

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-2/3" />
      </div>
    );
  }

  if (!data?.history || data.history.length === 0) {
    return (
      <div className="space-y-4">
        <EmptyState
          icon={<History className="h-8 w-8 text-gray-300" />}
          title="No digest history yet"
          description={data?.message ?? "Digest history will appear here once emails have been sent."}
        />
      </div>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">Date Sent</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Recipients</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.history.map((entry) => (
              <tr key={entry.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-900 flex items-center gap-2">
                  <Clock className="h-3.5 w-3.5 text-gray-400" />
                  {formatDate(entry.sent_at)}
                </td>
                <td className="px-4 py-3 text-gray-600">{entry.recipients}</td>
                <td className="px-4 py-3">
                  <Badge
                    variant={
                      entry.status === "sent"
                        ? "success"
                        : entry.status === "failed"
                        ? "error"
                        : "neutral"
                    }
                  >
                    {entry.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

// ── Preferences tab ───────────────────────────────────────────────────────────

function PreferencesTab() {
  const { data: prefs, isLoading } = useDigestPreferences();
  const { mutate: update, isPending, isSuccess } = useUpdateDigestPreferences();

  const [form, setForm] = useState<{
    is_subscribed: boolean;
    frequency: DigestFrequency;
  } | null>(null);

  const current = form ??
    (prefs
      ? { is_subscribed: prefs.is_subscribed, frequency: prefs.frequency }
      : null);

  if (isLoading || !current) {
    return (
      <Card>
        <CardContent className="p-5">
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="max-w-lg">
      <Card>
        <CardContent className="p-6 space-y-6">
          <div>
            <p className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Mail className="h-4 w-4 text-indigo-500" />
              Email Digest Settings
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              Control how and when you receive AI-generated activity summaries.
            </p>
          </div>

          {/* Subscription toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">Email Digest</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Receive periodic AI-generated summaries by email
              </p>
            </div>
            <button
              onClick={() =>
                setForm((f) => ({
                  ...(f ?? current),
                  is_subscribed: !current.is_subscribed,
                }))
              }
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none",
                current.is_subscribed ? "bg-indigo-600" : "bg-gray-200"
              )}
              role="switch"
              aria-checked={current.is_subscribed}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform",
                  current.is_subscribed ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>

          {/* Frequency selector */}
          {current.is_subscribed && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Frequency</p>
              <div className="flex gap-2">
                {(["daily", "weekly", "monthly"] as DigestFrequency[]).map((f) => (
                  <button
                    key={f}
                    onClick={() =>
                      setForm((prev) => ({ ...(prev ?? current), frequency: f }))
                    }
                    className={cn(
                      "flex-1 py-2 text-sm rounded-lg border-2 capitalize transition-all",
                      current.frequency === f
                        ? "border-indigo-500 bg-indigo-50 text-indigo-700 font-medium"
                        : "border-gray-200 text-gray-600 hover:border-gray-300"
                    )}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400">
                {current.frequency === "daily"
                  ? "Digest sent every weekday morning."
                  : current.frequency === "weekly"
                  ? "Digest sent every Monday morning."
                  : "Digest sent on the first of each month."}
              </p>
            </div>
          )}

          {!current.is_subscribed && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <Bell className="h-4 w-4 text-amber-600 shrink-0" />
              <p className="text-xs text-amber-700">
                You are currently unsubscribed from email digests. You can still generate previews manually.
              </p>
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button
              size="sm"
              onClick={() => update(current)}
              disabled={isPending}
              className="flex-1"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Save Preferences
            </Button>
            {isSuccess && (
              <span className="text-xs text-green-600 font-medium">Saved!</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "preview" | "history" | "preferences";

export default function DigestPage() {
  const [activeTab, setActiveTab] = useState<Tab>("preview");
  const { user } = useSCRUser();
  const isAdmin = user?.role === "admin";

  const tabs: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    {
      id: "preview",
      label: "Preview",
      icon: <Sparkles className="h-4 w-4" />,
    },
    {
      id: "history",
      label: "History",
      icon: <History className="h-4 w-4" />,
    },
    {
      id: "preferences",
      label: "Preferences",
      icon: <Settings className="h-4 w-4" />,
    },
  ];

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
          <Mail className="h-6 w-6 text-indigo-500" />
          Weekly AI Digest
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          AI-generated summaries of your organisation's platform activity
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
              activeTab === tab.id
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "preview" && <PreviewTab isAdmin={isAdmin} />}
      {activeTab === "history" && <HistoryTab />}
      {activeTab === "preferences" && <PreferencesTab />}
    </div>
  );
}
