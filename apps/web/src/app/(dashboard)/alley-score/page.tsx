"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  BarChart2,
  CheckCircle2,
  ChevronRight,
  FileUp,
  Loader2,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
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
  dimensionBarColor,
  scoreBadgeClass,
  scoreLabelColor,
  useGenerateScore,
  usePortfolioOverview,
  useTaskStatus,
  type ProjectScoreListItem,
} from "@/lib/alley-score";

// ── Constants ─────────────────────────────────────────────────────────────────

const DISMISS_KEY = "alley_score_banner_dismissed";

// ── Info Banner ───────────────────────────────────────────────────────────────

function InfoBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setVisible(localStorage.getItem(DISMISS_KEY) !== "1");
    }
  }, []);

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
      <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
      <span className="flex-1">
        Your <strong>Signal Score</strong> is an AI-calculated investment readiness rating (0–10).
        Generate a score by uploading project documents below.
      </span>
      <button onClick={dismiss} className="shrink-0 text-blue-400 hover:text-blue-600">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ── Portfolio Stats ────────────────────────────────────────────────────────────

function PortfolioMetrics({
  avg,
  total,
  ready,
}: {
  avg: number;
  total: number;
  ready: number;
}) {
  return (
    <div className="grid grid-cols-3 gap-4 sm:gap-6">
      {[
        { label: "Avg Score", value: avg.toFixed(1), sub: "out of 10.0" },
        { label: "Projects Scored", value: total.toString(), sub: "total projects" },
        { label: "Investment Ready", value: ready.toString(), sub: "score ≥ 7.0" },
      ].map(({ label, value, sub }) => (
        <div
          key={label}
          className="flex flex-col items-center justify-center rounded-xl border border-neutral-200 bg-white py-5 text-center shadow-sm"
        >
          <span className="text-3xl font-bold text-[#1B2A4A]">{value}</span>
          <span className="mt-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {label}
          </span>
          <span className="text-xs text-neutral-400">{sub}</span>
        </div>
      ))}
    </div>
  );
}

// ── Dimension mini-bar ────────────────────────────────────────────────────────

function MiniBar({ score }: { score: number }) {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (barRef.current) {
      barRef.current.style.transition = "width 700ms ease-out";
      barRef.current.style.width = `${score}%`;
    }
  }, [score]);

  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
      <div
        ref={barRef}
        style={{ width: "0%" }}
        className={cn("h-full rounded-full", dimensionBarColor(score))}
      />
    </div>
  );
}

// ── Score Table Row ────────────────────────────────────────────────────────────

