"use client";

import { useState } from "react";
import { TrendingUp, BarChart3, Target, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import {
  useBenchmarkList,
  useBenchmarkComparison,
  type BenchmarkEntry,
  type BenchmarkMetricComparison,
} from "@/lib/metrics";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatValue(v: number | null): string {
  if (v == null) return "—";
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(2);
}

function quartileBadge(quartile: 1 | 2 | 3 | 4) {
  const map: Record<number, { label: string; cls: string }> = {
    1: { label: "Top 25%", cls: "bg-green-100 text-green-700" },
    2: { label: "25–50%", cls: "bg-blue-100 text-blue-700" },
    3: { label: "50–75%", cls: "bg-amber-100 text-amber-700" },
    4: { label: "Bottom 25%", cls: "bg-red-100 text-red-700" },
  };
  const { label, cls } = map[quartile] ?? map[4];
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{label}</span>;
}

function vsDelta(vsMedian: number) {
  if (Math.abs(vsMedian) < 0.001) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs text-neutral-400">
        <Minus className="h-3 w-3" /> At median
      </span>
    );
  }
  if (vsMedian > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs text-green-600">
        <ArrowUpRight className="h-3 w-3" /> +{(vsMedian * 100).toFixed(1)}%
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-xs text-red-500">
      <ArrowDownRight className="h-3 w-3" /> {(vsMedian * 100).toFixed(1)}%
    </span>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-xs font-medium text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-neutral-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-neutral-400">{sub}</p>}
    </div>
  );
}

// ── Benchmark list row ─────────────────────────────────────────────────────

function BenchmarkRow({ entry }: { entry: BenchmarkEntry }) {
  return (
    <tr className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <td className="px-4 py-3 text-sm font-medium text-neutral-900">{entry.metric_name}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">{entry.asset_class}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">{entry.geography}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">{entry.stage}</td>
      <td className="px-4 py-3 text-sm text-neutral-700">{formatValue(entry.p25)}</td>
      <td className="px-4 py-3 text-sm font-medium text-neutral-900">{formatValue(entry.median)}</td>
      <td className="px-4 py-3 text-sm text-neutral-700">{formatValue(entry.p75)}</td>
      <td className="px-4 py-3 text-xs text-neutral-400">{entry.sample_count} samples</td>
    </tr>
  );
}

// ── Comparison row ─────────────────────────────────────────────────────────

