"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  BookOpen,
  Briefcase,
  Calculator,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  FileCheck,
  FileText,
  Leaf,
  Loader2,
  RefreshCw,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Upload,
  Users,
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
  useRecalculateScore,
  useCalculateScore,
  priorityColor,
  type DimensionScore,
  type CriterionScore,
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
  /** The project whose score to display */
  projectId: string;
  /** Where the back button navigates */
  backHref: string;
  /**
   * Label for the back button.
   * If omitted, falls back to "Back to {project.name}" or "Back to Project".
   */
  backLabel?: string;
}

// ── Dimension icon map ────────────────────────────────────────────────────────

const DIM_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  project_viability: Target,
  financial_planning: Calculator,
  team_strength: Users,
  risk_assessment: Shield,
  market_opportunity: BarChart3,
  esg: Leaf,
  esg_impact: Leaf,
};

function getDimIcon(id: string): React.ComponentType<{ className?: string }> {
  return DIM_ICONS[id] ?? Sparkles;
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
}: {
  projectId: string;
  score: number;
  label: string;
  projectName: string;
  sector?: string | null;
  calculatedAt: string;
  version?: number;
  modelUsed?: string;
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
          Latest generated score:{" "}
          {new Date(calculatedAt).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
          {version != null && ` · v${version}`}
          {modelUsed && ` · ${modelUsed}`}
        </p>
      </div>

      {/* Ring + score — centred */}
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

// ── Dimension Bars ────────────────────────────────────────────────────────────

const DIMENSION_WEIGHTS: Record<string, string> = {
  project_viability: "20%",
  financial_planning: "20%",
  team_strength: "15%",
  risk_assessment: "15%",
  market_opportunity: "15%",
  esg: "15%",
  esg_impact: "15%",
};

function DimensionBar({ dim }: { dim: { id: string; label: string; score: number } }) {
  const Icon = getDimIcon(dim.id);
  const weight = DIMENSION_WEIGHTS[dim.id] ?? "";
  const score = Math.round(dim.score);

  return (
    <div className="flex items-center gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1B2A4A]/8">
        <Icon className="h-4 w-4 text-[#1B2A4A]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-neutral-700">{dim.label}</span>
          <span className="shrink-0 text-xs text-neutral-400">{weight}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-100">
            <div
              className="h-full rounded-full bg-[#1B2A4A] transition-all duration-700"
              style={{ width: `${score}%` }}
            />
          </div>
          <span className="w-12 shrink-0 text-right text-sm font-bold tabular-nums text-neutral-700">
            {score}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Key Readiness Indicators ──────────────────────────────────────────────────

const DEFAULT_INDICATORS = [
  "Solid business model with clear path to profitability",
  "Experienced management team with proven track record",
  "Strong market positioning with measurable competitive advantages",
  "Comprehensive documentation and investor-ready materials",
];

function ReadinessIndicators({
  indicators,
}: {
  indicators: Array<{ label: string; met: boolean }>;
}) {
  const items =
    indicators.length > 0
      ? indicators
      : DEFAULT_INDICATORS.map((label) => ({ label, met: true }));

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-900">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          Key Readiness Indicators
        </h3>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {items.map((ind) => (
            <div
              key={ind.label}
              className="flex items-start gap-2.5 rounded-lg bg-neutral-50 px-3 py-2.5 text-sm"
            >
              {ind.met ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
              ) : (
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-neutral-300" />
              )}
              <span className="leading-snug text-gray-600">{ind.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Deep Analysis — CriterionRow ──────────────────────────────────────────────

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
                {ai.strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {ai.weaknesses.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700">Weaknesses:</p>
              <ul className="ml-4 list-disc text-xs text-neutral-600">
                {ai.weaknesses.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
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

// ── Deep Analysis — DimensionSection ─────────────────────────────────────────

function DimensionSection({ dimension }: { dimension: DimensionScore }) {
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-neutral-50"
      >
        <div className="flex items-center gap-4">
          <ScoreGauge score={dimension.score} size={56} strokeWidth={6} label="" />
          <div>
            <p className="font-semibold text-neutral-900">{dimension.name}</p>
            <p className="text-xs text-neutral-500">
              Weight: {(dimension.weight * 100).toFixed(0)}% · Completeness:{" "}
              {dimension.completeness_score}% · Quality: {dimension.quality_score}%
            </p>
          </div>
        </div>
        {open ? (
          <ChevronDown className="h-5 w-5 text-neutral-400" />
        ) : (
          <ChevronRight className="h-5 w-5 text-neutral-400" />
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

// ── Analytics: Score History Chart (time-series from metrics API) ─────────────

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
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{ fontSize: 12 }}
              formatter={(value: number | undefined) =>
                value != null ? value.toFixed(1) : "—"
              }
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

// ── Analytics: Peer Benchmark Card ───────────────────────────────────────────

function BenchmarkCard({ projectId }: { projectId: string }) {
  const { data, isLoading } = useBenchmarkComparison(projectId, ["signal_score"]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-5">
          <h3 className="mb-3 text-sm font-semibold text-neutral-900">Peer Benchmark</h3>
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
          <h3 className="mb-2 text-sm font-semibold text-neutral-900">Peer Benchmark</h3>
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
  const deltaPositive = vsDelta >= 0;

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-4 text-sm font-semibold text-neutral-900">Peer Benchmark</h3>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <p className="text-2xl font-bold text-neutral-900">{quartileLabel}</p>
            <p className="text-xs text-neutral-500">Quartile</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-neutral-900">{percentileLabel}</p>
            <p className="text-xs text-neutral-500">Rank</p>
          </div>
          <div className="text-center">
            <p
              className={cn(
                "text-2xl font-bold",
                deltaPositive ? "text-green-600" : "text-red-600"
              )}
            >
              {deltaPositive ? "+" : ""}
              {vsDelta.toFixed(1)} pts
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

  // Primary data source: alley API (hero, dimension bars, readiness indicators)
  const { data, isLoading, error } = useProjectScoreDetail(projectId);

  // Deep analysis tabs
  const { data: details } = useSignalScoreDetails(projectId);
  const { data: gaps } = useSignalScoreGaps(projectId);
  const { data: history } = useSignalScoreHistory(projectId);

  const recalculate = useRecalculateScore();
  const calculate = useCalculateScore();

  // Project metadata for sector + dynamic back label
  const { data: project } = useProject(projectId);

  const resolvedBackLabel =
    backLabel ?? (project?.name ? `Back to ${project.name}` : "Back to Project");

  const sector = project?.project_type?.replace(/_/g, " ") ?? null;

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-300" />
      </div>
    );
  }

  // No score at all — show empty state with calculate option
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
              <Button
                onClick={() => calculate.mutate(projectId)}
                disabled={calculate.isPending}
              >
                Calculate Signal Score
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  const calculatedAt =
    data.calculated_at ??
    details?.calculated_at ??
    data.score_history?.[0]?.date ??
    new Date().toISOString();

  return (
    <div className="space-y-6 p-6">

      {/* Back + Recalculate */}
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

      {/* Hero score card with ring + analytics badges */}
      <HeroScoreCard
        projectId={projectId}
        score={data.score}
        label={data.score_label || scoreLabel(data.score)}
        projectName={data.project_name}
        sector={sector}
        calculatedAt={calculatedAt}
        version={details?.version}
        modelUsed={details?.model_used}
      />

      {/* 6 Dimension bars — 2-col */}
      {data.dimensions.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-5 text-sm font-semibold text-neutral-900">Dimension Breakdown</h3>
            <div className="grid gap-5 sm:grid-cols-2">
              {data.dimensions.map((dim) => (
                <DimensionBar key={dim.id} dim={dim} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Readiness Indicators */}
      <ReadinessIndicators indicators={data.readiness_indicators} />

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

      {/* ── Deep Analysis Tabs ── */}
      {details && (
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="gaps">
              Gaps &amp; Recommendations
              {gaps && gaps.total > 0 ? ` (${gaps.total})` : ""}
            </TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          {/* Details tab — 2×3 grid of expandable dimension cards */}
          <TabsContent value="details" className="mt-5 grid grid-cols-2 gap-4">
            {details.dimensions.map((dim) => (
              <DimensionSection key={dim.id} dimension={dim} />
            ))}
          </TabsContent>

          {/* Gaps & Recommendations tab */}
          <TabsContent value="gaps" className="mt-5 space-y-3">
            {!gaps?.items.length ? (
              <EmptyState
                icon={<FileCheck className="h-12 w-12 text-neutral-400" />}
                title="No gaps identified"
                description="All criteria are scoring above the threshold."
              />
            ) : (
              gaps.items.map((gap) => (
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
                              <Badge key={dt} variant="neutral">
                                {dt.replace("_", " ")}
                              </Badge>
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
              ))
            )}
          </TabsContent>

          {/* History tab */}
          <TabsContent value="history" className="mt-5">
            {!history?.items.length ? (
              <EmptyState
                icon={<RefreshCw className="h-12 w-12 text-neutral-400" />}
                title="No history yet"
                description="Score history will appear after multiple calculations."
              />
            ) : (
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
            )}
          </TabsContent>
        </Tabs>
      )}

      {/* Improvement roadmap — shown when deep tabs not yet available */}
      {!details && data.gap_analysis.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-4 text-sm font-semibold text-neutral-900">Improvement Roadmap</h3>
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
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-xs capitalize",
                          effortColor(gap.effort)
                        )}
                      >
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
      )}

      {/* Score History Chart (time-series from metrics API) */}
      <ScoreHistoryChart projectId={projectId} />

      {/* Peer Benchmark */}
      <BenchmarkCard projectId={projectId} />

      {/* What Changed? */}
      <WhatChangedCard projectId={projectId} />

      {/* Understanding & Improving Your Score */}
      <UnderstandingSection />
    </div>
  );
}
