"use client";

import { useState } from "react";
import { Loader2, TrendingUp, Lightbulb, ChevronDown, ChevronRight } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  LineChart,
  cn,
} from "@scr/ui";
import {
  useScorePerformanceList,
  useScoreJourney,
  useScoreInsights,
  trendVariant,
  trendIcon,
  impactColor,
  type ProjectScorePerformanceSummary,
} from "@/lib/score-journey";

// ── Helpers ──────────────────────────────────────────────────────────────────

function ImprovementBadge({ value }: { value: number }) {
  if (value > 0) {
    return (
      <span className="text-sm font-bold text-green-600">
        +{value.toFixed(1)}
      </span>
    );
  }
  if (value < 0) {
    return (
      <span className="text-sm font-bold text-red-600">{value.toFixed(1)}</span>
    );
  }
  return <span className="text-sm font-bold text-neutral-400">0.0</span>;
}

// ── Journey Panel ─────────────────────────────────────────────────────────────

function JourneyPanel({ projectId }: { projectId: string }) {
  const { data: journeyData, isLoading: loadingJourney } =
    useScoreJourney(projectId);
  const { data: insightsData, isLoading: loadingInsights } =
    useScoreInsights(projectId);

  const chartData =
    journeyData?.journey?.map((pt) => ({
      version: pt.version,
      score: pt.overall_score,
    })) ?? [];

  return (
    <div className="border-t border-neutral-100 bg-neutral-50 px-5 py-5 rounded-b-lg space-y-6">
      {/* Score Journey Timeline */}
      <div>
        <h3 className="text-sm font-semibold text-neutral-800 mb-3">
          Score Journey
        </h3>
        {loadingJourney ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
          </div>
        ) : !chartData.length ? (
          <p className="text-sm text-neutral-400 text-center py-6">
            No score history recorded yet.
          </p>
        ) : (
          <div className="bg-white rounded-lg border border-neutral-100 p-3">
            <LineChart
              data={chartData}
              xKey="version"
              yKeys={["score"]}
              yLabels={{ score: "Overall Score" }}
              height={220}
            />
            {journeyData && (
              <div className="mt-2 text-xs text-neutral-400 text-center">
                {chartData.length} versions recorded &middot; Total improvement:{" "}
                <span
                  className={cn(
                    "font-semibold",
                    journeyData.total_improvement >= 0
                      ? "text-green-600"
                      : "text-red-600"
                  )}
                >
                  {journeyData.total_improvement >= 0 ? "+" : ""}
                  {journeyData.total_improvement.toFixed(1)} pts
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Event labels timeline */}
      {journeyData?.journey?.some((pt) => pt.event_label) && (
        <div>
          <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
            Key Events
          </h4>
          <div className="space-y-1.5">
            {journeyData.journey
              .filter((pt) => pt.event_label)
              .map((pt) => (
                <div
                  key={pt.version}
                  className="flex items-center gap-3 text-sm"
                >
                  <Badge variant="neutral" className="shrink-0">
                    v{pt.version}
                  </Badge>
                  <span className="text-neutral-700">{pt.event_label}</span>
                  <span className="text-neutral-400 text-xs ml-auto">
                    {new Date(pt.calculated_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Score Insights */}
      <div>
        <h3 className="text-sm font-semibold text-neutral-800 mb-3 flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          Score Insights
        </h3>
        {loadingInsights ? (
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
          </div>
        ) : !insightsData?.insights?.length ? (
          <p className="text-sm text-neutral-400 text-center py-4">
            No insights available yet.
          </p>
        ) : (
          <div className="space-y-2">
            {insightsData.insights.map((insight, i) => (
              <div
                key={i}
                className="bg-white border border-neutral-100 rounded-lg px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="neutral" className="text-xs">
                        {insight.dimension}
                      </Badge>
                    </div>
                    <p className="text-sm text-neutral-800 mb-1">
                      {insight.insight}
                    </p>
                    <p className="text-xs text-blue-600">{insight.recommendation}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-xs text-neutral-400">Impact</p>
                    <p className={cn("text-sm", impactColor(insight.estimated_impact))}>
                      +{insight.estimated_impact} pts
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Project Performance Row ───────────────────────────────────────────────────

function ProjectPerformanceRow({
  project,
  expanded,
  onToggle,
}: {
  project: ProjectScorePerformanceSummary;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border border-neutral-200 rounded-lg bg-white overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-neutral-50 transition-colors"
      >
        <div className="shrink-0 text-neutral-400">
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <span className="font-semibold text-neutral-900 truncate block">
            {project.project_name}
          </span>
        </div>

        {/* Stat columns */}
        <div className="hidden sm:flex items-center gap-8">
          <div className="text-center">
            <p className="text-xs text-neutral-400 mb-0.5">Current</p>
            <p className="text-lg font-bold text-neutral-900">
              {project.current_score.toFixed(1)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-neutral-400 mb-0.5">Start</p>
            <p className="text-base font-medium text-neutral-600">
              {project.start_score.toFixed(1)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-neutral-400 mb-0.5">Change</p>
            <ImprovementBadge value={project.total_improvement} />
          </div>
          <div className="text-center">
            <p className="text-xs text-neutral-400 mb-0.5">Versions</p>
            <p className="text-sm font-medium text-neutral-600">
              {project.versions}
            </p>
          </div>
          <div>
            <Badge variant={trendVariant(project.trend)}>
              {trendIcon(project.trend)} {project.trend}
            </Badge>
          </div>
        </div>

        {/* Mobile compact */}
        <div className="flex sm:hidden items-center gap-3">
          <span className="text-lg font-bold text-neutral-900">
            {project.current_score.toFixed(1)}
          </span>
          <Badge variant={trendVariant(project.trend)}>
            {trendIcon(project.trend)}
          </Badge>
        </div>
      </button>

      {expanded && <JourneyPanel projectId={project.project_id} />}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ScoreJourneyPage() {
  const { data, isLoading } = useScorePerformanceList();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function toggle(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <TrendingUp className="h-6 w-6 text-green-600" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">Score Journey</h1>
          <p className="text-sm text-neutral-500">
            Track how your signal scores have improved over time
          </p>
        </div>
      </div>

      {/* Column headers (desktop) */}
      {!isLoading && data?.items && data.items.length > 0 && (
        <div className="hidden sm:flex items-center gap-4 px-5 text-xs font-medium text-neutral-400 uppercase tracking-wide">
          <div className="flex-1">Project</div>
          <div className="w-[340px] flex items-center gap-8 text-center">
            <div className="w-16">Current</div>
            <div className="w-16">Start</div>
            <div className="w-16">Change</div>
            <div className="w-16">Versions</div>
            <div className="w-20">Trend</div>
          </div>
          <div className="w-4" />
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
            <TrendingUp className="h-10 w-10 text-neutral-300 mb-3" />
            <h3 className="text-base font-semibold text-neutral-700 mb-1">
              No score history yet
            </h3>
            <p className="text-sm text-neutral-400 max-w-xs">
              Score journeys appear here as signal scores are recalculated over
              time for your projects.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {data.items.map((project) => (
            <ProjectPerformanceRow
              key={project.project_id}
              project={project}
              expanded={expandedId === project.project_id}
              onToggle={() => toggle(project.project_id)}
            />
          ))}
        </div>
      )}

      {/* Summary footer */}
      {data && data.total > 0 && (
        <div className="text-xs text-neutral-400 text-center">
          Showing {data.items.length} of {data.total} projects
        </div>
      )}
    </div>
  );
}
