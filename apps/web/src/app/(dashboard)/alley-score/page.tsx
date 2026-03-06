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
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  cn,
} from "@scr/ui";
import {
  scoreBadgeClass,
  scoreLabelColor,
  scoreLabel,
  readinessStatus,
  useGenerateScore,
  usePortfolioOverview,
  useTaskStatus,
  type ProjectScoreListItem,
} from "@/lib/alley-score";
import { useProjects } from "@/lib/projects";

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
        Your <strong>Signal Score</strong> is an AI-calculated investment readiness rating (0–100).
        Generate a score by uploading project documents below.
      </span>
      <button onClick={dismiss} className="shrink-0 text-blue-400 hover:text-blue-600">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ── Portfolio Hero Card ────────────────────────────────────────────────────────

function PortfolioHero({
  avg,
  total,
  ready,
}: {
  avg: number;
  total: number;
  ready: number;
}) {
  return (
    <div className="rounded-2xl bg-[#1B2A4A] px-8 py-7 text-white">
      <h2 className="mb-6 text-base font-semibold tracking-wide text-white/70 uppercase">
        Portfolio Signal Score Overview
      </h2>
      <div className="grid grid-cols-3 gap-6">
        <div>
          <p className="text-5xl font-bold tabular-nums">{Math.round(avg)}</p>
          <p className="mt-1.5 text-sm text-white/60">Average Score</p>
          <p className="text-xs text-white/40">out of 100</p>
        </div>
        <div>
          <p className="text-5xl font-bold tabular-nums">{total}</p>
          <p className="mt-1.5 text-sm text-white/60">Total Projects</p>
        </div>
        <div>
          <p className="text-5xl font-bold tabular-nums text-green-400">{ready}</p>
          <p className="mt-1.5 text-sm text-white/60">Investment Ready</p>
          <p className="text-xs text-white/40">score ≥ 80</p>
        </div>
      </div>
    </div>
  );
}

// ── Score Table Row ────────────────────────────────────────────────────────────

