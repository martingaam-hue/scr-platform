"use client";

import {
  TrendingUp,
  Clock,
  Briefcase,
  Target,
  CheckCircle,
  BarChart3,
} from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import {
  useCapitalEfficiency,
  useEfficiencyBreakdown,
  useEfficiencyBenchmark,
  formatSavings,
  efficiencyScoreColor,
  efficiencyScoreBg,
  percentileLabel,
} from "@/lib/capital-efficiency";

// ── KPI Card ──────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string;
  value: string;
  subtext?: string;
  icon: React.ReactNode;
  colorClass?: string;
}

function KpiCard({ label, value, subtext, icon, colorClass = "text-blue-600" }: KpiCardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-gray-500 font-medium">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${colorClass}`}>{value}</p>
            {subtext && (
              <p className="text-xs text-gray-400 mt-1">{subtext}</p>
            )}
          </div>
          <div className={`p-2 rounded-lg bg-gray-50 ${colorClass}`}>{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Savings Breakdown ─────────────────────────────────────────────────────

function SavingsBreakdown() {
  const { data: breakdown, isLoading } = useEfficiencyBreakdown();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-14 rounded-lg bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!breakdown) return null;

  const maxValue = Math.max(...breakdown.categories.map((c) => c.value), 1);

  return (
    <div className="space-y-4">
      {breakdown.categories.map((cat) => (
        <div key={cat.name}>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-sm font-medium text-gray-700">{cat.name}</span>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400">{cat.vs_industry}</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatSavings(cat.value)}
              </span>
              <span className="text-xs text-gray-500 w-8 text-right">
                {cat.percentage.toFixed(0)}%
              </span>
            </div>
          </div>
          <div className="h-2.5 rounded-full bg-gray-100">
            <div
              className="h-2.5 rounded-full bg-blue-500 transition-all duration-500"
              style={{ width: `${(cat.value / maxValue) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Benchmark Table ───────────────────────────────────────────────────────

const BENCHMARK_LABELS: Record<string, string> = {
  dd_cost: "Due Diligence Cost",
  time_to_close_days: "Avg. Time to Close (days)",
  legal_cost: "Legal & Compliance Cost",
  risk_assessment_cost: "Risk Assessment Cost",
  efficiency_score: "Platform Efficiency Score",
};

function BenchmarkTable() {
  const { data: benchmark, isLoading } = useEfficiencyBenchmark();

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-10 rounded-lg bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!benchmark) return null;

  const outperformingSet = new Set(benchmark.outperforming);

  return (
    <div className="space-y-4">
      {/* Percentile badge */}
      <div className="flex items-center gap-3">
        <div
          className={`px-3 py-1.5 rounded-full border text-sm font-semibold ${
            benchmark.percentile >= 75
              ? "bg-green-50 border-green-200 text-green-700"
              : benchmark.percentile >= 50
              ? "bg-amber-50 border-amber-200 text-amber-700"
              : "bg-red-50 border-red-200 text-red-700"
          }`}
        >
          {benchmark.percentile}th percentile
        </div>
        <span className="text-sm text-gray-500">
          {percentileLabel(benchmark.percentile)} among similar funds
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 pr-4 text-gray-500 font-medium">
                Metric
              </th>
              <th className="text-right py-2 px-4 text-gray-500 font-medium">
                Your Platform
              </th>
              <th className="text-right py-2 pl-4 text-gray-500 font-medium">
                Industry Avg
              </th>
              <th className="text-center py-2 pl-4 text-gray-500 font-medium">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(benchmark.platform).map(([key, platformVal]) => {
              const industryVal = benchmark.industry_avg[key] ?? 0;
              const isScore = key === "efficiency_score";
              const isOutperforming = outperformingSet.has(
                BENCHMARK_LABELS[key] ?? key
              );

              // Format value
              const fmt = (v: number) =>
                isScore
                  ? `${v.toFixed(1)}`
                  : key === "time_to_close_days"
                  ? `${v.toFixed(0)} days`
                  : formatSavings(v);

              return (
                <tr key={key} className="border-b border-gray-100">
                  <td className="py-2.5 pr-4 text-gray-700 font-medium">
                    {BENCHMARK_LABELS[key] ?? key}
                  </td>
                  <td
                    className={`py-2.5 px-4 text-right font-semibold ${
                      isOutperforming ? "text-green-700" : "text-gray-700"
                    }`}
                  >
                    {fmt(platformVal)}
                  </td>
                  <td className="py-2.5 pl-4 text-right text-gray-500">
                    {fmt(industryVal)}
                  </td>
                  <td className="py-2.5 pl-4 text-center">
                    {isOutperforming ? (
                      <Badge variant="success">Outperforming</Badge>
                    ) : (
                      <Badge variant="neutral">Industry Avg</Badge>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {benchmark.outperforming.length > 0 && (
        <div className="bg-green-50 rounded-lg p-3">
          <p className="text-xs font-medium text-green-700 mb-1">
            Outperforming in {benchmark.outperforming.length} dimension
            {benchmark.outperforming.length > 1 ? "s" : ""}:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {benchmark.outperforming.map((dim) => (
              <span
                key={dim}
                className="flex items-center gap-1 text-xs text-green-700"
              >
                <CheckCircle className="h-3 w-3" />
                {dim}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function CapitalEfficiencyPage() {
  const { data: metrics, isLoading: metricsLoading } = useCapitalEfficiency();

  const kpiLoading = metricsLoading;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-green-100 rounded-lg">
          <TrendingUp className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Capital Efficiency Dashboard
          </h1>
          <p className="text-sm text-gray-500">
            Platform ROI and cost savings vs industry benchmarks
          </p>
        </div>
      </div>

      {/* KPI Row */}
      {kpiLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      ) : metrics ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Total Savings"
            value={formatSavings(metrics.total_savings)}
            subtext="vs industry average costs"
            icon={<TrendingUp className="h-5 w-5" />}
            colorClass="text-green-600"
          />
          <KpiCard
            label="Time Saved"
            value={`${metrics.time_saved_hours.toFixed(0)} hrs`}
            subtext={`${(metrics.time_saved_hours / 40).toFixed(1)} analyst weeks`}
            icon={<Clock className="h-5 w-5" />}
            colorClass="text-blue-600"
          />
          <KpiCard
            label="Deals Closed"
            value={String(metrics.deals_closed)}
            subtext={`${metrics.deals_screened} screened this period`}
            icon={<Briefcase className="h-5 w-5" />}
            colorClass="text-purple-600"
          />
          <KpiCard
            label="Platform Score"
            value={`${metrics.platform_efficiency_score.toFixed(0)}/100`}
            subtext={`Avg close: ${metrics.avg_time_to_close_days.toFixed(0)} days`}
            icon={<Target className="h-5 w-5" />}
            colorClass={efficiencyScoreColor(metrics.platform_efficiency_score)}
          />
        </div>
      ) : (
        <EmptyState
          icon={<BarChart3 className="h-8 w-8 text-gray-400" />}
          title="No efficiency data yet"
          description="Efficiency metrics are computed automatically as you use the platform."
        />
      )}

      {/* Savings Breakdown + Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Savings by Category</CardTitle>
            {metrics && (
              <p className="text-xs text-gray-500 mt-0.5">
                Total: {formatSavings(metrics.total_savings)} ·{" "}
                {new Date(metrics.period_start).toLocaleDateString()} –{" "}
                {new Date(metrics.period_end).toLocaleDateString()}
              </p>
            )}
          </CardHeader>
          <CardContent>
            <SavingsBreakdown />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Benchmark vs Industry Average
            </CardTitle>
            {metrics && (
              <p className="text-xs text-gray-500 mt-0.5">
                Industry data from comparable alternative investment funds
              </p>
            )}
          </CardHeader>
          <CardContent>
            <BenchmarkTable />
          </CardContent>
        </Card>
      </div>

      {/* Period footer */}
      {metrics && (
        <div className="text-xs text-gray-400 text-right">
          Last updated: {new Date(metrics.updated_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}
