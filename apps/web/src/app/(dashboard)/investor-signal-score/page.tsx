"use client";

import { RefreshCw, TrendingUp, TrendingDown, Minus, AlertCircle } from "lucide-react";
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
  scoreColor,
  scoreBgColor,
  scoreBorderColor,
  dimensionLabel,
  DIMENSION_KEYS,
  type DimensionScore,
  type InvestorSignalScore,
} from "@/lib/investor-signal-score";

// ── Score Change Chip ─────────────────────────────────────────────────────

function ScoreChangeBadge({
  change,
}: {
  change: number | null;
}) {
  if (change === null) return null;

  if (change > 0) {
    return (
      <div className="flex items-center gap-1 text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-1 text-sm font-semibold">
        <TrendingUp className="h-3.5 w-3.5" />+{change.toFixed(1)} since last
        calculation
      </div>
    );
  }
  if (change < 0) {
    return (
      <div className="flex items-center gap-1 text-red-700 bg-red-50 border border-red-200 rounded-full px-2.5 py-1 text-sm font-semibold">
        <TrendingDown className="h-3.5 w-3.5" />
        {change.toFixed(1)} since last calculation
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1 text-gray-500 bg-gray-50 border border-gray-200 rounded-full px-2.5 py-1 text-sm font-medium">
      <Minus className="h-3.5 w-3.5" />
      No change since last calculation
    </div>
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
  const label = dimensionLabel(dimKey);
  const weightPct = Math.round(dimension.weight * 100);

  return (
    <Card
      className={`border ${scoreBorderColor(dimension.score)} ${scoreBgColor(
        dimension.score
      )}`}
    >
      <CardContent className="pt-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm font-semibold text-gray-800">{label}</p>
            <p className="text-xs text-gray-500">{weightPct}% weight</p>
          </div>
          <div
            className={`text-2xl font-bold ${scoreColor(dimension.score)}`}
          >
            {dimension.score.toFixed(0)}
          </div>
        </div>

        {/* Score bar */}
        <div className="h-2 rounded-full bg-gray-200 mb-3">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${
              dimension.score >= 80
                ? "bg-green-500"
                : dimension.score >= 60
                ? "bg-amber-500"
                : "bg-red-500"
            }`}
            style={{ width: `${dimension.score}%` }}
          />
        </div>

        {/* Gaps */}
        {dimension.gaps.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-semibold text-gray-600 mb-1.5">
              Gaps
            </p>
            <ul className="space-y-1">
              {dimension.gaps.slice(0, 2).map((gap, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-xs text-gray-600"
                >
                  <AlertCircle className="h-3 w-3 text-amber-500 mt-0.5 flex-shrink-0" />
                  {gap}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {dimension.recommendations.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-semibold text-gray-600 mb-1.5">
              Recommendations
            </p>
            <ul className="space-y-1">
              {dimension.recommendations.slice(0, 2).map((rec, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-xs text-gray-600"
                >
                  <TrendingUp className="h-3 w-3 text-blue-500 mt-0.5 flex-shrink-0" />
                  {rec}
                </li>
              ))}
            </ul>
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
          {/* Gauge */}
          <div className="flex-shrink-0">
            <ScoreGauge score={score.overall_score} size={160} />
          </div>

          {/* Score info */}
          <div className="flex-1 text-center md:text-left">
            <p className="text-sm text-gray-500 font-medium mb-1">
              Overall Investor Signal Score
            </p>
            <p className={`text-5xl font-bold ${scoreColor(score.overall_score)}`}>
              {score.overall_score.toFixed(1)}
            </p>
            <p className="text-sm text-gray-400 mt-1">out of 100</p>

            <div className="mt-3 flex flex-wrap gap-2 justify-center md:justify-start">
              <ScoreChangeBadge change={score.score_change} />
              {score.previous_score !== null && (
                <span className="text-xs text-gray-400 self-center">
                  Previous: {score.previous_score.toFixed(1)}
                </span>
              )}
            </div>

            <p className="text-xs text-gray-400 mt-3">
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

          {/* Dimension weights summary */}
          <div className="hidden lg:block flex-shrink-0 w-48">
            <p className="text-xs font-semibold text-gray-600 mb-2">
              Dimension Scores
            </p>
            <div className="space-y-1.5">
              {DIMENSION_KEYS.map((key) => {
                const dim = score[key] as DimensionScore;
                return (
                  <div key={String(key)} className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full bg-gray-100">
                      <div
                        className={`h-1.5 rounded-full ${
                          dim.score >= 80
                            ? "bg-green-500"
                            : dim.score >= 60
                            ? "bg-amber-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${dim.score}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-8 text-right">
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
        <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center">
          <span className="text-3xl font-bold text-gray-300">—</span>
        </div>
      }
      title="No Signal Score Yet"
      description="Calculate your Investor Signal Score to see how your mandate, risk profile, and platform readiness compare. This score helps projects identify the best-fit investors."
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
  const { mutate: recalculate, isPending: recalculating } =
    useCalculateInvestorScore();

  const handleCalculate = () => {
    recalculate();
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-10 w-64 bg-gray-100 rounded animate-pulse" />
        <div className="h-48 rounded-xl bg-gray-100 animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-40 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <TrendingUp className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Investor Signal Score
            </h1>
            <p className="text-sm text-gray-500">
              Your 6-dimension readiness score shown to potential deal partners
            </p>
          </div>
        </div>

        {score && (
          <Button
            variant="outline"
            onClick={handleCalculate}
            disabled={recalculating}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${recalculating ? "animate-spin" : ""}`}
            />
            {recalculating ? "Recalculating..." : "Recalculate"}
          </Button>
        )}
      </div>

      {/* No score: empty state with CTA */}
      {(isError || !score) && !isLoading && (
        <NoScoreState
          onCalculate={handleCalculate}
          isLoading={recalculating}
        />
      )}

      {/* Score exists: show full dashboard */}
      {score && (
        <>
          {/* Score gauge header card */}
          <ScoreHeader score={score} />

          {/* 6-dimension cards: 2x3 grid */}
          <div>
            <h2 className="text-base font-semibold text-gray-900 mb-4">
              Dimension Breakdown
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {DIMENSION_KEYS.map((key) => {
                const dim = score[key] as DimensionScore;
                return (
                  <DimensionCard
                    key={String(key)}
                    dimKey={String(key)}
                    dimension={dim}
                  />
                );
              })}
            </div>
          </div>

          {/* Summary: total gaps and recommendations */}
          {(() => {
            const allGaps = DIMENSION_KEYS.flatMap(
              (k) => (score[k] as DimensionScore).gaps
            );
            const allRecs = DIMENSION_KEYS.flatMap(
              (k) => (score[k] as DimensionScore).recommendations
            );
            if (allGaps.length === 0 && allRecs.length === 0) return null;
            return (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {allGaps.length > 0 && (
                  <Card className="border-amber-200">
                    <CardHeader>
                      <CardTitle className="text-sm flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-amber-500" />
                        Identified Gaps ({allGaps.length})
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-1.5">
                        {allGaps.map((gap, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2 text-sm text-gray-700"
                          >
                            <span className="w-1 h-1 rounded-full bg-amber-400 mt-2 flex-shrink-0" />
                            {gap}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {allRecs.length > 0 && (
                  <Card className="border-blue-200">
                    <CardHeader>
                      <CardTitle className="text-sm flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-blue-500" />
                        Recommendations ({allRecs.length})
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-1.5">
                        {allRecs.map((rec, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2 text-sm text-gray-700"
                          >
                            <span className="w-1 h-1 rounded-full bg-blue-400 mt-2 flex-shrink-0" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