function ScoreTableRow({ project }: { project: ProjectScoreListItem }) {
  const score = Math.round(project.score);
  const label = project.score_label || scoreLabel(score);
  const status = project.status || readinessStatus(score);

  return (
    <tr className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
      <td className="py-3 pr-4 pl-6">
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
          <span className={cn("text-2xl font-bold tabular-nums", scoreLabelColor(score))}>
            {score}
          </span>
          {project.trend === "up" && (
            <TrendingUp className="h-3.5 w-3.5 text-green-500" />
          )}
          {project.trend === "down" && (
            <TrendingDown className="h-3.5 w-3.5 text-red-500" />
          )}
        </div>
        <p className="text-xs text-neutral-400">{label}</p>
      </td>
      <td className="px-2 py-3">
        <span
          className={cn(
            "inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold",
            scoreBadgeClass(score)
          )}
        >
          {status}
        </span>
      </td>
      <td className="hidden px-2 py-3 text-xs text-neutral-400 sm:table-cell">
        {new Date(project.calculated_at).toLocaleDateString()}
      </td>
      <td className="py-3 pl-2 pr-6 text-right">
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

// Mobile card fallback
function ScoreCard({ project }: { project: ProjectScoreListItem }) {
  const score = Math.round(project.score);
  const label = project.score_label || scoreLabel(score);
  const status = project.status || readinessStatus(score);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-neutral-900">{project.project_name}</p>
          <p className="text-xs text-neutral-400">{project.sector ?? project.stage ?? "—"}</p>
        </div>
        <div className="text-right">
          <span className={cn("text-2xl font-bold tabular-nums", scoreLabelColor(score))}>
            {score}
          </span>
          <p className="text-xs text-neutral-400">{label}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold",
            scoreBadgeClass(score)
          )}
        >
          {status}
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

// ── Generate Score Panel ───────────────────────────────────────────────────────

function GenerateScorePanel() {
  const [pitchFiles, setPitchFiles] = useState<File[]>([]);
  const [docFiles, setDocFiles] = useState<File[]>([]);
  const [summary, setSummary] = useState("");
  const [projectId, setProjectId] = useState("");
  const [taskId, setTaskId] = useState<string | undefined>();
  const pitchRef = useRef<HTMLInputElement>(null);
  const docsRef = useRef<HTMLInputElement>(null);

  const generate = useGenerateScore();
  const taskStatus = useTaskStatus(taskId);
  const { data: projects } = useProjects();

  function handlePitchFiles(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) setPitchFiles(Array.from(e.target.files));
  }

  function handleDocFiles(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) setDocFiles(Array.from(e.target.files));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const fd = new FormData();
    fd.append("project_id", projectId);
    if (summary) fd.append("project_summary", summary);
    [...pitchFiles, ...docFiles].forEach((f) => fd.append("project_documents", f));
    const result = await generate.mutateAsync(fd);
    setTaskId(result.task_id);
  }

  const isRunning = taskStatus.data?.status === "pending" || taskStatus.data?.status === "running";
  const isDone = taskStatus.data?.status === "completed";
  const isFailed = taskStatus.data?.status === "failed";

  if (isDone) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
          <CheckCircle2 className="h-10 w-10 text-green-500" />
          <p className="font-semibold text-neutral-800">Score generated successfully!</p>
          <p className="text-sm text-neutral-500">Your updated score will appear above shortly.</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => { setTaskId(undefined); setPitchFiles([]); setDocFiles([]); setSummary(""); }}
          >
            Generate Another
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-[#1B2A4A]" />
          Generate New Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Project selector */}
          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-600">
              Project <span className="text-red-500">*</span>
            </label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              required
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/30"
            >
              <option value="">Select a project…</option>
              {projects?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Two upload buttons */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Pitch Deck
              </label>
              <button
                type="button"
                onClick={() => pitchRef.current?.click()}
                className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 py-4 text-xs text-neutral-500 hover:border-[#1B2A4A] hover:text-[#1B2A4A]"
              >
                <FileUp className="h-4 w-4" />
                {pitchFiles.length > 0 ? `${pitchFiles.length} file(s)` : "Upload"}
              </button>
              <input ref={pitchRef} type="file" multiple accept=".pdf,.pptx,.key" onChange={handlePitchFiles} className="sr-only" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">
                Supporting Docs
              </label>
              <button
                type="button"
                onClick={() => docsRef.current?.click()}
                className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 py-4 text-xs text-neutral-500 hover:border-[#1B2A4A] hover:text-[#1B2A4A]"
              >
                <FileUp className="h-4 w-4" />
                {docFiles.length > 0 ? `${docFiles.length} file(s)` : "Upload"}
              </button>
              <input ref={docsRef} type="file" multiple accept=".pdf,.doc,.docx,.xlsx,.csv" onChange={handleDocFiles} className="sr-only" />
            </div>
          </div>

          {/* Summary textarea */}
          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-600">
              Project Summary <span className="text-neutral-400">(optional)</span>
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
                Generate New Score
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ── Understanding & Improving ──────────────────────────────────────────────────

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
          Highest-impact actions across your portfolio to improve investment readiness:
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
                    +{Math.round(item.estimated_impact)} pts
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

// ── Score scale legend ─────────────────────────────────────────────────────────

function ScoreLegend() {
  const levels = [
    { range: "90–100", label: "Excellent", color: "bg-green-900" },
    { range: "80–89",  label: "Strong",    color: "bg-green-700" },
    { range: "70–79",  label: "Good",      color: "bg-teal-700" },
    { range: "60–69",  label: "Fair",      color: "bg-orange-500" },
    { range: "< 60",   label: "Needs Review", color: "bg-red-600" },
  ];

  return (
    <Card>
      <CardContent className="py-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Score Scale
        </p>
        <div className="flex flex-wrap gap-2">
          {levels.map(({ range, label, color }) => (
            <div key={range} className="flex items-center gap-1.5">
              <span className={cn("inline-block h-2 w-2 rounded-full", color)} />
              <span className="text-xs text-neutral-600">
                {range} — {label}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlleyScorePage() {
  const { data, isLoading } = usePortfolioOverview();

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart2 className="h-6 w-6 text-[#1B2A4A]" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">Signal Score</h1>
          <p className="text-sm text-neutral-500">
            AI-calculated investment readiness rating for your projects
          </p>
        </div>
      </div>

      <InfoBanner />

      {/* Portfolio Hero */}
      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-7 w-7 animate-spin text-neutral-400" />
        </div>
      ) : data && data.stats.total_projects > 0 ? (
        <PortfolioHero
          avg={data.stats.avg_score}
          total={data.stats.total_projects}
          ready={data.stats.investment_ready_count}
        />
      ) : null}

      {/* Project Scores Table */}
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
                    <th className="px-2 py-3 text-right pr-6">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {data.projects.map((p) => (
                    <ScoreTableRow key={p.project_id} project={p} />
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

      {/* Score scale legend */}
      <ScoreLegend />

      {/* Generate + Improvement side by side on desktop */}
      <div className="grid gap-6 lg:grid-cols-2">
        <GenerateScorePanel />
        <ImprovementGuide actions={data?.improvement_actions ?? []} />
      </div>
    </div>
  );
}
