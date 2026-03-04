"use client";

import { useState } from "react";
import { Loader2, TrendingUp, TrendingDown, Minus, BarChart2, Target } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  cn,
} from "@scr/ui";
import {
  useAlleyScores,
  useAlleyScoreGaps,
  useAlleyBenchmark,
  scoreColor,
  scoreBg,
  priorityVariant,
  type AlleyProjectScoreSummary,
} from "@/lib/alley-score";

// ── Helpers ──────────────────────────────────────────────────────────────────

const DIMENSION_LABELS: Record<string, string> = {
  project_viability_score: "Viability",
  financial_planning_score: "Financial",
  team_strength_score: "Team",
  risk_assessment_score: "Risk",
  esg_score: "ESG",
  market_opportunity_score: "Market",
};

const DIMENSION_KEYS = [
  "project_viability_score",
  "financial_planning_score",
  "team_strength_score",
  "risk_assessment_score",
  "esg_score",
  "market_opportunity_score",
] as const;

function TrendBadge({ trend, change }: { trend: string; change: number }) {
  if (trend === "new") {
    return <Badge variant="neutral">New</Badge>;
  }
  if (trend === "up") {
    return (
      <Badge variant="success" className="flex items-center gap-1">
        <TrendingUp className="h-3 w-3" />
        +{change.toFixed(1)}
      </Badge>
    );
  }
  if (trend === "down") {
    return (
      <Badge variant="error" className="flex items-center gap-1">
        <TrendingDown className="h-3 w-3" />
        {change.toFixed(1)}
      </Badge>
    );
  }
  return (
    <Badge variant="neutral" className="flex items-center gap-1">
      <Minus className="h-3 w-3" />
      Stable
    </Badge>
  );
}

function DimensionBar({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  const pct = Math.min(100, Math.max(0, score));
  const barColor =
    pct >= 75 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 shrink-0 text-neutral-500">{label}</span>
      <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right font-medium text-neutral-700">
        {pct.toFixed(0)}
      </span>
    </div>
  );
}

// ── Gap Analysis Panel ────────────────────────────────────────────────────────

