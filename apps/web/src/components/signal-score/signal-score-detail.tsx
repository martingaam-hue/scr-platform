"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  FileCheck,
  FileText,
  Loader2,
  Minus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Upload,
  Zap,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  LineChart,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  cn,
} from "@scr/ui";
import {
  ResponsiveContainer,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  useProjectScoreDetail,
  scoreLabel,
  effortColor,
} from "@/lib/alley-score";
import {
  useSignalScoreDetails,
  useSignalScoreGaps,
  useSignalScoreHistory,
  useSignalScoreStrengths,
  useImprovementGuidance,
  useRecalculateScore,
  useCalculateScore,
  priorityColor,
  type DimensionScore,
  type CriterionScore,
  type GapItem,
  type StrengthItem,
  type ImprovementAction,
} from "@/lib/signal-score";
import { useProject } from "@/lib/projects";
import { usePermission } from "@/lib/auth";
import { AIFeedback } from "@/components/ai-feedback";
import { CitationBadges } from "@/components/citations/citation-badges";
import { LineagePanel } from "@/components/lineage/lineage-panel";
import {
  useScoreHistoryTrend,
  useScoreVolatility,
  useScoreChanges,
  useBenchmarkComparison,
} from "@/lib/metrics";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface SignalScoreDetailProps {
  projectId: string;
  backHref: string;
  backLabel?: string;
}

// ── Score color helpers (0–100 scale) ─────────────────────────────────────────

/** Returns a hex color for a score value — used for rings, numbers, and inline styles. */
function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 70) return "#3b82f6";
  if (score >= 60) return "#f59e0b";
  if (score >= 50) return "#eab308";
  return "#ef4444";
}

function ratingColor(score: number) {
  if (score >= 80) return "bg-green-100 text-green-700";
  if (score >= 70) return "bg-blue-100 text-blue-700";
  if (score >= 60) return "bg-amber-100 text-amber-700";
  if (score >= 50) return "bg-yellow-100 text-yellow-700";
  return "bg-red-100 text-red-700";
}

function ratingBorder(score: number) {
  if (score >= 80) return "border-green-200 bg-green-50";
  if (score >= 70) return "border-blue-200 bg-blue-50";
  if (score >= 60) return "border-amber-200 bg-amber-50";
  if (score >= 50) return "border-yellow-200 bg-yellow-50";
  return "border-red-200 bg-red-50";
}

function ratingBarColor(score: number) {
  if (score >= 80) return "bg-green-500";
  if (score >= 70) return "bg-blue-500";
  if (score >= 60) return "bg-amber-500";
  if (score >= 50) return "bg-yellow-400";
  return "bg-red-400";
}

function ratingTextColor(score: number) {
  if (score >= 80) return "text-green-600";
  if (score >= 70) return "text-blue-600";
  if (score >= 60) return "text-amber-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

// ── Score Change Badge ────────────────────────────────────────────────────────

function ScoreChangeBadge({ change }: { change: number | null }) {
  if (change === null) return null;
  if (change > 0)
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-sm font-semibold text-green-700">
        <TrendingUp className="h-3.5 w-3.5" />+{change.toFixed(1)}
      </span>
    );
  if (change < 0)
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-sm font-semibold text-red-700">
        <TrendingDown className="h-3.5 w-3.5" />
        {change.toFixed(1)}
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-sm font-medium text-neutral-500">
      <Minus className="h-3.5 w-3.5" />
      No change
    </span>
  );
}

// ── Circular Score Ring ───────────────────────────────────────────────────────

function ScoreRing({ score, size = 200 }: { score: number; size?: number }) {
  const strokeWidth = 14;
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(score, 0), 100) / 100;
  const offset = circ * (1 - pct);
  const cx = size / 2;
  const color = scoreColor(score);

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth} />
      <circle
        cx={cx}
        cy={cx}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 800ms ease-out" }}
      />
    </svg>
  );
}

// ── Hero Score Card ────────────────────────────────────────────────────────────

