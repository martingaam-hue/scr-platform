"use client";

import { Loader2, BarChart2, Zap, DollarSign, Target, FileText } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  cn,
} from "@scr/ui";
import {
  useAlleyOverview,
  useStageDistribution,
  useScoreDistribution,
  useRiskHeatmap,
  useDocumentCompleteness,
  riskCellBg,
  formatCurrency,
} from "@/lib/alley-analytics";

// ── Helpers ──────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4">
        <div className="flex items-start justify-between mb-2">
          <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
            {label}
          </p>
          <span className="text-neutral-300">{icon}</span>
        </div>
        <p className="text-2xl font-bold text-neutral-900">{value}</p>
        {sub && <p className="text-xs text-neutral-400 mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── Stage Distribution ────────────────────────────────────────────────────────

function StageDistributionChart() {
  const { data, isLoading } = useStageDistribution();

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data?.length) {
    return (
      <p className="text-sm text-neutral-400 text-center py-8">
        No stage data available.
      </p>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const stageColors = [
    "bg-blue-500",
    "bg-indigo-500",
    "bg-violet-500",
    "bg-purple-500",
    "bg-pink-500",
    "bg-rose-500",
  ];

  return (
    <div className="space-y-3">
      {data.map((item, i) => {
        const pct = (item.count / maxCount) * 100;
        return (
          <div key={item.stage} className="flex items-center gap-3">
            <div className="w-28 shrink-0 text-xs text-neutral-600 text-right truncate">
              {item.stage}
            </div>
            <div className="flex-1 h-6 bg-neutral-100 rounded overflow-hidden flex items-center">
              <div
                className={cn(
                  "h-full rounded transition-all flex items-center px-2",
                  stageColors[i % stageColors.length]
                )}
                style={{ width: `${Math.max(pct, 4)}%` }}
              >
                <span className="text-xs text-white font-medium">
                  {item.count}
                </span>
              </div>
            </div>
            <div className="w-24 shrink-0 text-xs text-neutral-400 text-right">
              {item.total_mw > 0 ? `${item.total_mw.toFixed(0)} MW` : ""}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Score Distribution ────────────────────────────────────────────────────────

function ScoreDistributionChart() {
  const { data, isLoading } = useScoreDistribution();

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data?.length) {
    return (
      <p className="text-sm text-neutral-400 text-center py-8">
        No score distribution data.
      </p>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const bucketColors: Record<string, string> = {
    "0-20": "bg-red-500",
    "20-40": "bg-orange-500",
    "40-60": "bg-amber-500",
    "60-80": "bg-lime-500",
    "80-100": "bg-green-500",
  };

  return (
    <div className="flex items-end gap-2 h-32">
      {data.map((item) => {
        const heightPct = (item.count / maxCount) * 100;
        const color = bucketColors[item.bucket] ?? "bg-blue-500";
        return (
          <div
            key={item.bucket}
            className="flex flex-col items-center gap-1 flex-1"
          >
            <span className="text-xs font-medium text-neutral-600">
              {item.count}
            </span>
            <div className="w-full flex items-end" style={{ height: "80px" }}>
              <div
                className={cn("w-full rounded-t transition-all", color)}
                style={{ height: `${Math.max(heightPct, 4)}%` }}
              />
            </div>
            <span className="text-xs text-neutral-400 truncate w-full text-center">
              {item.bucket}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Risk Heatmap ──────────────────────────────────────────────────────────────

function RiskHeatmapTable() {
  const { data, isLoading } = useRiskHeatmap();

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data?.length) {
    return (
      <p className="text-sm text-neutral-400 text-center py-8">
        No risk heatmap data.
      </p>
    );
  }

  const RISK_DIMS: Array<{ key: keyof typeof data[0]; label: string }> = [
    { key: "technical", label: "Technical" },
    { key: "financial", label: "Financial" },
    { key: "regulatory", label: "Regulatory" },
    { key: "esg", label: "ESG" },
    { key: "market", label: "Market" },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-100">
            <th className="pb-2 text-left text-xs font-medium text-neutral-500 pr-4">
              Project
            </th>
            {RISK_DIMS.map((d) => (
              <th
                key={d.key}
                className="pb-2 text-center text-xs font-medium text-neutral-500 px-2"
              >
                {d.label}
              </th>
            ))}
            <th className="pb-2 text-center text-xs font-medium text-neutral-500 px-2">
              Overall
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.project_id} className="border-b border-neutral-50 last:border-0">
              <td className="py-2 pr-4 font-medium text-neutral-800 max-w-[140px] truncate">
                {row.project_name}
              </td>
              {RISK_DIMS.map((d) => {
                const score = row[d.key] as number;
                return (
                  <td key={d.key} className="py-2 px-2 text-center">
                    <span
                      className={cn(
                        "inline-block rounded px-2 py-0.5 text-xs font-semibold",
                        riskCellBg(score)
                      )}
                    >
                      {score}
                    </span>
                  </td>
                );
              })}
              <td className="py-2 px-2 text-center">
                <Badge
                  variant={
                    row.overall_risk_level === "high" ||
                    row.overall_risk_level === "critical"
                      ? "error"
                      : row.overall_risk_level === "medium"
                      ? "warning"
                      : "neutral"
                  }
                >
                  {row.overall_risk_level}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Document Completeness ─────────────────────────────────────────────────────

function DocumentCompletenessList() {
  const { data, isLoading } = useDocumentCompleteness();

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data?.length) {
    return (
      <p className="text-sm text-neutral-400 text-center py-8">
        No document completeness data.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {data.map((item) => {
        const pct = Math.min(100, Math.max(0, item.completeness_pct));
        const barColor =
          pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
        return (
          <div key={item.project_id} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-neutral-800 truncate mr-2">
                {item.project_name}
              </span>
              <span className="shrink-0 text-neutral-500 text-xs">
                {item.uploaded_count}/{item.expected_count} docs &middot;{" "}
                {pct.toFixed(0)}%
              </span>
            </div>
            <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", barColor)}
                style={{ width: `${pct}%` }}
              />
            </div>
            {item.missing_types.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {item.missing_types.slice(0, 5).map((t) => (
                  <span
                    key={t}
                    className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded"
                  >
                    Missing: {t}
                  </span>
                ))}
                {item.missing_types.length > 5 && (
                  <span className="text-xs text-neutral-400">
                    +{item.missing_types.length - 5} more
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const { data: overview, isLoading: loadingOverview } = useAlleyOverview();

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart2 className="h-6 w-6 text-blue-600" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">
            Pipeline Analytics
          </h1>
          <p className="text-sm text-neutral-500">
            Portfolio-level view across all your projects
          </p>
        </div>
      </div>

      {/* KPI cards */}
      {loadingOverview ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : overview ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label="Total Projects"
            value={String(overview.total_projects)}
            sub={`${overview.scored_projects} scored`}
            icon={<Target className="h-5 w-5" />}
          />
          <StatCard
            label="Total Capacity"
            value={`${overview.total_mw.toFixed(0)} MW`}
            sub="Aggregate pipeline"
            icon={<Zap className="h-5 w-5" />}
          />
          <StatCard
            label="Avg Signal Score"
            value={overview.avg_score.toFixed(1)}
            sub="Portfolio average"
            icon={<BarChart2 className="h-5 w-5" />}
          />
          <StatCard
            label="Total Value"
            value={formatCurrency(overview.total_value, overview.currency)}
            sub="Aggregate investment"
            icon={<DollarSign className="h-5 w-5" />}
          />
        </div>
      ) : null}

      {/* Stage + Score distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Stage Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <StageDistributionChart />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Score Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ScoreDistributionChart />
          </CardContent>
        </Card>
      </div>

      {/* Risk heatmap */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Risk Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <RiskHeatmapTable />
        </CardContent>
      </Card>

      {/* Document completeness */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <FileText className="h-4 w-4 text-neutral-500" />
          <CardTitle className="text-sm">Document Completeness</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentCompletenessList />
        </CardContent>
      </Card>
    </div>
  );
}