function ComparisonRow({ comp }: { comp: BenchmarkMetricComparison }) {
  return (
    <tr className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <td className="px-4 py-3 text-sm font-medium text-neutral-900">{comp.metric_name}</td>
      <td className="px-4 py-3 text-sm text-primary-700 font-semibold">
        {formatValue(comp.project_value)}
      </td>
      <td className="px-4 py-3 text-sm text-neutral-600">{formatValue(comp.p25)}</td>
      <td className="px-4 py-3 text-sm text-neutral-700 font-medium">{formatValue(comp.median)}</td>
      <td className="px-4 py-3 text-sm text-neutral-600">{formatValue(comp.p75)}</td>
      <td className="px-4 py-3">{quartileBadge(comp.quartile)}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">
        {(comp.percentile_rank * 100).toFixed(0)}th pct
      </td>
      <td className="px-4 py-3">{vsDelta(comp.vs_median)}</td>
    </tr>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

type ViewMode = "benchmarks" | "comparison";

export default function MetricsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("benchmarks");
  const [projectId, setProjectId] = useState<string>("");

  const { data: benchmarkList, isLoading: benchmarksLoading } = useBenchmarkList();
  const { data: comparison, isLoading: comparisonLoading } = useBenchmarkComparison(
    projectId || ""
  );

  const benchmarks: BenchmarkEntry[] = benchmarkList?.items ?? [];
  const comparisons: BenchmarkMetricComparison[] = comparison?.comparisons ?? [];

  // Stats from benchmark list
  const uniqueMetrics = new Set(benchmarks.map((b) => b.metric_name)).size;
  const uniqueClasses = new Set(benchmarks.map((b) => b.asset_class)).size;
  const totalSamples = benchmarks.reduce((s, b) => s + b.sample_count, 0);

  // Comparison stats
  const topQuartile = comparisons.filter((c) => c.quartile === 1).length;
  const belowMedian = comparisons.filter((c) => c.quartile >= 3).length;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100">
            <TrendingUp className="h-5 w-5 text-teal-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Benchmarks & Metrics</h1>
            <p className="text-sm text-neutral-500">Compare project performance against industry benchmarks</p>
          </div>
        </div>

        {/* View toggle */}
        <div className="flex rounded-lg border border-neutral-200 overflow-hidden">
          <button
            onClick={() => setViewMode("benchmarks")}
            className={`flex items-center gap-2 px-4 py-1.5 text-sm font-medium transition-colors ${
              viewMode === "benchmarks"
                ? "bg-primary-600 text-white"
                : "bg-white text-neutral-600 hover:bg-neutral-50"
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Benchmark Library
          </button>
          <button
            onClick={() => setViewMode("comparison")}
            className={`flex items-center gap-2 px-4 py-1.5 text-sm font-medium transition-colors ${
              viewMode === "comparison"
                ? "bg-primary-600 text-white"
                : "bg-white text-neutral-600 hover:bg-neutral-50"
            }`}
          >
            <Target className="h-4 w-4" />
            Project Comparison
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {viewMode === "benchmarks" ? (
          <>
            <StatCard label="Total Benchmarks" value={benchmarkList?.total ?? 0} />
            <StatCard label="Unique Metrics" value={uniqueMetrics} />
            <StatCard label="Asset Classes" value={uniqueClasses} />
            <StatCard label="Total Samples" value={totalSamples.toLocaleString()} />
          </>
        ) : (
          <>
            <StatCard label="Metrics Compared" value={comparisons.length} />
            <StatCard
              label="Top Quartile"
              value={topQuartile}
              sub="metrics in Q1"
            />
            <StatCard
              label="Below Median"
              value={belowMedian}
              sub="metrics in Q3/Q4"
            />
            <StatCard
              label="Avg Percentile"
              value={
                comparisons.length
                  ? `${(
                      (comparisons.reduce((s, c) => s + c.percentile_rank, 0) /
                        comparisons.length) *
                      100
                    ).toFixed(0)}th`
                  : "—"
              }
            />
          </>
        )}
      </div>

      {/* Project ID input (comparison mode) */}
      {viewMode === "comparison" && (
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-neutral-700">Project ID</label>
          <input
            type="text"
            placeholder="Enter project ID to compare against benchmarks…"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
        <div className="border-b border-neutral-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-neutral-900">
            {viewMode === "benchmarks" ? "Benchmark Library" : "Project vs Benchmarks"}
          </h2>
        </div>

        {viewMode === "benchmarks" ? (
          benchmarksLoading ? (
            <div className="animate-pulse">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="border-b border-neutral-100 px-4 py-4 flex gap-4">
                  {Array.from({ length: 8 }).map((_, j) => (
                    <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
                  ))}
                </div>
              ))}
            </div>
          ) : benchmarks.length === 0 ? (
            <div className="py-16 text-center text-neutral-400 text-sm">No data available</div>
          ) : (
            <table className="w-full text-left">
              <thead className="border-b border-neutral-200 bg-neutral-50">
                <tr>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Metric</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Asset Class</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Geography</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Stage</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">P25</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Median</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">P75</th>
                  <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Samples</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.map((b) => (
                  <BenchmarkRow key={b.id} entry={b} />
                ))}
              </tbody>
            </table>
          )
        ) : comparisonLoading ? (
          <div className="animate-pulse">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="border-b border-neutral-100 px-4 py-4 flex gap-4">
                {Array.from({ length: 8 }).map((_, j) => (
                  <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
                ))}
              </div>
            ))}
          </div>
        ) : !projectId ? (
          <div className="py-16 text-center text-neutral-400 text-sm">
            Enter a project ID above to compare against benchmarks
          </div>
        ) : comparisons.length === 0 ? (
          <div className="py-16 text-center text-neutral-400 text-sm">No data available</div>
        ) : (
          <table className="w-full text-left">
            <thead className="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Metric</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Your Value</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">P25</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Median</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">P75</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Quartile</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Percentile</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">vs Median</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((comp) => (
                <ComparisonRow key={comp.metric_name} comp={comp} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
