"use client";

import { useState } from "react";
import {
  ArrowRight,
  DollarSign,
  Loader2,
  Target,
  TrendingUp,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { Badge, Button, Card, CardContent, EmptyState, cn } from "@scr/ui";
import {
  useProjects,
  useProjectStats,
  formatCurrency,
  type ProjectResponse,
} from "@/lib/projects";
import {
  useAllyRecommendations,
  alignmentColor,
  statusLabel,
  statusVariant,
  type MatchingInvestor,
} from "@/lib/matching";

// ── Helpers ───────────────────────────────────────────────────────────────────

function FundingStageBar({
  stage,
  status,
}: {
  stage: string;
  status: string;
}) {
  const STAGES = [
    "concept",
    "development",
    "ready_to_build",
    "construction",
    "operational",
  ];
  const stageIndex = STAGES.indexOf(stage);
  return (
    <div className="flex items-center gap-1 mt-1">
      {STAGES.map((s, i) => (
        <div
          key={s}
          className={cn(
            "h-1.5 flex-1 rounded-full",
            i <= stageIndex
              ? status === "active"
                ? "bg-indigo-500"
                : "bg-gray-300"
              : "bg-gray-100"
          )}
        />
      ))}
    </div>
  );
}

// ── Project fundraising card ───────────────────────────────────────────────

function ProjectFundingCard({ project }: { project: ProjectResponse }) {
  const { data: matches, isLoading } = useAllyRecommendations(project.id);
  const investors = (matches?.items ?? []) as MatchingInvestor[];
  const interestedCount = investors.filter(
    (m) => m.status === "interested" || m.status === "in_due_diligence"
  ).length;

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-gray-900 truncate">{project.name}</p>
            <p className="text-xs text-gray-500 capitalize mt-0.5">
              {project.project_type.replace(/_/g, " ")} ·{" "}
              {project.geography_country}
            </p>
            <FundingStageBar stage={project.stage} status={project.status} />
          </div>
          <Badge
            variant={
              project.status === "active" || project.status === "fundraising"
                ? "success"
                : project.status === "construction"
                ? "info"
                : "neutral"
            }
            className="shrink-0 capitalize text-[10px]"
          >
            {project.stage.replace(/_/g, " ")}
          </Badge>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">
              Target Raise
            </p>
            <p className="text-sm font-bold text-gray-900 mt-0.5">
              {formatCurrency(parseFloat(project.total_investment_required))}
            </p>
          </div>
          <div className="rounded-lg bg-indigo-50 p-3">
            <p className="text-[10px] text-indigo-400 uppercase tracking-wide">
              Interested Investors
            </p>
            <p className="text-sm font-bold text-indigo-700 mt-0.5">
              {isLoading ? "…" : interestedCount}
            </p>
          </div>
        </div>

        {/* Top investors */}
        {investors.length > 0 && (
          <div className="mt-3 space-y-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              Matched Investors
            </p>
            {investors.slice(0, 3).map((inv) => (
              <div
                key={inv.match_id ?? inv.investor_org_id}
                className="flex items-center justify-between gap-2"
              >
                <p className="text-xs text-gray-700 truncate">{inv.investor_name}</p>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={cn(
                      "text-xs font-semibold",
                      alignmentColor(inv.alignment.overall)
                    )}
                  >
                    {inv.alignment.overall}%
                  </span>
                  <Badge
                    variant={statusVariant(inv.status ?? "")}
                    className="text-[10px]"
                  >
                    {statusLabel(inv.status ?? "")}
                  </Badge>
                </div>
              </div>
            ))}
            {investors.length > 3 && (
              <p className="text-[10px] text-gray-400">
                +{investors.length - 3} more
              </p>
            )}
          </div>
        )}

        <div className="mt-4 flex gap-2">
          <Link
            href={`/projects/${project.id}/matching`}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
          >
            <Zap className="h-3 w-3" />
            View Matches
          </Link>
          <Link
            href={`/projects/${project.id}`}
            className="flex items-center justify-center rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
          >
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  accent?: boolean;
}) {
  return (
    <Card className={cn(accent && "border-indigo-200 bg-indigo-50/40")}>
      <CardContent className="p-4 flex items-start gap-3">
        <div
          className={cn(
            "p-2 rounded-lg",
            accent ? "bg-indigo-100" : "bg-gray-100"
          )}
        >
          <Icon
            className={cn("h-4 w-4", accent ? "text-indigo-600" : "text-gray-600")}
          />
        </div>
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p
            className={cn(
              "text-xl font-bold mt-0.5",
              accent ? "text-indigo-700" : "text-gray-900"
            )}
          >
            {value}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FundingPage() {
  const [filter, setFilter] = useState<"all" | "active" | "development">("all");
  const { data: stats, isLoading: loadingStats } = useProjectStats();
  const { data: projectList, isLoading: loadingProjects } = useProjects({
    page_size: 50,
  });

  const allProjects = projectList?.items ?? [];
  const projects = allProjects.filter((p) => {
    if (filter === "active") return p.status === "active";
    if (filter === "development") return p.stage === "development";
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <Wallet className="h-6 w-6 text-indigo-500" />
            Funding Overview
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Capital raise status across your project portfolio
          </p>
        </div>
        <Link href="/matching">
          <Button size="sm">
            <Users className="h-4 w-4 mr-2" />
            Find Investors
          </Button>
        </Link>
      </div>

      {/* KPIs */}
      {loadingStats ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard
            label="Total Projects"
            value={String(stats.total_projects)}
            icon={Target}
          />
          <KpiCard
            label="Active Fundraising"
            value={String(stats.active_fundraising)}
            icon={TrendingUp}
            accent
          />
          <KpiCard
            label="Total Capital Needed"
            value={formatCurrency(parseFloat(stats.total_funding_needed))}
            icon={DollarSign}
          />
          <KpiCard
            label="Avg Signal Score"
            value={
              stats.avg_signal_score != null
                ? `${stats.avg_signal_score.toFixed(0)}/100`
                : "—"
            }
            icon={Zap}
          />
        </div>
      ) : null}

      {/* Filter */}
      <div className="flex items-center gap-2">
        {(
          [
            { value: "all", label: "All Projects" },
            { value: "active", label: "Active" },
            { value: "development", label: "Development" },
          ] as const
        ).map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
              filter === f.value
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Project grid */}
      {loadingProjects ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title="No projects"
          description="Create a project to start tracking fundraising progress."
          action={
            <Link href="/projects/new">
              <Button size="sm">Create Project</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <ProjectFundingCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}
