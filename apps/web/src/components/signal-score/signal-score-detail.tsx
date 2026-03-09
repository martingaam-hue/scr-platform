"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  BookOpen,
  Briefcase,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  FileCheck,
  FileText,
  Loader2,
  Minus,
  RefreshCw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Upload,
  Users,
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

function ratingColor(score: number) {
  if (score >= 80) return "bg-green-100 text-green-700";
  if (score >= 60) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function ratingBorder(score: number) {
  if (score >= 80) return "border-green-200 bg-green-50";
  if (score >= 60) return "border-amber-200 bg-amber-50";
  return "border-red-200 bg-red-50";
}

function ratingBarColor(score: number) {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-500";
}

function ratingTextColor(score: number) {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

// ── Score Change Badge (matches investor side) ────────────────────────────────

function ScoreChangeBadge({ change }: { change: number | null }) {
  if (change === null) return null;
  if (change > 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-sm font-semibold text-green-700">
        <TrendingUp className="h-3.5 w-3.5" />+{change.toFixed(1)}
      </span>
    );
  }
  if (change < 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-sm font-semibold text-red-700">
        <TrendingDown className="h-3.5 w-3.5" />
        {change.toFixed(1)}
      </span>
    );
  }
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

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth} />
      <circle
        cx={cx}
        cy={cx}
        r={r}
        fill="none"
        stroke="#1a2332"
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

      {/* Ring + score */}
      <div className="flex flex-col items-center">
        <div className="relative">
          <ScoreRing score={displayScore} size={200} />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="font-bold tabular-nums leading-none text-[#1a2332]"
              style={{ fontSize: "88px" }}
            >
              {displayScore}
            </span>
          </div>
        </div>
        <p className="mt-3 text-sm text-gray-500">
          Project Readiness Score ·{" "}
          <span className="font-medium text-neutral-700">{label}</span>
        </p>

        {/* Previous score + change badge — matches investor side layout */}
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <ScoreChangeBadge change={scoreDelta} />
          {previousScore !== undefined && (
            <span className="text-xs text-neutral-400">
              Previous: {previousScore.toFixed(1)}
            </span>
          )}
        </div>
      </div>

      {/* Metadata badges row */}
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

// ── Dimension Section (expandable card, colored rating box) ───────────────────

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
          {/* Colored rating box — replaces ScoreGauge half-circle */}
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
            {/* Score bar */}
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

// ── Gaps to Close ─────────────────────────────────────────────────────────────