function GapAnalysisPanel({ projectId }: { projectId: string }) {
  const { data, isLoading } = useAlleyScoreGaps(projectId);
  const benchmark = useAlleyBenchmark(projectId);

  return (
    <div className="border-t border-neutral-100 mt-0 bg-neutral-50 rounded-b-lg px-5 py-4 space-y-4">
      {/* Benchmark row */}
      {benchmark.data && (
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span className="font-medium text-neutral-700">Benchmark:</span>
          <span className="text-neutral-500">
            Your score:{" "}
            <span className={cn("font-bold", scoreColor(benchmark.data.your_score))}>
              {benchmark.data.your_score.toFixed(1)}
            </span>
          </span>
          <span className="text-neutral-400">|</span>
          <span className="text-neutral-500">
            Platform median: <strong>{benchmark.data.platform_median.toFixed(1)}</strong>
          </span>
          <span className="text-neutral-500">
            Top quartile: <strong>{benchmark.data.top_quartile.toFixed(1)}</strong>
          </span>
          <Badge variant="neutral">{benchmark.data.percentile}th percentile</Badge>
          <span className="text-xs text-neutral-400">
            vs {benchmark.data.peer_count} {benchmark.data.peer_asset_type} peers
          </span>
        </div>
      )}

      {/* Gap items */}
      <div>
        <h3 className="text-sm font-semibold text-neutral-800 mb-3">
          Gap Analysis &amp; Action Items
        </h3>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
          </div>
        ) : !data?.gap_items?.length ? (
          <p className="text-sm text-neutral-400 text-center py-6">
            No gap items found for this project.
          </p>
        ) : (
          <div className="space-y-2">
            {data.gap_items.map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-3 bg-white rounded-lg border border-neutral-100 px-4 py-3"
              >
                <div className="flex flex-col gap-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-neutral-700">
                      {item.dimension}
                    </span>
                    <span className="text-neutral-300">›</span>
                    <span className="text-xs text-neutral-500">{item.criterion}</span>
                    <Badge variant={priorityVariant(item.priority)} className="text-xs">
                      {item.priority}
                    </Badge>
                    <Badge variant="neutral" className="text-xs">
                      Effort: {item.effort}
                    </Badge>
                  </div>
                  <p className="text-sm text-neutral-800">{item.action}</p>
                  {item.document_types.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {item.document_types.map((dt) => (
                        <span
                          key={dt}
                          className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded"
                        >
                          {dt}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs text-neutral-400">Score now</p>
                  <p className="text-sm font-bold text-neutral-700">
                    {item.current_score}/{item.max_score}
                  </p>
                  <p className="text-xs text-green-600 font-medium mt-0.5">
                    +{item.estimated_impact} pts
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Project Score Card ────────────────────────────────────────────────────────

function ProjectScoreCard({
  project,
  selected,
  onSelect,
}: {
  project: AlleyProjectScoreSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-white transition-all cursor-pointer overflow-hidden",
        selected
          ? "border-blue-400 shadow-md ring-1 ring-blue-200"
          : "border-neutral-200 hover:border-neutral-300 hover:shadow-sm"
      )}
    >
      {/* Card header */}
      <div className="px-5 pt-4 pb-3" onClick={onSelect}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-neutral-900 truncate">
              {project.project_name}
            </h3>
            <p className="text-xs text-neutral-400 mt-0.5">
              v{project.version} &middot;{" "}
              {new Date(project.calculated_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <span
              className={cn(
                "text-3xl font-bold tabular-nums",
                scoreColor(project.overall_score)
              )}
            >
              {project.overall_score.toFixed(1)}
            </span>
            <TrendBadge trend={project.trend} change={project.score_change} />
          </div>
        </div>

        {/* Dimension bars */}
        <div className="space-y-1.5">
          {DIMENSION_KEYS.map((key) => (
            <DimensionBar
              key={key}
              label={DIMENSION_LABELS[key]}
              score={project[key]}
            />
          ))}
        </div>
      </div>

      {/* View gap analysis button */}
      <div className="px-5 pb-4 pt-1">
        <Button
          size="sm"
          variant={selected ? "default" : "outline"}
          onClick={onSelect}
          className="w-full"
        >
          <Target className="h-3.5 w-3.5 mr-1.5" />
          {selected ? "Hide" : "View"} Gap Analysis
        </Button>
      </div>

      {/* Expanded gap panel */}
      {selected && <GapAnalysisPanel projectId={project.project_id} />}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AlleyScorePage() {
  const { data, isLoading } = useAlleyScores();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null
  );

  function toggleProject(id: string) {
    setSelectedProjectId((prev) => (prev === id ? null : id));
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart2 className="h-6 w-6 text-blue-600" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">
            My Signal Score
          </h1>
          <p className="text-sm text-neutral-500">
            AI-calculated investment readiness scores for your projects
          </p>
        </div>
      </div>

      {/* Summary strip */}
      {data && data.total > 0 && (
        <div className="flex items-center gap-4 text-sm text-neutral-500">
          <span>
            <strong className="text-neutral-800">{data.total}</strong>{" "}
            project{data.total !== 1 ? "s" : ""} scored
          </span>
          {data.items.length > 0 && (
            <span>
              Avg score:{" "}
              <strong className="text-neutral-800">
                {(
                  data.items.reduce((s, p) => s + p.overall_score, 0) /
                  data.items.length
                ).toFixed(1)}
              </strong>
            </span>
          )}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-7 w-7 animate-spin text-neutral-400" />
        </div>
      ) : !data?.items?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20 text-center">
            <BarChart2 className="h-10 w-10 text-neutral-300 mb-3" />
            <h3 className="text-base font-semibold text-neutral-700 mb-1">
              No scores calculated yet
            </h3>
            <p className="text-sm text-neutral-400 max-w-xs">
              Upload project documents and request a signal score calculation to
              see your readiness scores here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-5 sm:grid-cols-1 lg:grid-cols-2">
          {data.items.map((project) => (
            <ProjectScoreCard
              key={project.project_id}
              project={project}
              selected={selectedProjectId === project.project_id}
              onSelect={() => toggleProject(project.project_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