function ScoreTableRow({ project }: { project: ProjectScoreListItem }) {
  return (
    <tr className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
      <td className="py-3 pr-4">
        <p className="font-medium text-neutral-900">{project.project_name}</p>
        {project.sector && (
          <p className="text-xs text-neutral-400">{project.sector}</p>
        )}
      </td>
      <td className="hidden px-2 py-3 text-sm text-neutral-500 sm:table-cell">
        {project.stage ?? "—"}
      </td>
      <td className="px-2 py-3">
        <div className="flex items-center gap-2">
          <span className={cn("text-xl font-bold", scoreLabelColor(project.score_label_color))}>
            {project.score.toFixed(1)}
          </span>
          {project.trend === "up" && (
            <TrendingUp className="h-3.5 w-3.5 text-green-500" />
          )}
          {project.trend === "down" && (
            <TrendingDown className="h-3.5 w-3.5 text-red-500" />
          )}
        </div>
        <p className="text-xs text-neutral-400">{project.score_label}</p>
      </td>
      <td className="px-2 py-3">
        <span
          className={cn(
            "inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold",
            scoreBadgeClass(project.status)
          )}
        >
          {project.status}
        </span>
      </td>
      <td className="hidden px-2 py-3 text-xs text-neutral-400 sm:table-cell">
        {new Date(project.calculated_at).toLocaleDateString()}
      </td>
      <td className="py-3 pl-2 text-right">
        <Link
          href={`/alley-score/${project.project_id}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-[#1B2A4A] hover:underline"
        >
          View <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </td>
    </tr>
  );
}

// Mobile card fallback for the table
function ScoreCard({ project }: { project: ProjectScoreListItem }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-neutral-900">{project.project_name}</p>
          <p className="text-xs text-neutral-400">{project.sector ?? project.stage ?? "—"}</p>
        </div>
        <div className="text-right">
          <span className={cn("text-2xl font-bold", scoreLabelColor(project.score_label_color))}>
            {project.score.toFixed(1)}
          </span>
          <p className="text-xs text-neutral-400">{project.score_label}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold",
            scoreBadgeClass(project.status)
          )}
        >
          {project.status}
        </span>
        <Link
          href={`/alley-score/${project.project_id}`}
          className="text-sm font-medium text-[#1B2A4A] hover:underline"
        >
          View Details →
        </Link>
      </div>
    </div>
  );
}

// ── Generate Score Card ────────────────────────────────────────────────────────

function GenerateScoreCard() {
  const [files, setFiles] = useState<File[]>([]);
  const [summary, setSummary] = useState("");
  const [projectId, setProjectId] = useState("");
  const [taskId, setTaskId] = useState<string | undefined>();
  const generate = useGenerateScore();
  const taskStatus = useTaskStatus(taskId);

  function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) setFiles(Array.from(e.target.files));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const fd = new FormData();
    fd.append("project_id", projectId);
    if (summary) fd.append("project_summary", summary);
    files.forEach((f) => fd.append("project_documents", f));
    const result = await generate.mutateAsync(fd);
    setTaskId(result.task_id);
  }

  const isRunning = taskStatus.data?.status === "pending" || taskStatus.data?.status === "running";
  const isDone = taskStatus.data?.status === "completed";
  const isFailed = taskStatus.data?.status === "failed";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-[#1B2A4A]" />
          Generate New Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isDone ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
            <p className="font-semibold text-neutral-800">Score generated successfully!</p>
            <p className="text-sm text-neutral-500">Refresh the page to see your updated score.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Project ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                placeholder="Paste your project UUID"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                required
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/30"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Project Documents
              </label>
              <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 px-4 py-6 text-sm text-neutral-500 hover:border-[#1B2A4A] hover:text-[#1B2A4A]">
                <FileUp className="h-5 w-5" />
                <span>
                  {files.length > 0
                    ? `${files.length} file${files.length > 1 ? "s" : ""} selected`
                    : "Click to upload PDFs, pitch decks, financials"}
                </span>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.pptx,.xlsx,.csv"
                  onChange={handleFiles}
                  className="sr-only"
                />
              </label>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Project Summary (optional)
              </label>
              <textarea
                rows={3}
                placeholder="Brief description of your project, technology, and impact goals…"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="w-full resize-none rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/30"
              />
            </div>

            {isFailed && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                Score generation failed. Please try again.
              </p>
            )}

            <Button
              type="submit"
              disabled={generate.isPending || isRunning || !projectId}
              className="w-full bg-[#1B2A4A] text-white hover:bg-[#243660]"
            >
              {generate.isPending || isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isRunning ? "Generating…" : "Submitting…"}
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Signal Score
                </>
              )}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}

// ── Improvement Guide ─────────────────────────────────────────────────────────

function ImprovementGuide({
  actions,
}: {
  actions: Array<{ action: string; dimension: string; priority: string; estimated_impact: number }>;
}) {
  if (!actions.length) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Understanding &amp; Improving Your Score</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-neutral-500">
          These are the highest-impact actions across your portfolio to improve your investment readiness score:
        </p>
        <ul className="space-y-2">
          {actions.map((item, i) => (
            <li key={i} className="flex items-start gap-3 rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-xs font-bold text-white">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-neutral-800">{item.action}</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
                    {item.dimension.replace(/_/g, " ")}
                  </span>
                  <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 capitalize">
                    {item.priority} priority
                  </span>
                  <span className="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-700">
                    +{item.estimated_impact.toFixed(1)} pts
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlleyScorePage() {
  const { data, isLoading } = usePortfolioOverview();

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart2 className="h-6 w-6 text-[#1B2A4A]" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">My Signal Score</h1>
          <p className="text-sm text-neutral-500">
            AI-calculated investment readiness rating for your projects
          </p>
        </div>
      </div>

      <InfoBanner />

      {/* Section 1 — Portfolio Overview */}
      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-7 w-7 animate-spin text-neutral-400" />
        </div>
      ) : data && data.stats.total_projects > 0 ? (
        <PortfolioMetrics
          avg={data.stats.avg_score}
          total={data.stats.total_projects}
          ready={data.stats.investment_ready_count}
        />
      ) : null}

      {/* Section 2 — Project Scores Table */}
      {data && data.projects.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Project Scores</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {/* Desktop table */}
            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-400">
                    <th className="px-6 py-3">Project</th>
                    <th className="px-2 py-3">Stage</th>
                    <th className="px-2 py-3">Score</th>
                    <th className="px-2 py-3">Status</th>
                    <th className="px-2 py-3">Date</th>
                    <th className="px-2 py-3 text-right">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100 px-6">
                  {data.projects.map((p) => (
                    <tr key={p.project_id} className="px-6">
                      <ScoreTableRow project={p} />
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Mobile cards */}
            <div className="space-y-3 p-4 sm:hidden">
              {data.projects.map((p) => (
                <ScoreCard key={p.project_id} project={p} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!isLoading && (!data || data.projects.length === 0) && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20 text-center">
            <BarChart2 className="mb-3 h-10 w-10 text-neutral-300" />
            <h3 className="mb-1 text-base font-semibold text-neutral-700">No scores yet</h3>
            <p className="max-w-xs text-sm text-neutral-400">
              Generate your first signal score below by uploading project documents.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Sections 3 & 4 — Generate + Improvement Guide (side by side on desktop) */}
      <div className="grid gap-6 lg:grid-cols-2">
        <GenerateScoreCard />
        <ImprovementGuide actions={data?.improvement_actions ?? []} />
      </div>
    </div>
  );
}
