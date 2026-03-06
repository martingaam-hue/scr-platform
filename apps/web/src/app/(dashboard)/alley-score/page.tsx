"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Briefcase,
  CheckCircle2,
  FileUp,
  Info,
  Loader2,
  Plus,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
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

const BANNER_KEY = "signal_score_banner_dismissed";

// ── Info Banner ───────────────────────────────────────────────────────────────

function InfoBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setVisible(localStorage.getItem(BANNER_KEY) !== "1");
    }
  }, []);

  if (!visible) return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
      <span className="flex-1">
        <strong>Signal Score</strong> measures your project&apos;s investment readiness based on
        documentation quality, team credentials, business fundamentals, financial projections,
        and overall presentation. Scores range from 0–100.
      </span>
      <button
        onClick={() => { localStorage.setItem(BANNER_KEY, "1"); setVisible(false); }}
        className="shrink-0 text-blue-400 hover:text-blue-600"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ── Portfolio Hero ─────────────────────────────────────────────────────────────

function PortfolioHero({ avg, total, ready }: { avg: number; total: number; ready: number }) {
  return (
    <div className="rounded-2xl bg-[#1B2A4A] px-8 py-10 text-white">
      <p className="mb-8 text-xs font-semibold uppercase tracking-widest text-white/40">
        Portfolio Signal Score Overview
      </p>
      <div className="grid grid-cols-3 divide-x divide-white/10">
        <div className="pr-8">
          <p className="text-7xl font-black tabular-nums leading-none">{Math.round(avg)}</p>
          <p className="mt-3 text-sm font-medium text-white/50">Average Score</p>
          <p className="mt-0.5 text-xs text-white/30">out of 100</p>
        </div>
        <div className="px-8">
          <p className="text-7xl font-black tabular-nums leading-none">{total}</p>
          <p className="mt-3 text-sm font-medium text-white/50">Total Projects</p>
        </div>
        <div className="pl-8">
          <p className="text-7xl font-black tabular-nums leading-none text-green-400">{ready}</p>
          <p className="mt-3 text-sm font-medium text-white/50">Investment Ready</p>
          <p className="mt-0.5 text-xs text-white/30">score ≥ 80</p>
        </div>
      </div>
    </div>
  );
}

// ── Score Table ────────────────────────────────────────────────────────────────

function ScoreTableRow({ project }: { project: ProjectScoreListItem }) {
  const score = Math.round(project.score);
  const label = project.score_label || scoreLabel(score);
  const status = project.status || readinessStatus(score);

  return (
    <tr className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50/60 transition-colors">
      <td className="py-3.5 pr-4 pl-6">
        <p className="font-medium text-neutral-900">{project.project_name}</p>
      </td>
      <td className="hidden px-3 py-3.5 text-sm text-neutral-500 sm:table-cell">
        {project.sector ?? "—"}
      </td>
      <td className="hidden px-3 py-3.5 text-sm text-neutral-500 sm:table-cell">
        {project.stage ?? "—"}
      </td>
      <td className="px-3 py-3.5">
        <div className="flex items-center gap-2">
          <span className={cn("text-xl font-bold tabular-nums", scoreLabelColor(score))}>
            {score}
          </span>
          <span className={cn("text-sm font-medium", scoreLabelColor(score))}>
            {label}
          </span>
          {project.trend === "up" && <TrendingUp className="h-3 w-3 text-green-500" />}
          {project.trend === "down" && <TrendingDown className="h-3 w-3 text-red-500" />}
        </div>
      </td>
      <td className="hidden px-3 py-3.5 sm:table-cell">
        <span
          className={cn(
            "inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold",
            score >= 80
              ? "border-green-700 bg-green-700 text-white"
              : score >= 60
                ? "border-orange-400 text-orange-600"
                : "border-neutral-300 text-neutral-500"
          )}
        >
          {status}
        </span>
      </td>
      <td className="hidden px-3 py-3.5 text-xs text-neutral-400 sm:table-cell">
        {new Date(project.calculated_at).toLocaleDateString("en-GB", {
          day: "numeric", month: "short", year: "numeric",
        })}
      </td>
      <td className="py-3.5 pl-3 pr-6 text-right">
        <Link
          href={`/alley-score/${project.project_id}`}
          className="text-sm font-medium text-[#1B2A4A] hover:underline"
        >
          View Details
        </Link>
      </td>
    </tr>
  );
}