function GapsToCloseSection({ gaps }: { gaps: GapItem[] }) {
  if (!gaps.length) return null;

  return (
    <Card className="border-amber-200">
      <CardContent className="p-5">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          Gaps to Close ({gaps.length})
        </h3>
        <ul className="space-y-2">
          {gaps.slice(0, 8).map((gap, i) => (
            <li
              key={i}
              className="flex items-start justify-between gap-2"
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-neutral-700">{gap.criterion_name}</p>
                <p className="text-xs text-neutral-400">{gap.dimension_name}</p>
              </div>
              <Badge variant={priorityColor(gap.priority)} className="shrink-0 text-[10px]">
                {gap.priority}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// ── What's Working ────────────────────────────────────────────────────────────

function WhatsWorkingSection({ strengths }: { strengths: StrengthItem[] }) {
  if (!strengths.length) return null;

  return (
    <Card className="border-green-200">
      <CardContent className="p-5">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          What&apos;s Working ({strengths.length})
        </h3>
        <ul className="space-y-1.5">
          {strengths.map((s, i) => (
            <li key={i} className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-neutral-700">{s.criterion_name}</p>
                <p className="text-xs text-neutral-400">{s.dimension_name}</p>
              </div>
              <span className={cn("shrink-0 text-xs font-semibold", ratingTextColor(s.score))}>
                {Math.round(s.score)} pts
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// ── Improvement Plan ──────────────────────────────────────────────────────────

const EFFORT_PILL: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

function ImprovementPlanSection({ actions }: { actions: ImprovementAction[] }) {
  if (!actions.length) return null;

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900">
          <Zap className="h-4 w-4 text-amber-500" />
          Improvement Plan
          <span className="ml-auto text-xs font-normal text-neutral-400">sorted by impact</span>
        </h3>
        <div className="space-y-3">
          {actions.slice(0, 8).map((action, i) => (
            <div
              key={i}
              className="flex items-start gap-3 rounded-xl border border-neutral-100 bg-neutral-50 px-3 py-2.5"
            >
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-600">
                {i + 1}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-sm font-medium text-neutral-800">{action.action}</p>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        EFFORT_PILL[action.effort] ?? EFFORT_PILL.medium
                      )}
                    >
                      {action.effort} effort
                    </span>
                    <span className="text-xs font-semibold text-green-600">
                      +{action.expected_gain.toFixed(1)} pts
                    </span>
                  </div>
                </div>
                <p className="mt-0.5 text-xs text-neutral-500">{action.dimension_name}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
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
            <p
              className={cn(
                "text-2xl font-bold",
                vsDelta >= 0 ? "text-green-600" : "text-red-600"
              )}
            >
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
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-xs text-neutral-500">{key}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Analytics: "What Changed?" Timeline ──────────────────────────────────────

function WhatChangedCard({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
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

// ── Understanding & Improving ─────────────────────────────────────────────────

function UnderstandingSection() {
  const affects = [
    { Icon: Briefcase, label: "Business Model Strength" },
    { Icon: BarChart3, label: "Financial Projections" },
    { Icon: TrendingUp, label: "Market Opportunity" },
    { Icon: Users, label: "Team Capabilities" },
    { Icon: Sparkles, label: "Competitive Positioning" },
    { Icon: BookOpen, label: "Documentation Quality" },
  ];
  const improve = [
    {
      label: "Strengthen Documentation",
      desc: "Upload your pitch deck, business plan, and financial models.",
    },
    {
      label: "Refine Financials",
      desc: "Provide 3–5 year projections with clear assumptions and sensitivity analysis.",
    },
    {
      label: "Build Your Team",
      desc: "Upload CVs and credentials highlighting sector experience and track record.",
    },
    {
      label: "Validate Market Fit",
      desc: "Include LOIs, MoUs, pilot results, or third-party market reports.",
    },
    {
      label: "Clarify Competitive Advantage",
      desc: "Document IP, partnerships, location advantages, or regulatory approvals.",
    },
  ];

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 className="text-sm font-semibold text-neutral-900">
        Understanding &amp; Improving Your Score
      </h3>
      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">
            What Affects Your Score
          </p>
          <ul className="space-y-2.5">
            {affects.map(({ Icon, label }) => (
              <li key={label} className="flex items-center gap-2.5">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-[#1B2A4A]/8">
                  <Icon className="h-3.5 w-3.5 text-[#1B2A4A]" />
                </div>
                <span className="text-sm text-neutral-700">{label}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">
            How to Improve Your Project Score
          </p>
          <ol className="space-y-2.5">
            {improve.map(({ label, desc }, i) => (
              <li key={label} className="flex items-start gap-2.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-[10px] font-bold text-white">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-neutral-800">{label}</p>
                  <p className="text-xs text-neutral-500">{desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

// ── Main shared component ─────────────────────────────────────────────────────

export function SignalScoreDetail({ projectId, backHref, backLabel }: SignalScoreDetailProps) {
  const router = useRouter();
  const canAnalyze = usePermission("run_analysis", "analysis");

  // Alley API — project metadata + improvement roadmap fallback
  const { data, isLoading, error } = useProjectScoreDetail(projectId);

  // Signal-score API — deep analysis (primary score source for 0-100 accuracy)
  const { data: details } = useSignalScoreDetails(projectId);
  const { data: gaps } = useSignalScoreGaps(projectId);
  const { data: history } = useSignalScoreHistory(projectId);
  const { data: strengths } = useSignalScoreStrengths(projectId);
  const { data: guidance } = useImprovementGuidance(projectId);

  const recalculate = useRecalculateScore();
  const calculate = useCalculateScore();

  // Project metadata for sector + default back label
  const { data: project } = useProject(projectId);
  const resolvedBackLabel =
    backLabel ?? (project?.name ? `Back to ${project.name}` : "Back to Project");
  const sector = project?.project_type?.replace(/_/g, " ") ?? null;

  // Use signal-score API score (accurate 0-100) when available; cap alley score as fallback
  const heroScore = details?.overall_score ?? Math.min(Math.round(data?.score ?? 0), 100);

  // Previous score and delta from version history (items[0] = latest, items[1] = previous)
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

      {/* Hero — score ring + previous score + change badge + metadata */}
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

      {/* Dimension Breakdown — 2×3 grid of expandable, colored-border cards */}
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

      {/* Generate Project Memorandum — full-width */}
      <Button
        className="w-full bg-[#1B2A4A] py-3.5 text-white hover:bg-[#243660]"
        onClick={() =>
          router.push(`/projects/${projectId}?tab=business-plan&action=investor_pitch`)
        }
      >
        <FileText className="mr-2 h-4 w-4" />
        Generate Project Memorandum
      </Button>

      {/* Gaps to Close + What's Working — side by side */}
      {(gaps?.items.length || strengths?.items.length) ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {gaps?.items.length ? <GapsToCloseSection gaps={gaps.items} /> : null}
          {strengths?.items.length ? <WhatsWorkingSection strengths={strengths.items} /> : null}
        </div>
      ) : null}

      {/* Improvement Plan */}
      {guidance?.top_actions.length ? (
        <ImprovementPlanSection actions={guidance.top_actions} />
      ) : !details && data.gap_analysis.length > 0 ? (
        /* Fallback roadmap when deep analysis not yet run */
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900">
              <Zap className="h-4 w-4 text-amber-500" />
              Improvement Roadmap
            </h3>
            <ul className="space-y-3">
              {data.gap_analysis.map((gap, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3"
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-neutral-800">{gap.action}</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
                        {gap.dimension.replace(/_/g, " ")}
                      </span>
                      <span className={cn("rounded px-1.5 py-0.5 text-xs capitalize", effortColor(gap.effort))}>
                        {gap.effort} effort
                      </span>
                      <span className="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-700">
                        +{Math.round(gap.estimated_impact)} pts
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {/* Version history */}
      {history?.items.length ? (
        <Tabs defaultValue="history">
          <TabsList>
            {gaps?.items.length ? (
              <TabsTrigger value="gaps">
                Gaps &amp; Recommendations ({gaps.total})
              </TabsTrigger>
            ) : null}
            <TabsTrigger value="history">Version History</TabsTrigger>
          </TabsList>

          {gaps?.items.length ? (
            <TabsContent value="gaps" className="mt-5 space-y-3">
              {gaps.items.map((gap) => (
                <Card key={gap.criterion_id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant={priorityColor(gap.priority)}>{gap.priority}</Badge>
                          <p className="font-medium text-neutral-900">{gap.criterion_name}</p>
                        </div>
                        <p className="mt-1 text-xs text-neutral-500">
                          {gap.dimension_name} · {gap.current_score}/{gap.max_points} pts
                        </p>
                        <p className="mt-2 text-sm text-neutral-600">{gap.recommendation}</p>
                        {gap.relevant_doc_types.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {gap.relevant_doc_types.map((dt) => (
                              <Badge key={dt} variant="neutral">{dt.replace("_", " ")}</Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/projects/${projectId}?tab=dataroom`)}
                      >
                        <Upload className="mr-1 h-3.5 w-3.5" /> Upload
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>
          ) : null}

          <TabsContent value="history" className="mt-5">
            <Card>
              <CardContent className="p-6">
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
        </Tabs>
      ) : null}

      {/* Benchmark Comparison */}
      <BenchmarkCard projectId={projectId} />

      {/* What Changed? */}
      <WhatChangedCard projectId={projectId} />

      {/* Score History Chart (time-series from metrics API) */}
      <ScoreHistoryChart projectId={projectId} />

      {/* Understanding & Improving Your Score */}
      <UnderstandingSection />
    </div>
  );
}
