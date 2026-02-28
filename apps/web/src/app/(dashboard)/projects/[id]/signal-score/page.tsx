"use client";

import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  FileCheck,
  RefreshCw,
  Upload,
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
import { useState } from "react";
import { useProject } from "@/lib/projects";
import { usePermission } from "@/lib/auth";
import { AIFeedback } from "@/components/ai-feedback";
import {
  useSignalScoreDetails,
  useSignalScoreGaps,
  useSignalScoreHistory,
  useRecalculateScore,
  useCalculateScore,
  scoreColor,
  scoreBgColor,
  priorityColor,
  type DimensionScore,
  type CriterionScore,
} from "@/lib/signal-score";

// ── Helpers ─────────────────────────────────────────────────────────────────

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  const color =
    pct >= 80
      ? "bg-green-500"
      : pct >= 60
        ? "bg-amber-500"
        : pct >= 30
          ? "bg-orange-500"
          : "bg-red-500";
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 rounded-full bg-neutral-200">
        <div
          className={cn("h-2 rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-12 text-right text-sm font-medium text-neutral-700">
        {score}/{max}
      </span>
    </div>
  );
}

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
            <span className="text-sm font-medium text-neutral-900">
              {criterion.name}
            </span>
            {criterion.has_document ? (
              <FileCheck className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <span className="text-xs text-neutral-400">No docs</span>
            )}
          </div>
          <div className="mt-1">
            <ScoreBar score={criterion.score} max={criterion.max_points} />
          </div>
        </div>
      </button>
      {expanded && ai && (
        <div className="border-t bg-neutral-50 px-11 py-3 space-y-2">
          <p className="text-sm text-neutral-600">{ai.reasoning}</p>
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
              <span className="font-medium">Recommendation:</span>{" "}
              {ai.recommendation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function DimensionSection({ dimension }: { dimension: DimensionScore }) {
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-neutral-50"
      >
        <div className="flex items-center gap-4">
          <ScoreGauge
            score={dimension.score}
            size={56}
            strokeWidth={6}
            label=""
          />
          <div>
            <h4 className="font-semibold text-neutral-900">
              {dimension.name}
            </h4>
            <p className="text-xs text-neutral-500">
              Weight: {(dimension.weight * 100).toFixed(0)}% · Completeness:{" "}
              {dimension.completeness_score}% · Quality:{" "}
              {dimension.quality_score}%
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

// ── Page ────────────────────────────────────────────────────────────────────

export default function SignalScorePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const canAnalyze = usePermission("run_analysis", "analysis");

  const { data: project } = useProject(id);
  const { data: details, isLoading } = useSignalScoreDetails(id);
  const { data: gaps } = useSignalScoreGaps(id);
  const { data: history } = useSignalScoreHistory(id);
  const recalculate = useRecalculateScore();
  const calculate = useCalculateScore();

  const handleRecalculate = () => {
    if (id) recalculate.mutate(id);
  };

  const handleCalculate = () => {
    if (id) calculate.mutate(id);
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.push(`/projects/${id}`)}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {project?.name ?? "Project"}
        </button>
        <div className="flex items-start justify-between">
          <h1 className="text-2xl font-bold text-neutral-900">
            Signal Score Analysis
          </h1>
          {canAnalyze && details && (
            <Button
              variant="outline"
              onClick={handleRecalculate}
              disabled={recalculate.isPending}
            >
              <RefreshCw
                className={cn(
                  "mr-2 h-4 w-4",
                  recalculate.isPending && "animate-spin"
                )}
              />
              Recalculate
            </Button>
          )}
        </div>
      </div>

      {!details ? (
        <EmptyState
          icon={
            <ScoreGauge score={0} size={80} strokeWidth={8} label="" />
          }
          title="No Signal Score"
          description="Run a Signal Score analysis to evaluate this project's investment readiness."
          action={
            canAnalyze ? (
              <Button onClick={handleCalculate} disabled={calculate.isPending}>
                Calculate Signal Score
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          {/* Overall + dimension gauges */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-6">
            <Card className="lg:col-span-2">
              <CardContent className="flex flex-col items-center justify-center p-6">
                <ScoreGauge
                  score={details.overall_score}
                  size={140}
                  strokeWidth={12}
                />
                <p className="mt-2 text-xs text-neutral-400">
                  v{details.version} · {details.model_used} ·{" "}
                  {new Date(details.calculated_at).toLocaleDateString()}
                </p>
                <AIFeedback
                  taskType="score_quality"
                  entityType="project"
                  entityId={id}
                  compact
                  className="mt-3"
                />
              </CardContent>
            </Card>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:col-span-4 lg:grid-cols-5">
              {details.dimensions.map((dim) => (
                <Card key={dim.id}>
                  <CardContent className="flex flex-col items-center p-4">
                    <ScoreGauge
                      score={dim.score}
                      size={72}
                      strokeWidth={7}
                      label={dim.name}
                    />
                    <p className="mt-1 text-xs text-neutral-400">
                      {(dim.weight * 100).toFixed(0)}%
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="details">
            <TabsList>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="gaps">
                Gaps & Recommendations{" "}
                {gaps && gaps.total > 0 && `(${gaps.total})`}
              </TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            {/* Details tab */}
            <TabsContent value="details" className="mt-6 space-y-4">
              {details.dimensions.map((dim) => (
                <DimensionSection key={dim.id} dimension={dim} />
              ))}
            </TabsContent>

            {/* Gaps tab */}
            <TabsContent value="gaps" className="mt-6 space-y-3">
              {!gaps?.items.length ? (
                <EmptyState
                  icon={
                    <FileCheck className="h-12 w-12 text-neutral-400" />
                  }
                  title="No gaps identified"
                  description="All criteria are scoring above the threshold."
                />
              ) : (
                gaps.items.map((gap) => (
                  <Card key={gap.criterion_id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <Badge variant={priorityColor(gap.priority)}>
                              {gap.priority}
                            </Badge>
                            <h4 className="font-medium text-neutral-900">
                              {gap.criterion_name}
                            </h4>
                          </div>
                          <p className="mt-1 text-xs text-neutral-500">
                            {gap.dimension_name} · {gap.current_score}/
                            {gap.max_points} points
                          </p>
                          <p className="mt-2 text-sm text-neutral-600">
                            {gap.recommendation}
                          </p>
                          {gap.relevant_doc_types.length > 0 && (
                            <div className="mt-2 flex gap-1">
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
                          onClick={() =>
                            router.push(`/projects/${id}?tab=dataroom`)
                          }
                        >
                          <Upload className="mr-1 h-3.5 w-3.5" />
                          Upload
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            {/* History tab */}
            <TabsContent value="history" className="mt-6">
              {!history?.items.length ? (
                <EmptyState
                  icon={
                    <RefreshCw className="h-12 w-12 text-neutral-400" />
                  }
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
                      yKeys={[
                        "Overall",
                        "Viability",
                        "Financial",
                        "ESG",
                        "Risk",
                        "Team",
                        "Market",
                      ]}
                      height={350}
                    />
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
