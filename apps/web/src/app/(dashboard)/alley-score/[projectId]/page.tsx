"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertCircle,
  FileText,
  Loader2,
  TrendingUp,
} from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  cn,
} from "@scr/ui";
import { LineChart } from "@scr/ui";
import {
  dimensionBarColor,
  effortColor,
  scoreLabelColor,
  useProjectScoreDetail,
  type DimensionBreakdown,
  type GapAction,
} from "@/lib/alley-score";

// ── Hero Score ────────────────────────────────────────────────────────────────

function HeroScore({
  score,
  label,
  color,
  projectName,
}: {
  score: number;
  label: string;
  color: string;
  projectName: string;
}) {
  return (
    <div className="relative flex flex-col items-center justify-center overflow-hidden rounded-2xl bg-[#1B2A4A] px-8 py-12 text-center text-white">
      {/* Radial glow */}
      <div
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          background: `radial-gradient(circle at 50% 60%, rgba(99,179,237,0.5) 0%, transparent 70%)`,
        }}
      />
      <p className="relative z-10 text-sm font-medium uppercase tracking-widest text-blue-200">
        Signal Score
      </p>
      <p
        className={cn(
          "relative z-10 mt-2 font-bold leading-none tabular-nums",
          "text-[80px] sm:text-[100px]",
          scoreLabelColor(color)
        )}
      >
        {score.toFixed(1)}
      </p>
      <p className="relative z-10 mt-1 text-lg font-semibold text-white/80">{label}</p>
      <p className="relative z-10 mt-3 text-sm text-blue-200/70">{projectName}</p>
    </div>
  );
}

// ── Animated Dimension Bar ────────────────────────────────────────────────────

function DimensionBar({ label, score }: { label: string; score: number }) {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (barRef.current) {
      barRef.current.style.transition = "width 700ms ease-out";
      barRef.current.style.width = `${score}%`;
    }
  }, [score]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-neutral-700">{label}</span>
        <span className="text-sm font-bold text-neutral-600">
          {(score / 10).toFixed(1)}
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-neutral-100">
        <div
          ref={barRef}
          style={{ width: "0%" }}
          className={cn("h-full rounded-full", dimensionBarColor(score))}
        />
      </div>
    </div>
  );
}

// ── Readiness Indicators ──────────────────────────────────────────────────────