function HeroScoreCard({
  projectId,
  score,
  label,
  projectName,
  sector,
  calculatedAt,
  version,
  modelUsed,
  previousScore,
  scoreDelta,
}: {
  projectId: string;
  score: number;
  label: string;
  projectName: string;
  sector?: string | null;
  calculatedAt: string;
  version?: number;
  modelUsed?: string;
  previousScore?: number;
  scoreDelta: number | null;
}) {
  const displayScore = Math.round(score);

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-neutral-900">Last Generated Score</h2>
        <p className="mt-1 text-sm font-medium text-neutral-700">
          {projectName}
          {sector && <span className="text-neutral-400"> · {sector}</span>}
        </p>
        <p className="mt-0.5 text-xs text-neutral-400">
          {new Date(calculatedAt).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
          {version != null && ` · v${version}`}
          {modelUsed && ` · ${modelUsed}`}
        </p>
      </div>

      <div className="flex flex-col items-center">
        <div className="relative">
          <ScoreRing score={displayScore} size={200} />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="font-bold tabular-nums leading-none"
              style={{ fontSize: "88px", color: scoreColor(displayScore) }}
            >
              {displayScore}
            </span>
          </div>
        </div>
        <p className="mt-3 text-sm text-gray-500">
          Project Readiness Score ·{" "}
          <span className="font-medium text-neutral-700">{label}</span>
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <ScoreChangeBadge change={scoreDelta} />
          {previousScore !== undefined && (
            <span className="text-xs text-neutral-400">Previous: {previousScore.toFixed(1)}</span>
          )}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-center gap-2 border-t border-neutral-100 pt-4">
        <VolatilityBadge projectId={projectId} />
        <LineagePanel
          entityType="project"
          entityId={projectId}
          fieldName="signal_score"
          fieldLabel="Signal Score"
        />
        <AIFeedback
          taskType="score_quality"
          entityType="project"
          entityId={projectId}
          compact
        />
        <CitationBadges aiTaskLogId={undefined} />
      </div>
    </div>
  );
}

// ── Dimension Section ─────────────────────────────────────────────────────────

