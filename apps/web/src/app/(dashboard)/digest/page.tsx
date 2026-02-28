"use client";

import { useState } from "react";
import {
  Bell,
  BellOff,
  BookOpen,
  CalendarClock,
  Loader2,
  Mail,
  Play,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Badge, Button, Card, CardContent, cn } from "@scr/ui";
import {
  useDigestPreview,
  useDigestPreferences,
  useUpdateDigestPreferences,
  useTriggerDigest,
  type DigestFrequency,
  type DigestSummary,
} from "@/lib/digest";

// ── Summary stat card ─────────────────────────────────────────────────────────

function StatCard({ label, value }: { label: string; value: number }) {
  if (value === 0) return null;
  return (
    <div className="flex items-center justify-between border rounded-lg p-3 text-sm">
      <span className="text-gray-600">{label}</span>
      <Badge variant="info">{value}</Badge>
    </div>
  );
}

const SUMMARY_LABELS: Record<string, string> = {
  new_projects: "New Projects",
  new_documents: "New Documents",
  new_matches: "New Matches",
  new_alerts: "Watchlist Alerts",
  signal_score_updates: "Signal Score Updates",
  new_deals: "New Deals",
  new_risks: "New Risks",
  new_comments: "New Comments",
};

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
        <StatCard key={key} label={SUMMARY_LABELS[key] ?? key.replace(/_/g, " ")} value={val} />
      ))}
    </div>
  );
}

// ── Narrative panel ───────────────────────────────────────────────────────────

function NarrativePanel({ text }: { text: string }) {
  return (
    <div className="prose prose-sm max-w-none text-gray-700 bg-gray-50 rounded-lg p-4 border text-sm leading-relaxed whitespace-pre-wrap">
      {text}
    </div>
  );
}

// ── Preferences ───────────────────────────────────────────────────────────────

function PreferencesCard() {
  const { data: prefs, isLoading } = useDigestPreferences();
  const { mutate: update, isPending } = useUpdateDigestPreferences();

  const [form, setForm] = useState<{ is_subscribed: boolean; frequency: DigestFrequency } | null>(
    null
  );

  // Initialise form from server data (once)
  const current = form ?? (prefs ? { is_subscribed: prefs.is_subscribed, frequency: prefs.frequency } : null);

  if (isLoading || !current) {
    return (
      <Card>
        <CardContent className="p-4 flex justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </CardContent>
      </Card>
    );
  }

  const handleSave = () => {
    update(current);
  };

  return (
    <Card>
      <CardContent className="p-5 space-y-4">
        <p className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <Mail className="h-4 w-4 text-indigo-500" />
          Email Preferences
        </p>

        {/* Subscription toggle */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900">Activity Digest</p>
            <p className="text-xs text-gray-500">Receive a periodic AI-generated summary</p>
          </div>
          <button
            onClick={() =>
              setForm((f) => ({
                ...(f ?? current),
                is_subscribed: !current.is_subscribed,
              }))
            }
            className={cn(
              "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
              current.is_subscribed ? "bg-indigo-600" : "bg-gray-200"
            )}
          >
            <span
              className={cn(
                "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform",
                current.is_subscribed ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>

        {/* Frequency */}
        {current.is_subscribed && (
          <div className="space-y-2">
            <p className="text-sm text-gray-700">Frequency</p>
            <div className="flex gap-2">
              {(["daily", "weekly", "monthly"] as DigestFrequency[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setForm((prev) => ({ ...(prev ?? current), frequency: f }))}
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
          </div>
        )}

        <Button
          size="sm"
          className="w-full"
          onClick={handleSave}
          disabled={isPending}
        >
          {isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Save Preferences
        </Button>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DigestPage() {
  const [days, setDays] = useState(7);
  const { data: preview, isLoading: loadingPreview } = useDigestPreview(days);
  const {
    mutate: trigger,
    isPending: generating,
    data: generated,
    reset,
  } = useTriggerDigest();

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-indigo-500" />
          Activity Digest
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          AI-generated summary of your organisation's recent activity
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main */}
        <div className="lg:col-span-2 space-y-5">
          {/* Period selector */}
          <div className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-600">Look-back window:</span>
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => { setDays(d); reset(); }}
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

          {/* Activity summary */}
          <Card>
            <CardContent className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-indigo-500" />
                  Activity Summary — last {days} days
                </p>
                {loadingPreview && <Loader2 className="h-4 w-4 animate-spin text-gray-400" />}
              </div>
              {preview ? (
                <DigestSummaryPanel summary={preview.summary} />
              ) : !loadingPreview ? (
                <p className="text-sm text-gray-400">No data available.</p>
              ) : null}
            </CardContent>
          </Card>

          {/* Generate digest */}
          <Card>
            <CardContent className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-indigo-500" />
                  AI Narrative
                </p>
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
                      Generate Digest
                    </>
                  )}
                </Button>
              </div>

              {generated ? (
                <div className="space-y-3">
                  <NarrativePanel text={generated.narrative} />
                  <p className="text-xs text-gray-400">
                    Generated for the last {generated.days} days ·{" "}
                    <button onClick={() => reset()} className="underline hover:text-gray-600">
                      Clear
                    </button>
                  </p>
                </div>
              ) : (
                <p className="text-sm text-gray-400 italic">
                  Click "Generate Digest" to create an AI narrative summarising the activity above.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div>
          <PreferencesCard />
        </div>
      </div>
    </div>
  );
}