function ReadinessIndicators({
  indicators,
}: {
  indicators: Array<{ label: string; met: boolean }>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Key Readiness Indicators</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {indicators.map((ind) => (
          <div
            key={ind.label}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm",
              ind.met ? "bg-green-50 text-green-800" : "bg-orange-50 text-orange-700"
            )}
          >
            {ind.met ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0 text-orange-400" />
            )}
            {ind.label}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Score Breakdown Accordion ─────────────────────────────────────────────────

function BreakdownAccordion({ breakdown }: { breakdown: DimensionBreakdown[] }) {
  const [open, setOpen] = useState<string | null>(null);

  if (!breakdown.length) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Score Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 p-0 pb-4">
        {breakdown.map((dim) => {
          const isOpen = open === dim.dimension_id;
          return (
            <div key={dim.dimension_id} className="border-b border-neutral-100 last:border-0">
              <button
                onClick={() => setOpen(isOpen ? null : dim.dimension_id)}
                className="flex w-full items-center justify-between px-6 py-3 text-left text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                <span>{dim.dimension_name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-neutral-400">
                    {(dim.score / 10).toFixed(1)} / 10
                  </span>
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4 text-neutral-400" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-neutral-400" />
                  )}
                </div>
              </button>
              {isOpen && dim.criteria.length > 0 && (
                <div className="divide-y divide-neutral-50 px-6 pb-3">
                  {dim.criteria.map((c) => (
                    <div key={c.id} className="flex items-start gap-3 py-2">
                      <div className="mt-0.5">
                        {c.status === "met" ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : c.status === "partial" ? (
                          <AlertCircle className="h-4 w-4 text-amber-400" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-neutral-300" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-neutral-700">{c.name}</p>
                        {c.evidence_note && (
                          <p className="mt-0.5 text-xs text-neutral-400">{c.evidence_note}</p>
                        )}
                      </div>
                      <span className="shrink-0 text-xs text-neutral-400">
                        {c.points_earned}/{c.points_max}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ── Improvement Roadmap ───────────────────────────────────────────────────────

function ImprovementRoadmap({ gaps }: { gaps: GapAction[] }) {
  if (!gaps.length) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Improvement Roadmap</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {gaps.map((gap, i) => (
          <div
            key={i}
            className="flex items-start gap-4 rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3"
          >
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-xs font-bold text-white">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-neutral-800">{gap.action}</p>
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <span className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                  {gap.dimension.replace(/_/g, " ")}
                </span>
                <span
                  className={cn(
                    "rounded px-2 py-0.5 text-xs font-medium capitalize",
                    effortColor(gap.effort)
                  )}
                >
                  {gap.effort} effort
                </span>
                <span className="text-xs text-neutral-400">{gap.timeline}</span>
                <span className="rounded bg-green-50 px-2 py-0.5 text-xs text-green-700">
                  +{gap.estimated_impact.toFixed(1)} pts
                </span>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Score History Chart ───────────────────────────────────────────────────────

function ScoreHistoryChart({
  history,
}: {
  history: Array<{ date: string; score: number }>;
}) {
  if (history.length < 2) return null;

  const data = history.map((h) => ({ date: h.date, score: h.score }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp className="h-4 w-4 text-[#1B2A4A]" />
          Score History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <LineChart
          data={data}
          xKey="date"
          yKeys={["score"]}
          yLabels={{ score: "Signal Score" }}
          height={200}
        />
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProjectScoreDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { data, isLoading, error } = useProjectScoreDetail(projectId);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <AlertCircle className="mx-auto mb-3 h-10 w-10 text-neutral-300" />
        <h2 className="mb-1 text-lg font-semibold text-neutral-700">Score not found</h2>
        <p className="mb-4 text-sm text-neutral-500">
          No signal score has been calculated for this project yet.
        </p>
        <Button variant="outline" onClick={() => router.push("/alley-score")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Scores
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
      {/* Back */}
      <button
        onClick={() => router.push("/alley-score")}
        className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-[#1B2A4A]"
      >
        <ArrowLeft className="h-4 w-4" /> Back to My Scores
      </button>

      {/* Hero */}
      <HeroScore
        score={data.score}
        label={data.score_label}
        color={data.score_label_color}
        projectName={data.project_name}
      />

      {/* Dimensions Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dimension Scores</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {data.dimensions.map((dim) => (
            <DimensionBar key={dim.id} label={dim.label} score={dim.score} />
          ))}
        </CardContent>
      </Card>

      {/* Readiness Indicators */}
      {data.readiness_indicators.length > 0 && (
        <ReadinessIndicators indicators={data.readiness_indicators} />
      )}

      {/* Generate Memorandum CTA */}
      <div className="flex items-center justify-between rounded-xl border border-[#1B2A4A]/20 bg-[#1B2A4A]/5 px-6 py-4">
        <div>
          <p className="font-semibold text-[#1B2A4A]">Generate Project Memorandum</p>
          <p className="text-sm text-neutral-500">
            Create a professional investment memorandum based on your score data.
          </p>
        </div>
        <Button className="shrink-0 bg-[#1B2A4A] text-white hover:bg-[#243660]">
          <FileText className="mr-2 h-4 w-4" />
          Generate PDF
        </Button>
      </div>

      {/* Score Breakdown */}
      {data.criteria_breakdown.length > 0 && (
        <BreakdownAccordion breakdown={data.criteria_breakdown} />
      )}

      {/* Improvement Roadmap */}
      {data.gap_analysis.length > 0 && (
        <ImprovementRoadmap gaps={data.gap_analysis} />
      )}

      {/* Score History */}
      <ScoreHistoryChart history={data.score_history} />
    </div>
  );
}
