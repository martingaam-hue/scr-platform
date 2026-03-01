"use client";

import { useState } from "react";
import { DollarSign, Cpu, AlertCircle, TrendingUp } from "lucide-react";
import {
  useAICostReport,
  formatTokens,
  type AICostEntry,
} from "@/lib/admin";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatCost(tokens: number): string {
  // Approximate cost: claude-sonnet ~$3/M input tokens, using as proxy
  const cost = (tokens / 1_000_000) * 3;
  if (cost >= 1000) return `$${(cost / 1000).toFixed(1)}K`;
  if (cost >= 1) return `$${cost.toFixed(2)}`;
  return `$${cost.toFixed(4)}`;
}

function formatAvgMs(ms: number | null): string {
  if (ms == null) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

// ── Stat card ─────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  iconClass,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  sub?: string;
  iconClass: string;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 flex items-center gap-4">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${iconClass}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-neutral-500">{label}</p>
        <p className="text-2xl font-bold text-neutral-900">{value}</p>
        {sub && <p className="text-xs text-neutral-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Cost entry row ─────────────────────────────────────────────────────────

function CostRow({
  entry,
  totalTokens,
}: {
  entry: AICostEntry;
  totalTokens: number;
}) {
  const pct = totalTokens > 0 ? (entry.total_tokens / totalTokens) * 100 : 0;

  return (
    <tr className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <td className="px-4 py-3">
        <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs font-mono text-neutral-700">
          {entry.label}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-neutral-800">{entry.task_count.toLocaleString()}</td>
      <td className="px-4 py-3 text-sm font-medium text-neutral-900">{formatTokens(entry.total_tokens)}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-24 rounded-full bg-neutral-100 overflow-hidden">
            <div className="h-full rounded-full bg-primary-500" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs text-neutral-500">{pct.toFixed(1)}%</span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-neutral-800">{formatCost(entry.total_tokens)}</td>
      <td className="px-4 py-3 text-sm text-neutral-800">{formatAvgMs(entry.avg_processing_ms)}</td>
      <td className="px-4 py-3">
        {entry.failed_count > 0 ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            <AlertCircle className="h-3 w-3" />
            {entry.failed_count}
          </span>
        ) : (
          <span className="text-xs text-neutral-300">—</span>
        )}
      </td>
    </tr>
  );
}

// ── Period tabs ────────────────────────────────────────────────────────────

const PERIODS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
];

type ViewTab = "by_agent" | "by_model" | "by_org";

const VIEW_TABS: { key: ViewTab; label: string }[] = [
  { key: "by_agent", label: "By Agent" },
  { key: "by_model", label: "By Model" },
  { key: "by_org", label: "By Org" },
];

// ── Page ───────────────────────────────────────────────────────────────────

export default function AICostsPage() {
  const [periodDays, setPeriodDays] = useState(30);
  const [viewTab, setViewTab] = useState<ViewTab>("by_agent");

  const { data: report, isLoading } = useAICostReport(periodDays);

  const entries: AICostEntry[] = report ? report[viewTab] : [];
  const totalTokens = report?.total_tokens ?? 0;
  const estimatedTotalCost = formatCost(totalTokens);
  const dailyAvgTokens = report ? totalTokens / report.period_days : 0;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
            <DollarSign className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">AI Cost Management</h1>
            <p className="text-sm text-neutral-500">Monitor token usage and estimated costs across all AI tasks</p>
          </div>
        </div>

        {/* Period selector */}
        <div className="flex rounded-lg border border-neutral-200 overflow-hidden">
          {PERIODS.map((p) => (
            <button
              key={p.days}
              onClick={() => setPeriodDays(p.days)}
              className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                periodDays === p.days
                  ? "bg-primary-600 text-white"
                  : "bg-white text-neutral-600 hover:bg-neutral-50"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      {isLoading ? (
        <div className="grid grid-cols-4 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4">
              <div className="h-3 w-20 bg-neutral-100 rounded mb-2" />
              <div className="h-7 w-16 bg-neutral-200 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            icon={DollarSign}
            label="Estimated Spend"
            value={estimatedTotalCost}
            sub={`${periodDays}-day period`}
            iconClass="bg-emerald-100 text-emerald-600"
          />
          <StatCard
            icon={Cpu}
            label="Total Tokens"
            value={formatTokens(totalTokens)}
            sub={`${formatTokens(Math.round(dailyAvgTokens))}/day avg`}
            iconClass="bg-blue-100 text-blue-600"
          />
          <StatCard
            icon={TrendingUp}
            label="Total Tasks"
            value={(report?.total_tasks ?? 0).toLocaleString()}
            iconClass="bg-violet-100 text-violet-600"
          />
          <StatCard
            icon={AlertCircle}
            label="Failed Tasks"
            value={report?.total_failed ?? 0}
            sub={
              report && report.total_tasks > 0
                ? `${((report.total_failed / report.total_tasks) * 100).toFixed(1)}% failure rate`
                : undefined
            }
            iconClass="bg-red-100 text-red-600"
          />
        </div>
      )}

      {/* View tabs + table */}
      <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
        <div className="border-b border-neutral-200 flex items-center justify-between px-4">
          <div className="flex">
            {VIEW_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setViewTab(tab.key)}
                className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  viewTab === tab.key
                    ? "border-primary-600 text-primary-700"
                    : "border-transparent text-neutral-500 hover:text-neutral-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-neutral-400">{entries.length} entries</span>
        </div>

        {isLoading ? (
          <div className="animate-pulse">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="border-b border-neutral-100 px-4 py-4 flex gap-4">
                {Array.from({ length: 7 }).map((_, j) => (
                  <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
                ))}
              </div>
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="py-16 text-center text-neutral-400 text-sm">No data available</div>
        ) : (
          <table className="w-full text-left">
            <thead className="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Label</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Task Count</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Total Tokens</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Token Share</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Est. Cost</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Avg Processing</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Failures</th>
              </tr>
            </thead>
            <tbody>
              {entries
                .slice()
                .sort((a, b) => b.total_tokens - a.total_tokens)
                .map((entry) => (
                  <CostRow key={entry.label} entry={entry} totalTokens={totalTokens} />
                ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-neutral-400">
        * Cost estimates are approximate based on ~$3/M tokens (Claude Sonnet pricing). Actual costs depend on model mix and provider rates.
      </p>
    </div>
  );
}
