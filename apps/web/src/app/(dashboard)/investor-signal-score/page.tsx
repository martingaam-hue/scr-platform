"use client";

import React, { useState } from "react";
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Zap,
  BarChart3,
  Users,
  Target,
  Leaf,
  ShieldCheck,
  DollarSign,
  Trophy,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ScoreGauge,
} from "@scr/ui";
import {
  useInvestorSignalScore,
  useCalculateInvestorScore,
  useScoreHistory,
  useImprovementPlan,
  useScoreFactors,
  useBenchmark,
  useTopMatches,
  scoreColor,
  scoreBgColor,
  scoreBorderColor,
  scoreBarColor,
  dimensionLabel,
  recommendationLabel,
  DIMENSION_KEYS,
  type DimensionScore,
  type InvestorSignalScore,
  type ImprovementAction,
  type ScoreHistoryItem,
  type BenchmarkData,
  type TopMatchItem,
  type ScoreFactorItem,
} from "@/lib/investor-signal-score";

// ── Icon map ──────────────────────────────────────────────────────────────

const DIMENSION_ICONS: Record<string, React.ReactNode> = {
  financial_capacity: <DollarSign className="h-4 w-4" />,
  risk_management: <ShieldCheck className="h-4 w-4" />,
  investment_strategy: <Target className="h-4 w-4" />,
  team_experience: <Users className="h-4 w-4" />,
  esg_commitment: <Leaf className="h-4 w-4" />,
  platform_readiness: <BarChart3 className="h-4 w-4" />,
};

const DIMENSION_DESCRIPTIONS: Record<string, string> = {
  financial_capacity: "Capital availability, deployment pace, and fund lifecycle stage",
  risk_management: "Risk framework, diversification, and compliance processes",
  investment_strategy: "Strategy clarity, thesis documentation, and track record",
  team_experience: "Team size, sector expertise, and deal flow quality",
  esg_commitment: "ESG policy, SFDR classification, and impact measurement",
  platform_readiness: "Profile completeness, mandate specification, and engagement",
};

// ── Score Change Badge ─────────────────────────────────────────────────────

function ScoreChangeBadge({ change }: { change: number | null }) {
  if (change === null) return null;
  if (change > 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-50 border border-green-200 px-2.5 py-1 text-sm font-semibold text-green-700 dark:bg-green-950/20 dark:border-green-900 dark:text-green-400">
        <TrendingUp className="h-3.5 w-3.5" />+{change.toFixed(1)}
      </span>
    );
  }
  if (change < 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 border border-red-200 px-2.5 py-1 text-sm font-semibold text-red-700 dark:bg-red-950/20 dark:border-red-900 dark:text-red-400">
        <TrendingDown className="h-3.5 w-3.5" />
        {change.toFixed(1)}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-neutral-50 border border-neutral-200 px-2.5 py-1 text-sm font-medium text-neutral-500 dark:bg-neutral-800 dark:border-neutral-700">
      <Minus className="h-3.5 w-3.5" />
      No change
    </span>
  );
}

// ── Dimension Card ────────────────────────────────────────────────────────