function ScoreMobileCard({ project }: { project: ProjectScoreListItem }) {
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
          <p className={cn("text-2xl font-bold tabular-nums", scoreLabelColor(score))}>{score}</p>
          <p className="text-xs text-neutral-400">{label}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold",
            score >= 80
              ? "border-green-700 bg-green-700 text-white"
              : score >= 60
                ? "border-orange-400 text-orange-600"
                : "border-neutral-300 text-neutral-500"
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

// ── Generate New Score ─────────────────────────────────────────────────────────

function GenerateNewScore() {
  const [projectId, setProjectId] = useState("");
  const [summary, setSummary] = useState("");
  const [docFiles, setDocFiles] = useState<File[]>([]);
  const [teamFiles, setTeamFiles] = useState<File[]>([]);
  const [taskId, setTaskId] = useState<string | undefined>();
  const docRef = useRef<HTMLInputElement>(null);
  const teamRef = useRef<HTMLInputElement>(null);

  const generate = useGenerateScore();
  const taskStatus = useTaskStatus(taskId);
  const { data: projects } = useProjects();

  const isRunning = taskStatus.data?.status === "pending" || taskStatus.data?.status === "running";
  const isDone = taskStatus.data?.status === "completed";
  const isFailed = taskStatus.data?.status === "failed";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const fd = new FormData();
    fd.append("project_id", projectId);
    if (summary) fd.append("project_summary", summary);
    [...docFiles, ...teamFiles].forEach((f) => fd.append("project_documents", f));
    const result = await generate.mutateAsync(fd);
    setTaskId(result.task_id);
  }

  if (isDone) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-green-200 bg-green-50 py-10 text-center">
        <CheckCircle2 className="h-10 w-10 text-green-500" />
        <p className="font-semibold text-neutral-800">Score generated successfully!</p>
        <p className="text-sm text-neutral-500">Your updated score will appear in the table above.</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => { setTaskId(undefined); setDocFiles([]); setTeamFiles([]); setSummary(""); setProjectId(""); }}
        >
          Generate Another
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-neutral-900">Generate New Score</h2>
      <p className="mt-1 text-sm text-neutral-500">
        Update your project details and upload documentation to generate a new readiness score.
      </p>

      <form onSubmit={handleSubmit} className="mt-5 space-y-5">
        {/* Project selector */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-neutral-700">
            Select Project <span className="text-red-500">*</span>
          </label>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            required
            className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/30"
          >
            <option value="">Select a project…</option>
            {projects?.items.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Two upload areas */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-700">
              Upload Project Documents
            </label>
            <button
              type="button"
              onClick={() => docRef.current?.click()}
              className="flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 py-6 text-center text-sm text-neutral-500 transition-colors hover:border-[#1B2A4A] hover:text-[#1B2A4A]"
            >
              <FileUp className="h-5 w-5" />
              <span>
                {docFiles.length > 0
                  ? `${docFiles.length} file${docFiles.length > 1 ? "s" : ""} selected`
                  : "Business plan, pitch deck, financials"}
              </span>
            </button>
            <input
              ref={docRef}
              type="file"
              multiple
              accept=".pdf,.pptx,.key,.doc,.docx,.xlsx"
              onChange={(e) => e.target.files && setDocFiles(Array.from(e.target.files))}
              className="sr-only"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-700">
              Upload Team Background
            </label>
            <button
              type="button"
              onClick={() => teamRef.current?.click()}
              className="flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 py-6 text-center text-sm text-neutral-500 transition-colors hover:border-[#1B2A4A] hover:text-[#1B2A4A]"
            >
              <Users className="h-5 w-5" />
              <span>
                {teamFiles.length > 0
                  ? `${teamFiles.length} file${teamFiles.length > 1 ? "s" : ""} selected`
                  : "CVs, track record, credentials"}
              </span>
            </button>
            <input
              ref={teamRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx"
              onChange={(e) => e.target.files && setTeamFiles(Array.from(e.target.files))}
              className="sr-only"
            />
          </div>
        </div>

        {/* Summary */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-neutral-700">
            Project Overview Summary
          </label>
          <textarea
            rows={4}
            placeholder="Describe your project scope, funding target, timeline, key milestones, and impact goals…"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            className="w-full resize-none rounded-lg border border-neutral-300 px-3 py-2.5 text-sm text-neutral-900 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/30"
          />
        </div>

        {isFailed && (
          <p className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">
            Score generation failed. Please try again.
          </p>
        )}

        <Button
          type="submit"
          disabled={generate.isPending || isRunning || !projectId}
          className="w-full bg-[#1B2A4A] py-3 text-white hover:bg-[#243660]"
        >
          {generate.isPending || isRunning ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {isRunning ? "Generating score…" : "Submitting…"}
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate New Score
            </>
          )}
        </Button>
      </form>
    </div>
  );
}

// ── Understanding & Improving (bild22 — static content) ───────────────────────

function UnderstandingSection() {
  const affects = [
    { icon: Briefcase, label: "Business Model Strength", desc: "Clarity of value proposition, revenue model, and path to profitability" },
    { icon: BarChart3, label: "Financial Projections", desc: "Quality and credibility of financial forecasts and assumptions" },
    { icon: TrendingUp, label: "Market Opportunity", desc: "Size, growth, and accessibility of your target market" },
    { icon: Users, label: "Team Capabilities", desc: "Credentials, experience, and track record of the founding team" },
    { icon: Sparkles, label: "Competitive Positioning", desc: "Differentiation, barriers to entry, and sustainable advantages" },
    { icon: BookOpen, label: "Documentation Quality", desc: "Completeness and professionalism of investor-ready materials" },
  ];

  const improve = [
    { label: "Strengthen Documentation", desc: "Upload complete pitch deck, business plan, and financial models. Each document added improves your documentation quality score." },
    { label: "Refine Financials", desc: "Provide detailed 3–5 year projections with clearly stated assumptions. Include sensitivity analysis and break-even timelines." },
    { label: "Build Your Team", desc: "Upload CVs and LinkedIn profiles for key team members. Highlight relevant sector experience and prior exits or project completions." },
    { label: "Validate Market Fit", desc: "Include letters of intent, MoUs, or pilot results. Third-party market reports and customer evidence strengthen this dimension." },
    { label: "Clarify Competitive Advantage", desc: "Document what makes your project uniquely positioned — IP, location, partnerships, regulatory approvals, or technology differentiation." },
  ];

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-neutral-900">
        Understanding &amp; Improving Your Score
      </h2>

      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        {/* What affects your score */}
        <div>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            What Affects Your Score
          </h3>
          <ul className="space-y-3">
            {affects.map(({ icon: Icon, label, desc }) => (
              <li key={label} className="flex items-start gap-3">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#1B2A4A]/8">
                  <Icon className="h-4 w-4 text-[#1B2A4A]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900">{label}</p>
                  <p className="text-xs text-neutral-500">{desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* How to improve */}
        <div>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            How to Improve Your Project Score
          </h3>
          <ol className="space-y-3">
            {improve.map(({ label, desc }, i) => (
              <li key={label} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-[11px] font-bold text-white">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-neutral-900">{label}</p>
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlleyScorePage() {
  const { data, isLoading } = usePortfolioOverview();
  const router = useRouter();

  return (
    <div className="mx-auto max-w-5xl space-y-7 px-4 py-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Project Signal Score</h1>
        <p className="mt-1 text-sm text-neutral-500">
          AI-powered project readiness and investor matching profile scoring
        </p>
      </div>

      <InfoBanner />

      {/* Portfolio hero */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-7 w-7 animate-spin text-neutral-300" />
        </div>
      ) : data && data.stats.total_projects > 0 ? (
        <PortfolioHero
          avg={data.stats.avg_score}
          total={data.stats.total_projects}
          ready={data.stats.investment_ready_count}
        />
      ) : null}

      {/* Generate New Score */}
      <GenerateNewScore />

      {/* Project Scores Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Individual Project Scores</CardTitle>
          <Button
            size="sm"
            className="bg-[#1B2A4A] text-white hover:bg-[#243660]"
            onClick={() => router.push("/projects/new")}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add New Project
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-300" />
            </div>
          ) : data && data.projects.length > 0 ? (
            <>
              {/* Desktop table */}
              <div className="hidden overflow-x-auto sm:block">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                      <th className="px-6 py-3">Project Name</th>
                      <th className="px-3 py-3">Sector</th>
                      <th className="px-3 py-3">Stage</th>
                      <th className="px-3 py-3">Score</th>
                      <th className="px-3 py-3">Status</th>
                      <th className="px-3 py-3">Last Updated</th>
                      <th className="px-3 py-3 pr-6 text-right">Actions</th>
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
                  <ScoreMobileCard key={p.project_id} project={p} />
                ))}
              </div>
              {/* Footer */}
              <p className="border-t border-neutral-100 px-6 py-3 text-xs text-neutral-400">
                Each project is evaluated individually based on its unique metrics, documentation quality,
                team credentials, and alignment with investor preferences. Upload comprehensive project
                documentation to improve individual scores.
              </p>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BarChart3 className="mb-3 h-10 w-10 text-neutral-200" />
              <p className="text-sm font-semibold text-neutral-600">No scores yet</p>
              <p className="mt-1 max-w-xs text-xs text-neutral-400">
                Generate your first signal score by selecting a project and uploading documents above.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Understanding & Improving */}
      <UnderstandingSection />
    </div>
  );
}
