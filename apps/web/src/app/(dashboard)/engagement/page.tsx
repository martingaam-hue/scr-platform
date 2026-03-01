"use client";

import { useState } from "react";
import { Activity, Eye, Users, Clock, Download } from "lucide-react";
import {
  useDealRoomEngagement,
  type DealEngagementSummary,
} from "@/lib/engagement";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatSeconds(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function engagementBadge(score: number) {
  if (score >= 75) {
    return (
      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        High
      </span>
    );
  }
  if (score >= 40) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
        Medium
      </span>
    );
  }
  return (
    <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600">
      Low
    </span>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  iconClass,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  iconClass: string;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 flex items-center gap-4">
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconClass}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs font-medium text-neutral-500">{label}</p>
        <p className="text-2xl font-bold text-neutral-900">{value}</p>
      </div>
    </div>
  );
}

// ── Engagement row ─────────────────────────────────────────────────────────

function EngagementRow({ entry }: { entry: DealEngagementSummary }) {
  return (
    <tr className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <td className="px-4 py-3 text-sm font-mono text-neutral-600">{entry.investor_org_id.slice(0, 8)}…</td>
      <td className="px-4 py-3 text-sm text-neutral-800">{entry.unique_documents_viewed}</td>
      <td className="px-4 py-3 text-sm text-neutral-800">{formatSeconds(entry.total_time_seconds)}</td>
      <td className="px-4 py-3 text-sm text-neutral-800">{entry.avg_completion_pct.toFixed(1)}%</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-24 rounded-full bg-neutral-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-primary-500 transition-all"
              style={{ width: `${Math.min(entry.engagement_score, 100)}%` }}
            />
          </div>
          <span className="text-sm text-neutral-700">{entry.engagement_score.toFixed(0)}</span>
          {engagementBadge(entry.engagement_score)}
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-neutral-500">{formatDate(entry.last_active_at)}</td>
    </tr>
  );
}

// ── Date range tabs ────────────────────────────────────────────────────────

type Range = "7d" | "30d" | "90d";

const RANGES: { key: Range; label: string }[] = [
  { key: "7d", label: "7 days" },
  { key: "30d", label: "30 days" },
  { key: "90d", label: "90 days" },
];

// ── Page ───────────────────────────────────────────────────────────────────

export default function EngagementPage() {
  const [range, setRange] = useState<Range>("30d");
  const [dealRoomId, setDealRoomId] = useState<string>("");

  const { data: engagementData, isLoading } = useDealRoomEngagement(dealRoomId || undefined);

  const entries: DealEngagementSummary[] = engagementData ?? [];

  const totalTime = entries.reduce((sum, e) => sum + e.total_time_seconds, 0);
  const totalDocs = entries.reduce((sum, e) => sum + e.unique_documents_viewed, 0);
  const avgScore = entries.length
    ? entries.reduce((sum, e) => sum + e.engagement_score, 0) / entries.length
    : 0;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
            <Activity className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Engagement Analytics</h1>
            <p className="text-sm text-neutral-500">Track investor engagement across deal room documents</p>
          </div>
        </div>

        {/* Date range filter */}
        <div className="flex rounded-lg border border-neutral-200 overflow-hidden">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                range === r.key
                  ? "bg-primary-600 text-white"
                  : "bg-white text-neutral-600 hover:bg-neutral-50"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Deal Room selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-neutral-700">Deal Room ID</label>
        <input
          type="text"
          placeholder="Enter deal room ID to load engagement data…"
          value={dealRoomId}
          onChange={(e) => setDealRoomId(e.target.value)}
          className="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={Users} label="Unique Investors" value={entries.length} iconClass="bg-blue-100 text-blue-600" />
        <StatCard icon={Eye} label="Total Doc Views" value={totalDocs} iconClass="bg-violet-100 text-violet-600" />
        <StatCard icon={Clock} label="Total Time Spent" value={formatSeconds(totalTime)} iconClass="bg-amber-100 text-amber-600" />
        <StatCard icon={Download} label="Avg Engagement Score" value={avgScore.toFixed(1)} iconClass="bg-green-100 text-green-600" />
      </div>

      {/* Table */}
      <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
        <div className="border-b border-neutral-200 px-4 py-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-900">Investor Engagement</h2>
          <span className="text-xs text-neutral-400">{entries.length} investor{entries.length !== 1 ? "s" : ""}</span>
        </div>

        {isLoading ? (
          <div className="animate-pulse">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="border-b border-neutral-100 px-4 py-4 flex gap-4">
                {Array.from({ length: 6 }).map((_, j) => (
                  <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
                ))}
              </div>
            ))}
          </div>
        ) : !dealRoomId ? (
          <div className="py-16 text-center text-neutral-400 text-sm">
            Enter a deal room ID above to load engagement analytics
          </div>
        ) : entries.length === 0 ? (
          <div className="py-16 text-center text-neutral-400 text-sm">No data available</div>
        ) : (
          <table className="w-full text-left">
            <thead className="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Investor Org</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Docs Viewed</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Total Time</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Avg Completion</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Engagement Score</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Last Active</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <EngagementRow key={entry.investor_org_id} entry={entry} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