function DimensionCard({
  dimKey,
  dimension,
}: {
  dimKey: string;
  dimension: DimensionScore;
}) {
  const [expanded, setExpanded] = useState(false);
  const label = dimensionLabel(dimKey);
  const weightPct = Math.round(dimension.weight * 100);
  const detailsData = dimension.details as Record<string, unknown> | null;
  const criteria = detailsData?.criteria as Array<{
    name: string;
    description: string;
    points: number;
    max_points: number;
    met: boolean;
  }> | undefined;
  const criteriaTotal = detailsData?.criteria_total as number | undefined;
  const criteriaMet = detailsData?.criteria_met as number | undefined;

  return (
    <Card className={`border ${scoreBorderColor(dimension.score)} ${scoreBgColor(dimension.score)} transition-all duration-200`}>
      <CardContent className="pt-4 pb-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg ${dimension.score >= 80 ? "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400" : dimension.score >= 60 ? "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400" : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"}`}>
              {DIMENSION_ICONS[dimKey]}
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{label}</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{weightPct}% weight</p>
            </div>
          </div>
          <div className={`text-2xl font-bold ${scoreColor(dimension.score)}`}>
            {dimension.score.toFixed(0)}
          </div>
        </div>

        {/* Score bar */}
        <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 mb-3">
          <div
            className={`h-1.5 rounded-full transition-all duration-500 ${scoreBarColor(dimension.score)}`}
            style={{ width: `${dimension.score}%` }}
          />
        </div>

        {/* Criteria summary */}
        {criteriaMet !== undefined && criteriaTotal !== undefined && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">
            {criteriaMet}/{criteriaTotal} criteria met
          </p>
        )}

        {/* Description */}
        <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed mb-3">
          {DIMENSION_DESCRIPTIONS[dimKey]}
        </p>

        {/* Expand/collapse criteria */}
        {criteria && criteria.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs font-medium text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-colors"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" />
                Hide criteria
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" />
                Show {criteria.length} criteria
              </>
            )}
          </button>
        )}

        {/* Criteria list */}
        {expanded && criteria && (
          <div className="mt-3 space-y-2 border-t border-neutral-200 dark:border-neutral-700 pt-3">
            {criteria.map((c, i) => (
              <div key={i} className="flex items-start gap-2">
                {c.met ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-neutral-300 dark:text-neutral-600 mt-0.5 flex-shrink-0" />
                )}
                <div className="min-w-0 flex-1">
                  <p className={`text-xs font-medium ${c.met ? "text-neutral-800 dark:text-neutral-200" : "text-neutral-500 dark:text-neutral-400"}`}>
                    {c.name}
                  </p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 leading-snug">
                    {c.description}
                  </p>
                </div>
                <span className={`text-xs font-semibold flex-shrink-0 ${c.met ? "text-green-600 dark:text-green-400" : "text-neutral-400 dark:text-neutral-500"}`}>
                  {c.met ? `+${c.points}` : `0/${c.max_points}`}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Score Header ──────────────────────────────────────────────────────────

function ScoreHeader({ score }: { score: InvestorSignalScore }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-col md:flex-row items-center gap-6">
          <div className="flex-shrink-0">
            <ScoreGauge score={score.overall_score} size={160} />
          </div>
          <div className="flex-1 text-center md:text-left">
            <p className="text-sm text-neutral-500 font-medium mb-1">
              Overall Investor Signal Score
            </p>
            <p className={`text-5xl font-bold ${scoreColor(score.overall_score)}`}>
              {score.overall_score.toFixed(1)}
            </p>
            <p className="text-sm text-neutral-400 mt-1">out of 100</p>
            <div className="mt-3 flex flex-wrap gap-2 justify-center md:justify-start">
              <ScoreChangeBadge change={score.score_change} />
              {score.previous_score !== null && (
                <span className="text-xs text-neutral-400 self-center">
                  Previous: {score.previous_score.toFixed(1)}
                </span>
              )}
            </div>
            <p className="text-xs text-neutral-400 mt-3">
              Calculated{" "}
              {new Date(score.calculated_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          </div>
          {/* Dimension mini bars */}
          <div className="hidden lg:block flex-shrink-0 w-52">
            <p className="text-xs font-semibold text-neutral-600 dark:text-neutral-400 mb-2">
              Dimension Scores
            </p>
            <div className="space-y-2">
              {DIMENSION_KEYS.map((key) => {
                const dim = score[key] as DimensionScore;
                return (
                  <div key={String(key)} className="flex items-center gap-2">
                    <span className="text-xs text-neutral-400 w-20 truncate">{dimensionLabel(String(key)).split(" ")[0]}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-neutral-100 dark:bg-neutral-800">
                      <div
                        className={`h-1.5 rounded-full ${scoreBarColor(dim.score)}`}
                        style={{ width: `${dim.score}%` }}
                      />
                    </div>
                    <span className="text-xs text-neutral-500 w-8 text-right">
                      {dim.score.toFixed(0)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Score History ─────────────────────────────────────────────────────────

function ScoreHistorySection({ items }: { items: ScoreHistoryItem[] }) {
  if (items.length < 2) return null;

  const max = Math.max(...items.map((i) => i.overall_score));
  const min = Math.min(...items.map((i) => i.overall_score));
  const range = max - min || 10;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-blue-500" />
          Score History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-1.5 h-16">
          {items.map((item, i) => {
            const height = Math.max(
              8,
              Math.round(((item.overall_score - min) / range) * 56 + 8)
            );
            return (
              <div key={item.id} className="flex flex-col items-center gap-1 flex-1 min-w-0">
                <div
                  className={`w-full rounded-t-sm ${scoreBarColor(item.overall_score)} transition-all duration-300`}
                  style={{ height: `${height}px` }}
                  title={`${item.overall_score.toFixed(1)} — ${new Date(item.calculated_at).toLocaleDateString()}`}
                />
              </div>
            );
          })}
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-xs text-neutral-400">
            {new Date(items[0].calculated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
          <span className="text-xs font-medium text-neutral-600 dark:text-neutral-400">
            {items[items.length - 1].overall_score.toFixed(1)} now
          </span>
          <span className="text-xs text-neutral-400">
            {new Date(items[items.length - 1].calculated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Improvement Plan ──────────────────────────────────────────────────────

function ImprovementPlanSection({ actions }: { actions: ImprovementAction[] }) {
  if (actions.length === 0) return null;

  const effortColor = {
    low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" />
          Improvement Plan
          <span className="ml-auto text-xs font-normal text-neutral-400">
            sorted by impact
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {actions.slice(0, 8).map((action, i) => (
            <div
              key={i}
              className="flex items-start gap-3 rounded-xl border border-neutral-100 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-800/50 px-3 py-2.5"
            >
              <div className="flex-shrink-0 mt-0.5">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 text-xs font-bold">
                  {i + 1}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {action.title}
                  </p>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${effortColor[action.effort_level] ?? effortColor.medium}`}>
                      {action.effort_level} effort
                    </span>
                    <span className="text-xs font-semibold text-green-600 dark:text-green-400">
                      +{action.estimated_impact.toFixed(1)} pts
                    </span>
                  </div>
                </div>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 leading-snug">
                  {action.description}
                </p>
              </div>
              {action.link_to && (
                <a
                  href={action.link_to}
                  className="flex-shrink-0 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
                >
                  <ArrowRight className="h-4 w-4" />
                </a>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Benchmark ─────────────────────────────────────────────────────────────

function BenchmarkSection({ data }: { data: BenchmarkData }) {
  const items = [
    { label: "Your Score", value: data.your_score, color: "bg-blue-500" },
    { label: "Platform Average", value: data.platform_average, color: "bg-neutral-400 dark:bg-neutral-600" },
    { label: "Top Quartile", value: data.top_quartile, color: "bg-green-500" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Trophy className="h-4 w-4 text-yellow-500" />
          Benchmark Comparison
          <span className="ml-auto inline-flex items-center rounded-full bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-900 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:text-blue-300">
            {data.percentile}th percentile
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.label}>
              <div className="flex justify-between mb-1">
                <span className="text-xs text-neutral-600 dark:text-neutral-400">{item.label}</span>
                <span className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">
                  {item.value.toFixed(1)}
                </span>
              </div>
              <div className="h-2 rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className={`h-2 rounded-full ${item.color} transition-all duration-500`}
                  style={{ width: `${item.value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Top Matches ───────────────────────────────────────────────────────────

function TopMatchesSection({ matches }: { matches: TopMatchItem[] }) {
  if (matches.length === 0) return null;

  const recColors: Record<string, string> = {
    strong_fit: "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-900",
    good_fit: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-900",
    marginal_fit: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-900",
    poor_fit: "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-900",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Target className="h-4 w-4 text-purple-500" />
          Top Matching Projects
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {matches.map((match) => (
            <div
              key={match.project_id}
              className="flex items-center gap-3 rounded-xl border border-neutral-100 dark:border-neutral-800 px-3 py-2.5 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">
                  {match.project_name}
                </p>
                {match.geography_country && (
                  <p className="text-xs text-neutral-400 dark:text-neutral-500">
                    {match.geography_country}
                    {match.project_type ? ` · ${match.project_type}` : ""}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${recColors[match.recommendation] ?? recColors.marginal_fit}`}>
                  {recommendationLabel(match.recommendation)}
                </span>
                <span className={`text-sm font-bold ${scoreColor(match.alignment_score)}`}>
                  {match.alignment_score}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Score Factors ─────────────────────────────────────────────────────────

function ScoreFactorsSection({ factors }: { factors: ScoreFactorItem[] }) {
  if (factors.length === 0) return null;

  const positive = factors.filter((f) => f.impact === "positive");
  const negative = factors.filter((f) => f.impact === "negative");

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {positive.length > 0 && (
        <Card className="border-green-200 dark:border-green-900">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              What's Working ({positive.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {positive.map((f, i) => (
                <li key={i} className="flex items-center justify-between gap-2">
                  <span className="text-xs text-neutral-700 dark:text-neutral-300">{f.label}</span>
                  <span className="text-xs font-semibold text-green-600 dark:text-green-400 flex-shrink-0">{f.value}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {negative.length > 0 && (
        <Card className="border-amber-200 dark:border-amber-900">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              Gaps to Close ({negative.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {negative.map((f, i) => (
                <li key={i} className="flex items-center justify-between gap-2">
                  <span className="text-xs text-neutral-700 dark:text-neutral-300">{f.label}</span>
                  <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 flex-shrink-0">{f.value}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────

function NoScoreState({
  onCalculate,
  isLoading,
}: {
  onCalculate: () => void;
  isLoading: boolean;
}) {
  return (
    <EmptyState
      icon={
        <div className="w-20 h-20 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
          <span className="text-3xl font-bold text-neutral-300">—</span>
        </div>
      }
      title="No Signal Score Yet"
      description="Calculate your Investor Signal Score to see how your mandate, risk profile, and platform readiness compare. This score is visible to potential deal partners."
      action={
        <Button onClick={onCalculate} disabled={isLoading} size="lg">
          {isLoading ? (
            <>
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              Calculating...
            </>
          ) : (
            "Calculate Score"
          )}
        </Button>
      }
    />
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function InvestorSignalScorePage() {
  const { data: score, isLoading, isError } = useInvestorSignalScore();
  const { mutate: recalculate, isPending: recalculating } = useCalculateInvestorScore();
  const { data: history = [] } = useScoreHistory(12);
  const { data: improvementPlan = [] } = useImprovementPlan();
  const { data: factors = [] } = useScoreFactors();
  const { data: benchmark } = useBenchmark();
  const { data: topMatches = [] } = useTopMatches(5);

  const handleCalculate = () => recalculate();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-64 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse" />
        <div className="h-48 rounded-xl bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-40 rounded-xl bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <TrendingUp className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
              Investor Signal Score
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Your 6-dimension readiness score shown to potential deal partners
            </p>
          </div>
        </div>
        {score && (
          <Button variant="outline" onClick={handleCalculate} disabled={recalculating}>
            <RefreshCw className={`h-4 w-4 mr-2 ${recalculating ? "animate-spin" : ""}`} />
            {recalculating ? "Recalculating..." : "Recalculate"}
          </Button>
        )}
      </div>

      {/* No score state */}
      {(isError || !score) && !isLoading && (
        <NoScoreState onCalculate={handleCalculate} isLoading={recalculating} />
      )}

      {score && (
        <>
          {/* Score gauge header */}
          <ScoreHeader score={score} />

          {/* Score history */}
          {history.length >= 2 && <ScoreHistorySection items={history} />}

          {/* 6 dimension cards */}
          <div>
            <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-50 mb-4">
              Dimension Breakdown
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {DIMENSION_KEYS.map((key) => (
                <DimensionCard
                  key={String(key)}
                  dimKey={String(key)}
                  dimension={score[key] as DimensionScore}
                />
              ))}
            </div>
          </div>

          {/* Score factors */}
          {factors.length > 0 && <ScoreFactorsSection factors={factors} />}

          {/* Improvement plan */}
          {improvementPlan.length > 0 && (
            <ImprovementPlanSection actions={improvementPlan} />
          )}

          {/* Benchmark + top matches */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {benchmark && <BenchmarkSection data={benchmark} />}
            {topMatches.length > 0 && <TopMatchesSection matches={topMatches} />}
          </div>
        </>
      )}
    </div>
  );
}