function CriterionRow({ criterion }: { criterion: CriterionScore }) {
  const [expanded, setExpanded] = useState(false);
  const ai = criterion.ai_assessment;

  return (
    <div className="border-b last:border-0">
      <button
        onClick={() => ai && setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-neutral-50"
      >
        {ai ? (
          expanded ? (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-neutral-400" />
          )
        ) : (
          <div className="h-4 w-4" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-neutral-900">{criterion.name}</span>
            {criterion.has_document ? (
              <FileCheck className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <span className="text-xs text-neutral-400">No docs</span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2">
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-neutral-100">
              <div
                className={cn(
                  "h-full rounded-full",
                  criterion.score / criterion.max_points >= 0.8
                    ? "bg-green-500"
                    : criterion.score / criterion.max_points >= 0.6
                      ? "bg-amber-500"
                      : "bg-red-400"
                )}
                style={{ width: `${(criterion.score / criterion.max_points) * 100}%` }}
              />
            </div>
            <span className="text-xs text-neutral-400">
              {criterion.score}/{criterion.max_points} pts
            </span>
          </div>
        </div>
      </button>
      {expanded && ai && (
        <div className="space-y-2 border-t bg-neutral-50 px-11 py-3">
          <div className="flex items-start gap-1.5">
            <p className="text-sm text-neutral-600">{ai.reasoning}</p>
            <CitationBadges aiTaskLogId={undefined} className="mt-0.5 shrink-0" />
          </div>
          {ai.strengths.length > 0 && (
            <div>
              <p className="text-xs font-medium text-green-700">Strengths:</p>
              <ul className="ml-4 list-disc text-xs text-neutral-600">
                {ai.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {ai.weaknesses.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700">Weaknesses:</p>
              <ul className="ml-4 list-disc text-xs text-neutral-600">
                {ai.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
          {ai.recommendation && (
            <p className="text-xs text-neutral-500">
              <span className="font-medium">Recommendation:</span> {ai.recommendation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function DimensionSection({ dimension }: { dimension: DimensionScore }) {
  const [open, setOpen] = useState(false);
  const score = Math.round(dimension.score);

  return (
    <Card className={cn("border transition-all duration-200", ratingBorder(score))}>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-black/[0.02]"
      >
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-14 w-14 shrink-0 items-center justify-center rounded-xl text-xl font-bold tabular-nums",
              ratingColor(score)
            )}
          >
            {score}
          </div>
          <div>
            <p className="font-semibold text-neutral-900">{dimension.name}</p>
            <p className="text-xs text-neutral-500">
              Weight: {(dimension.weight * 100).toFixed(0)}% · Completeness:{" "}
              {dimension.completeness_score}% · Quality: {dimension.quality_score}%
            </p>
            <div className="mt-1.5 h-1.5 w-32 overflow-hidden rounded-full bg-neutral-200">
              <div
                className={cn("h-full rounded-full transition-all duration-500", ratingBarColor(score))}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>
        </div>
        {open ? (
          <ChevronUp className="h-5 w-5 shrink-0 text-neutral-400" />
        ) : (
          <ChevronDown className="h-5 w-5 shrink-0 text-neutral-400" />
        )}
      </button>
      {open && dimension.criteria.length > 0 && (
        <div className="border-t">
          {dimension.criteria.map((c) => (
            <CriterionRow key={c.id} criterion={c} />
          ))}
        </div>
      )}
    </Card>
  );
}

// ── Analytics: Volatility Badge ───────────────────────────────────────────────

function VolatilityBadge({ projectId }: { projectId: string }) {
  const { data } = useScoreVolatility(projectId);
  if (!data) return null;

  const config: Record<
    string,
    { label: string; variant: "success" | "warning" | "error" | "neutral" }
  > = {
    low: { label: "Stable", variant: "success" },
    medium: { label: "Moderate", variant: "warning" },
    high: { label: "Volatile", variant: "error" },
    insufficient_data: { label: "Insufficient data", variant: "neutral" },
  };

  const c = config[data.volatility] ?? { label: data.volatility, variant: "neutral" as const };
  return <Badge variant={c.variant}>{c.label}</Badge>;
}

// ── Analytics: Benchmark Comparison ──────────────────────────────────────────

function BenchmarkCard({ projectId }: { projectId: string }) {
  const { data, isLoading } = useBenchmarkComparison(projectId, ["signal_score"]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-5">
          <h3 className="mb-3 text-sm font-semibold text-neutral-900">Benchmark Comparison</h3>
          <div className="h-16 animate-pulse rounded-lg bg-neutral-100" />
        </CardContent>
      </Card>
    );
  }

  const comparison = data?.comparisons?.[0];
  if (!comparison) {
    return (
      <Card>
        <CardContent className="p-5">
          <h3 className="mb-2 text-sm font-semibold text-neutral-900">Benchmark Comparison</h3>
          <p className="text-sm text-neutral-400">No peer data available yet</p>
        </CardContent>
      </Card>
    );
  }

  const quartileLabel = `Q${comparison.quartile}`;
  const percentileLabel =
    comparison.percentile_rank >= 75
      ? `Top ${(100 - comparison.percentile_rank).toFixed(0)}%`
      : `${comparison.percentile_rank.toFixed(0)}th percentile`;
  const vsDelta = comparison.vs_median;

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900">
          Benchmark Comparison
          <span className="ml-auto inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
            {percentileLabel}
          </span>
        </h3>
        <div className="flex flex-wrap items-center gap-6">
          <div className="text-center">
            <p className="text-2xl font-bold text-neutral-900">{quartileLabel}</p>
            <p className="text-xs text-neutral-500">Quartile</p>
          </div>
          <div className="text-center">
            <p className={cn("text-2xl font-bold", vsDelta >= 0 ? "text-green-600" : "text-red-600")}>
              {vsDelta >= 0 ? "+" : ""}{vsDelta.toFixed(1)} pts
            </p>
            <p className="text-xs text-neutral-500">vs Median</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold text-neutral-600">{comparison.sample_count}</p>
            <p className="text-xs text-neutral-500">Peers</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Analytics: Score History Chart (time-series) ──────────────────────────────

const DIMENSION_COLORS: Record<string, string> = {
  overall: "#6366f1",
  project_viability: "#22c55e",
  financial_planning: "#3b82f6",
  team_strength: "#f59e0b",
  risk_assessment: "#ef4444",
  esg: "#10b981",
};

function ScoreHistoryChart({ projectId }: { projectId: string }) {
  const { data, isLoading } = useScoreHistoryTrend(projectId);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <h3 className="mb-4 text-sm font-semibold text-neutral-900">Score History</h3>
          <div className="h-64 animate-pulse rounded-lg bg-neutral-100" />
        </CardContent>
      </Card>
    );
  }
  if (!data?.items.length) return null;

  const chartData = data.items.map((pt) => ({
    date: new Date(pt.recorded_at).toLocaleDateString("en-US", {
      month: "short",
      day: "2-digit",
    }),
    Overall: pt.overall_score,
    "Project Viability": pt.project_viability ?? undefined,
    "Financial Planning": pt.financial_planning ?? undefined,
    "Team Strength": pt.team_strength ?? undefined,
    "Risk Assessment": pt.risk_assessment ?? undefined,
    ESG: pt.esg ?? undefined,
  }));

  const lines: Array<{ key: string; color: string }> = [
    { key: "Overall", color: DIMENSION_COLORS.overall },
    { key: "Project Viability", color: DIMENSION_COLORS.project_viability },
    { key: "Financial Planning", color: DIMENSION_COLORS.financial_planning },
    { key: "Team Strength", color: DIMENSION_COLORS.team_strength },
    { key: "Risk Assessment", color: DIMENSION_COLORS.risk_assessment },
    { key: "ESG", color: DIMENSION_COLORS.esg },
  ];

  return (
    <Card>
      <CardContent className="p-6">
        <h3 className="mb-4 text-sm font-semibold text-neutral-900">Score History</h3>
        <ResponsiveContainer width="100%" height={280}>
          <RechartsLineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value: number | undefined) => (value != null ? value.toFixed(1) : "—")}
            />
            {lines.map(({ key, color }) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={color}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </RechartsLineChart>
        </ResponsiveContainer>
        <div className="mt-3 flex flex-wrap gap-3">
          {lines.map(({ key, color }) => (
            <div key={key} className="flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-neutral-500">{key}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Analytics: "What Changed?" ────────────────────────────────────────────────

function WhatChangedCard({
  projectId,
  initialOpen = false,
}: {
  projectId: string;
  initialOpen?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  const { data, isLoading } = useScoreChanges(projectId);
  const events = data?.items ?? [];

  return (
    <Card>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-neutral-50"
      >
        <h3 className="text-sm font-semibold text-neutral-900">What Changed?</h3>
        {open ? (
          <ChevronUp className="h-4 w-4 text-neutral-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-neutral-400" />
        )}
      </button>
      {open && (
        <div className="border-t">
          {isLoading ? (
            <div className="space-y-3 p-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-neutral-100" />
              ))}
            </div>
          ) : !events.length ? (
            <div className="p-4">
              <p className="text-sm text-neutral-400">No change events yet.</p>
            </div>
          ) : (
            <div className="divide-y">
              {[...events]
                .sort(
                  (a, b) =>
                    new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
                )
                .map((event) => {
                  const deltaPos = event.overall_delta >= 0;
                  return (
                    <div key={event.id} className="px-4 py-3">
                      <div className="flex items-start gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-neutral-400">
                              {new Date(event.recorded_at).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </span>
                            <span
                              className={cn(
                                "text-sm font-semibold",
                                deltaPos ? "text-green-600" : "text-red-600"
                              )}
                            >
                              {deltaPos ? "+" : ""}
                              {event.overall_delta.toFixed(1)} pts
                            </span>
                            {event.trigger_event && (
                              <Badge variant="neutral" className="text-[10px]">
                                {event.trigger_event}
                              </Badge>
                            )}
                          </div>
                          {event.dimension_changes.length > 0 && (
                            <p className="mt-1 text-xs text-neutral-500">
                              {event.dimension_changes
                                .map((dc) => {
                                  const sign = dc.delta >= 0 ? "+" : "";
                                  return `${dc.dimension} ${sign}${dc.delta.toFixed(1)}`;
                                })
                                .join(" · ")}
                            </p>
                          )}
                          {event.explanation && (
                            <p className="mt-1 text-xs text-neutral-600">{event.explanation}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ── Readiness Action Plan ─────────────────────────────────────────────────────

const EFFORT_PILL: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

function ActionItemCard({
  gap,
  index,
  guidance,
  projectId,
}: {
  gap: GapItem;
  index: number;
  guidance: ImprovementAction | undefined;
  projectId: string;
}) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const scorePct = gap.max_points > 0 ? gap.current_score / gap.max_points : 0;

  return (
    <div
      className={cn(
        "rounded-xl border transition-all duration-150",
        gap.priority === "high"
          ? "border-red-200 bg-red-50/30"
          : gap.priority === "medium"
            ? "border-amber-200 bg-amber-50/30"
            : "border-neutral-200 bg-neutral-50/50"
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-start gap-3 p-4 text-left hover:bg-black/[0.02]"
      >
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-xs font-bold text-white">
          {index + 1}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={priorityColor(gap.priority)} className="text-[10px]">
              {gap.priority}
            </Badge>
            <span className="text-sm font-medium text-neutral-900">{gap.criterion_name}</span>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-neutral-200">
              <div
                className={cn("h-full rounded-full", ratingBarColor(scorePct * 100))}
                style={{ width: `${scorePct * 100}%` }}
              />
            </div>
            <span className="text-xs text-neutral-400">
              {gap.current_score}/{gap.max_points} pts · {gap.dimension_name}
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {guidance && (
            <>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium",
                  EFFORT_PILL[guidance.effort] ?? EFFORT_PILL.medium
                )}
              >
                {guidance.effort} effort
              </span>
              <span className="text-xs font-semibold text-green-600">
                +{guidance.expected_gain.toFixed(1)} pts
              </span>
            </>
          )}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          )}
        </div>
      </button>
      {expanded && (
        <div className="border-t px-4 pb-4 pt-3">
          {gap.recommendation && (
            <p className="text-sm text-neutral-700">{gap.recommendation}</p>
          )}
          {gap.relevant_doc_types.length > 0 && (
            <div className="mt-3">
              <p className="mb-1.5 text-xs font-medium text-neutral-500">Documents needed:</p>
              <div className="flex flex-wrap gap-1.5">
                {gap.relevant_doc_types.map((dt) => (
                  <Badge key={dt} variant="neutral" className="text-[10px]">
                    {dt.replace("_", " ")}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/projects/${projectId}?tab=dataroom`);
            }}
          >
            <Upload className="mr-1.5 h-3.5 w-3.5" />
            Upload Documents
          </Button>
        </div>
      )}
    </div>
  );
}

type HistoryItem = {
  version: number;
  overall_score: number;
  project_viability_score: number;
  financial_planning_score: number;
  esg_score: number;
  risk_assessment_score: number;
  team_strength_score: number;
  market_opportunity_score: number;
};

type FallbackItem = {
  action: string;
  dimension: string;
  effort: string;
  estimated_impact: number;
};

function ReadinessActionPlan({
  projectId,
  gaps,
  strengths,
  guidance,
  history,
  fallbackRoadmap,
}: {
  projectId: string;
  gaps: GapItem[];
  strengths: StrengthItem[];
  guidance: { top_actions: ImprovementAction[] } | undefined;
  history: { items: HistoryItem[] } | undefined;
  fallbackRoadmap?: FallbackItem[];
}) {
  const guidanceByDimension = useMemo(() => {
    const map = new Map<string, ImprovementAction>();
    guidance?.top_actions.forEach((a) => map.set(a.dimension_name, a));
    return map;
  }, [guidance]);

  const sortedGaps = useMemo(
    () =>
      [...gaps].sort(
        (a, b) => (PRIORITY_ORDER[a.priority] ?? 3) - (PRIORITY_ORDER[b.priority] ?? 3)
      ),
    [gaps]
  );

  const totalPotential = guidance?.top_actions.reduce((s, a) => s + a.expected_gain, 0) ?? 0;

  const hasActions = gaps.length > 0 || (fallbackRoadmap?.length ?? 0) > 0;
  const hasContent = hasActions || strengths.length > 0 || (history?.items.length ?? 0) > 0;
  if (!hasContent) return null;

  const defaultTab = hasActions ? "actions" : strengths.length > 0 ? "strengths" : "history";

  return (
    <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-5 py-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-neutral-900">
          <Zap className="h-4 w-4 text-amber-500" />
          Readiness Action Plan
          {gaps.length > 0 && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
              {gaps.length} gaps
            </span>
          )}
        </h2>
        {totalPotential > 0 && (
          <span className="text-xs text-neutral-400">
            Potential:{" "}
            <span className="font-semibold text-green-600">+{totalPotential.toFixed(1)} pts</span>
          </span>
        )}
      </div>

      <Tabs defaultValue={defaultTab}>
        <TabsList className="w-full justify-start rounded-none border-b px-5">
          {hasActions && (
            <TabsTrigger value="actions">
              Action Items{gaps.length > 0 ? ` (${gaps.length})` : ""}
            </TabsTrigger>
          )}
          {strengths.length > 0 && (
            <TabsTrigger value="strengths">
              What&apos;s Working ({strengths.length})
            </TabsTrigger>
          )}
          {history?.items.length ? (
            <TabsTrigger value="history">Version History</TabsTrigger>
          ) : null}
        </TabsList>

        {/* Action Items */}
        {hasActions && (
          <TabsContent value="actions" className="space-y-3 p-5">
            {gaps.length > 0
              ? sortedGaps.map((gap, i) => (
                  <ActionItemCard
                    key={gap.criterion_id}
                    gap={gap}
                    index={i}
                    guidance={guidanceByDimension.get(gap.dimension_name)}
                    projectId={projectId}
                  />
                ))
              : fallbackRoadmap?.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 rounded-xl border border-neutral-100 bg-neutral-50 px-3 py-3"
                  >
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-xs font-bold text-white">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-neutral-800">{item.action}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
                          {item.dimension.replace(/_/g, " ")}
                        </span>
                        <span
                          className={cn(
                            "rounded px-1.5 py-0.5 text-xs capitalize",
                            effortColor(item.effort)
                          )}
                        >
                          {item.effort} effort
                        </span>
                        <span className="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-700">
                          +{Math.round(item.estimated_impact)} pts
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
          </TabsContent>
        )}

        {/* What's Working */}
        {strengths.length > 0 && (
          <TabsContent value="strengths" className="p-5">
            <div className="space-y-2">
              {strengths.map((s, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg border border-green-100 bg-green-50 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-neutral-800">{s.criterion_name}</p>
                    <p className="text-xs text-neutral-500">{s.dimension_name}</p>
                  </div>
                  <span className={cn("text-sm font-bold", ratingTextColor(s.score))}>
                    {Math.round(s.score)} pts
                  </span>
                </div>
              ))}
            </div>
          </TabsContent>
        )}

        {/* Version History */}
        {history?.items.length ? (
          <TabsContent value="history" className="p-5">
            <Card>
              <CardContent className="p-4">
                <LineChart
                  data={history.items
                    .slice()
                    .reverse()
                    .map((h) => ({
                      version: `v${h.version}`,
                      Overall: h.overall_score,
                      Viability: h.project_viability_score,
                      Financial: h.financial_planning_score,
                      ESG: h.esg_score,
                      Risk: h.risk_assessment_score,
                      Team: h.team_strength_score,
                      Market: h.market_opportunity_score,
                    }))}
                  xKey="version"
                  yKeys={["Overall", "Viability", "Financial", "ESG", "Risk", "Team", "Market"]}
                  height={320}
                />
              </CardContent>
            </Card>
          </TabsContent>
        ) : null}
      </Tabs>
    </div>
  );
}

// ── Main shared component ─────────────────────────────────────────────────────

export function SignalScoreDetail({ projectId, backHref, backLabel }: SignalScoreDetailProps) {
  const router = useRouter();
  const canAnalyze = usePermission("run_analysis", "analysis");

  const { data, isLoading, error } = useProjectScoreDetail(projectId);
  const { data: details } = useSignalScoreDetails(projectId);
  const { data: gaps } = useSignalScoreGaps(projectId);
  const { data: history } = useSignalScoreHistory(projectId);
  const { data: strengths } = useSignalScoreStrengths(projectId);
  const { data: guidance } = useImprovementGuidance(projectId);

  const recalculate = useRecalculateScore();
  const calculate = useCalculateScore();

  const { data: project } = useProject(projectId);
  const resolvedBackLabel =
    backLabel ?? (project?.name ? `Back to ${project.name}` : "Back to Project");
  const sector = project?.project_type?.replace(/_/g, " ") ?? null;

  const heroScore = details?.overall_score ?? Math.min(Math.round(data?.score ?? 0), 100);

  const previousScore = history?.items[1]?.overall_score;
  const scoreDelta =
    history?.items[0] !== undefined && previousScore !== undefined
      ? history.items[0].overall_score - previousScore
      : null;

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-300" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6 p-6">
        <button
          onClick={() => router.push(backHref)}
          className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-[#1B2A4A]"
        >
          <ArrowLeft className="h-4 w-4" />
          {resolvedBackLabel}
        </button>
        <EmptyState
          icon={<ScoreGauge score={0} size={80} strokeWidth={8} label="" />}
          title="No Signal Score"
          description="No Signal Score has been generated for this project yet."
          action={
            canAnalyze ? (
              <Button onClick={() => calculate.mutate(projectId)} disabled={calculate.isPending}>
                Calculate Signal Score
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  const calculatedAt =
    details?.calculated_at ??
    data.calculated_at ??
    data.score_history?.[0]?.date ??
    new Date().toISOString();

  return (
    <div className="space-y-6 p-6">

      {/* Back + action buttons */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push(backHref)}
          className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-[#1B2A4A]"
        >
          <ArrowLeft className="h-4 w-4" />
          {resolvedBackLabel}
        </button>
        <div className="flex items-center gap-2">
          {details && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                router.push(`/projects/${projectId}?tab=business-plan&action=investor_pitch`)
              }
            >
              <FileText className="mr-1.5 h-3.5 w-3.5" />
              Generate Memorandum
            </Button>
          )}
          {canAnalyze && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => recalculate.mutate(projectId)}
              disabled={recalculate.isPending}
            >
              <RefreshCw
                className={cn("mr-1.5 h-3.5 w-3.5", recalculate.isPending && "animate-spin")}
              />
              Recalculate
            </Button>
          )}
        </div>
      </div>

      {/* Hero */}
      <HeroScoreCard
        projectId={projectId}
        score={heroScore}
        label={scoreLabel(heroScore)}
        projectName={data.project_name}
        sector={sector}
        calculatedAt={calculatedAt}
        version={details?.version}
        modelUsed={details?.model_used}
        previousScore={previousScore}
        scoreDelta={scoreDelta}
      />

      {/* Dimension Breakdown — 2×3 grid */}
      {details && details.dimensions.length > 0 && (
        <div>
          <h2 className="mb-4 text-base font-semibold text-neutral-900">Dimension Breakdown</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {details.dimensions.map((dim) => (
              <DimensionSection key={dim.id} dimension={dim} />
            ))}
          </div>
        </div>
      )}

      {/* Generate Memorandum CTA */}
      <Button
        className="w-full bg-[#1B2A4A] py-3.5 text-white hover:bg-[#243660]"
        onClick={() =>
          router.push(`/projects/${projectId}?tab=business-plan&action=investor_pitch`)
        }
      >
        <FileText className="mr-2 h-4 w-4" />
        Generate Project Memorandum
      </Button>

      {/* Analytics row: Benchmark Comparison + What Changed? */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <BenchmarkCard projectId={projectId} />
        <WhatChangedCard projectId={projectId} initialOpen />
      </div>

      {/* Readiness Action Plan — consolidated gap/improvement/strengths/history */}
      <ReadinessActionPlan
        projectId={projectId}
        gaps={gaps?.items ?? []}
        strengths={strengths?.items ?? []}
        guidance={guidance}
        history={history}
        fallbackRoadmap={
          !details && data.gap_analysis.length > 0 ? data.gap_analysis : undefined
        }
      />

      {/* Score History Chart (time-series) */}
      <ScoreHistoryChart projectId={projectId} />
    </div>
  );
}
