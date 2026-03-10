"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  FolderKanban,
  Plus,
  ArrowRight,
  Briefcase,
  Leaf,
  AlertCircle,
  Clock,
  CheckCircle2,
  ChevronRight,
  Building,
  Layers,
  Zap,
  Sparkles,
  Users,
  Target,
  TrendingUp,
  Database,
  FileText,
} from "lucide-react";
import {
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  Tooltip as RadarTooltip,
} from "recharts";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  MetricCard,
  Badge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  EmptyState,
  DonutChart,
  BarChart,
  Button,
  cn,
} from "@scr/ui";
import { useSCRUser } from "@/lib/auth";
import { useRalphStore, usePlatformModeStore } from "@/lib/store";
import {
  useProjects,
  useProjectStats,
  projectTypeLabel,
  projectStatusColor,
} from "@/lib/projects";
import {
  usePortfolios,
  usePortfolioMetrics,
  useAllocation,
  useHoldings,
  formatCurrency,
  formatMultiple,
  assetTypeLabel,
  sfdrLabel,
  type AssetType,
} from "@/lib/portfolio";
import { useDomainScores } from "@/lib/risk";

// ── Ally Dashboard ───────────────────────────────────────────────────────────

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

const SNAP_INVESTORS = [
  { id: 1, name: "GreenTech Ventures", match: 96, mandate: "Clean Energy Fund III" },
  { id: 2, name: "Impact Capital Partners", match: 88, mandate: "Sustainable Infrastructure" },
  { id: 3, name: "Nordic Green Fund", match: 82, mandate: "Renewable Energy III" },
];

const PIPELINE_COLS = [
  { key: "draft", label: "Draft", bg: "bg-neutral-50", border: "border-neutral-200", text: "text-neutral-700", dot: "bg-neutral-400" },
  { key: "active", label: "Active", bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-800", dot: "bg-blue-500" },
  { key: "fundraising", label: "Fundraising", bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-800", dot: "bg-amber-500" },
  { key: "funded", label: "Funded", bg: "bg-indigo-50", border: "border-indigo-200", text: "text-indigo-800", dot: "bg-indigo-500" },
  { key: "operational", label: "Operational", bg: "bg-green-50", border: "border-green-200", text: "text-green-800", dot: "bg-green-500" },
] as const;

function relativeDate(dateStr: string) {
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

function matchDot(score: number) {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-amber-400";
  return "bg-red-400";
}

function matchText(score: number) {
  if (score >= 80) return "text-green-700";
  if (score >= 60) return "text-amber-700";
  return "text-red-600";
}

function AllyDashboard() {
  const router = useRouter();
  const { user } = useSCRUser();
  const { toggle: toggleRalph } = useRalphStore();
  const { data: stats } = useProjectStats();
  const { data: recent } = useProjects({
    page: 1,
    page_size: 10,
    sort_by: "updated_at",
    sort_order: "desc",
  });
  const { data: all } = useProjects({ page: 1, page_size: 100 });

  const allProjects = all?.items ?? [];

  // Readiness list — scored projects sorted by score desc
  const readinessSorted = [...allProjects]
    .filter((p) => p.latest_signal_score !== null)
    .sort((a, b) => (b.latest_signal_score ?? 0) - (a.latest_signal_score ?? 0))
    .slice(0, 8);

  // Action items
  const noScore = allProjects.filter((p) => p.latest_signal_score === null);
  const onHold = allProjects.filter((p) => p.status === "on_hold");
  const drafts = allProjects.filter((p) => p.status === "draft");

  const actionItems: Array<{
    icon: React.ElementType;
    color: string;
    bg: string;
    text: string;
    action: string | null;
    href: string | null;
  }> = [];
  if (noScore.length > 0)
    actionItems.push({
      icon: AlertCircle,
      color: "text-amber-600",
      bg: "bg-amber-50",
      text: `${noScore.length} project${noScore.length > 1 ? "s" : ""} missing a signal score`,
      action: "Go to Projects",
      href: "/projects",
    });
  if (drafts.length > 0)
    actionItems.push({
      icon: Layers,
      color: "text-blue-600",
      bg: "bg-blue-50",
      text: `${drafts.length} draft project${drafts.length > 1 ? "s" : ""} not yet published`,
      action: "Publish",
      href: "/projects",
    });
  if (onHold.length > 0)
    actionItems.push({
      icon: Clock,
      color: "text-orange-600",
      bg: "bg-orange-50",
      text: `${onHold.length} project${onHold.length > 1 ? "s" : ""} currently on hold`,
      action: "Review",
      href: "/projects",
    });
  if (actionItems.length === 0)
    actionItems.push({
      icon: CheckCircle2,
      color: "text-green-600",
      bg: "bg-green-50",
      text: "All projects are in great shape — keep up the momentum!",
      action: null,
      href: null,
    });

  // Project type distribution for DonutChart
  const typeCounts: Record<string, number> = {};
  allProjects.forEach((p) => {
    const label = projectTypeLabel(p.project_type);
    typeCounts[label] = (typeCounts[label] ?? 0) + 1;
  });
  const typeData = Object.entries(typeCounts).map(([name, count]) => ({ name, count }));

  // Pipeline by status
  const pipelineCols = PIPELINE_COLS.map((col) => {
    const projects = allProjects.filter((p) => p.status === col.key);
    const capital = projects.reduce(
      (sum, p) => sum + (parseFloat(p.total_investment_required) || 0),
      0
    );
    return { ...col, projects, capital };
  });

  // AI highlights
  const scored = allProjects.filter((p) => p.latest_signal_score !== null);
  const topProject = [...scored].sort(
    (a, b) => (b.latest_signal_score ?? 0) - (a.latest_signal_score ?? 0)
  )[0];
  const lowProject = [...scored].sort(
    (a, b) => (a.latest_signal_score ?? 0) - (b.latest_signal_score ?? 0)
  )[0];

  const firstName = user?.full_name?.split(" ")[0] ?? "there";
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="space-y-6">
      {/* ── 1. Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            {greeting()}, {firstName}
          </h1>
          <p className="mt-1 text-sm text-neutral-500">{today} · Your fundraising overview</p>
        </div>
        <Button onClick={() => router.push("/projects/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </Button>
      </div>

      {/* ── 2. Stats Strip ── */}
      <div className="grid grid-cols-2 divide-x divide-neutral-200 overflow-hidden rounded-xl border border-neutral-200 bg-white sm:grid-cols-3 lg:grid-cols-5">
        {[
          {
            icon: FolderKanban,
            label: "Total Projects",
            value: stats?.total_projects?.toString() ?? "—",
            color: "text-neutral-700",
          },
          {
            icon: TrendingUp,
            label: "Active Fundraising",
            value: stats?.active_fundraising?.toString() ?? "—",
            color: "text-blue-600",
          },
          {
            icon: Target,
            label: "Total Funding Target",
            value: stats ? formatCurrency(stats.total_funding_needed) : "—",
            color: "text-indigo-600",
          },
          {
            icon: Users,
            label: "Investor Matches",
            value: "10",
            color: "text-purple-600",
          },
          {
            icon: Zap,
            label: "Avg Signal Score",
            value: stats?.avg_signal_score != null
              ? `${stats.avg_signal_score.toFixed(0)}/100`
              : "—",
            color: "text-amber-600",
          },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="flex flex-col items-center py-4 text-center">
            <Icon className={cn("mb-1.5 h-5 w-5", color)} />
            <p className="text-xl font-bold text-neutral-900">{value}</p>
            <p className="mt-0.5 text-xs text-neutral-500">{label}</p>
          </div>
        ))}
      </div>

      {/* ── 3. Project Readiness + Action Items ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Project Readiness — 2/3 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Project Readiness</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => router.push("/projects")}>
                  View all <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="divide-y divide-neutral-100 p-0">
              {readinessSorted.length === 0 && (
                <EmptyState
                  icon={<FolderKanban className="h-8 w-8 text-neutral-300" />}
                  title="No scored projects yet"
                  description="Run a signal score to see your readiness ranking."
                />
              )}
              {readinessSorted.map((project) => {
                const score = project.latest_signal_score ?? 0;
                const barColor =
                  score >= 80 ? "bg-green-500" :
                  score >= 70 ? "bg-blue-500" :
                  score >= 60 ? "bg-amber-500" :
                  score >= 50 ? "bg-yellow-400" : "bg-red-400";
                return (
                  <div
                    key={project.id}
                    className="flex cursor-pointer items-center gap-4 px-6 py-3 hover:bg-neutral-50"
                    onClick={() => router.push(`/projects/${project.id}/signal-score`)}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-neutral-900">
                        {project.name}
                      </p>
                      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                        <div
                          className={cn("h-full rounded-full transition-all", barColor)}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                    <span
                      className={cn(
                        "shrink-0 text-sm font-semibold tabular-nums",
                        score >= 80 ? "text-green-700" :
                        score >= 70 ? "text-blue-700" :
                        score >= 60 ? "text-amber-700" :
                        score >= 50 ? "text-yellow-700" :
                        "text-red-600"
                      )}
                    >
                      {score.toFixed(0)}
                    </span>
                    <Badge variant={projectStatusColor(project.status)} className="shrink-0">
                      {project.status.replace(/_/g, " ")}
                    </Badge>
                    <ArrowRight className="h-4 w-4 shrink-0 text-neutral-400" />
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        {/* Action Items — 1/3 */}
        <Card>
          <CardHeader>
            <CardTitle>Action Items</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-4">
            {actionItems.map((item, i) => {
              const Icon = item.icon;
              return (
                <div
                  key={i}
                  className={cn(
                    "flex items-start gap-3 rounded-lg p-3",
                    item.bg
                  )}
                >
                  <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", item.color)} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-neutral-700">{item.text}</p>
                    {item.href && item.action && (
                      <button
                        className={cn("mt-1 text-xs font-medium underline-offset-2 hover:underline", item.color)}
                        onClick={() => router.push(item.href!)}
                      >
                        {item.action} →
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* ── 4. Fundraising Pipeline ── */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-neutral-900">Fundraising Pipeline</h2>
          <span className="text-xs text-neutral-400">{allProjects.length} projects total</span>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {pipelineCols.map((col) => (
            <div
              key={col.key}
              className={cn(
                "rounded-xl border p-4",
                col.bg,
                col.border
              )}
            >
              <div className="flex items-center gap-1.5">
                <span className={cn("h-2 w-2 rounded-full", col.dot)} />
                <p className={cn("text-xs font-semibold uppercase tracking-wide", col.text)}>
                  {col.label}
                </p>
              </div>
              <p className="mt-3 text-2xl font-bold text-neutral-900">{col.projects.length}</p>
              <p className="mt-0.5 text-xs text-neutral-500">
                {col.capital > 0 ? formatCurrency(col.capital.toString()) : "No capital set"}
              </p>
              {col.projects.slice(0, 3).map((p) => (
                <div
                  key={p.id}
                  className="mt-2 cursor-pointer truncate rounded-md bg-white/70 px-2 py-1 text-xs text-neutral-700 hover:bg-white"
                  onClick={() => router.push(`/projects/${p.id}`)}
                >
                  {p.name}
                </div>
              ))}
              {col.projects.length > 3 && (
                <p className="mt-1 text-xs text-neutral-400">+{col.projects.length - 3} more</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── 5. Investor Matching Snapshot + Project Type Mix ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Investor Matching Snapshot */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                <span className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-indigo-500" />
                  Investor Matches
                </span>
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => router.push("/matching")}>
                View all <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="divide-y divide-neutral-100 p-0">
            {SNAP_INVESTORS.map((inv) => (
              <div
                key={inv.id}
                className="flex cursor-pointer items-center gap-3 px-6 py-3 hover:bg-neutral-50"
                onClick={() => router.push("/matching")}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1B2A4A] text-xs font-bold text-white">
                  {inv.name
                    .split(" ")
                    .slice(0, 2)
                    .map((w) => w[0])
                    .join("")}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-neutral-900">{inv.name}</p>
                  <p className="truncate text-xs text-neutral-500">{inv.mandate}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className={cn("h-2 w-2 rounded-full", matchDot(inv.match))} />
                  <span className={cn("text-sm font-semibold tabular-nums", matchText(inv.match))}>
                    {inv.match}%
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Project Type Mix */}
        <Card>
          <CardHeader>
            <CardTitle>Project Type Mix</CardTitle>
          </CardHeader>
          <CardContent>
            {typeData.length > 0 ? (
              <DonutChart
                data={typeData}
                nameKey="name"
                valueKey="count"
                height={220}
                innerRadius={55}
                outerRadius={85}
              />
            ) : (
              <ChartPlaceholder />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── 6. Recent Activity + Quick Access ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-neutral-100 p-0">
            {recent?.items.slice(0, 5).map((project) => (
              <div
                key={project.id}
                className="flex cursor-pointer items-center gap-3 px-6 py-3 hover:bg-neutral-50"
                onClick={() => router.push(`/projects/${project.id}`)}
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-xs font-bold text-neutral-600">
                  {project.name
                    .split(" ")
                    .slice(0, 2)
                    .map((w) => w[0])
                    .join("")
                    .toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-neutral-900">{project.name}</p>
                  <p className="text-xs text-neutral-500">
                    {projectTypeLabel(project.project_type)} · Updated {relativeDate(project.updated_at)}
                  </p>
                </div>
                <Badge variant={projectStatusColor(project.status)} className="shrink-0">
                  {project.status.replace(/_/g, " ")}
                </Badge>
              </div>
            ))}
            {!recent?.items.length && (
              <p className="px-6 py-4 text-sm text-neutral-400">No recent activity</p>
            )}
          </CardContent>
        </Card>

        {/* Quick Access */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Access</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Signal Score", icon: Zap, color: "text-amber-500", bg: "bg-amber-50", onClick: () => router.push("/projects") },
                { label: "Data Room", icon: Database, color: "text-blue-500", bg: "bg-blue-50", onClick: () => router.push("/data-room") },
                { label: "Matching", icon: Users, color: "text-indigo-500", bg: "bg-indigo-50", onClick: () => router.push("/matching") },
                { label: "Ralph AI", icon: Sparkles, color: "text-purple-500", bg: "bg-purple-50", onClick: toggleRalph },
                { label: "Business Plan", icon: FileText, color: "text-green-600", bg: "bg-green-50", onClick: () => router.push("/business-plan") },
                { label: "ESG", icon: Leaf, color: "text-emerald-600", bg: "bg-emerald-50", onClick: () => router.push("/esg") },
              ].map(({ label, icon: Icon, color, bg, onClick }) => (
                <button
                  key={label}
                  onClick={onClick}
                  className="flex flex-col items-center gap-2 rounded-xl border border-neutral-100 p-4 text-center transition-colors hover:border-neutral-200 hover:bg-neutral-50"
                >
                  <div className={cn("flex h-10 w-10 items-center justify-center rounded-full", bg)}>
                    <Icon className={cn("h-5 w-5", color)} />
                  </div>
                  <span className="text-xs font-medium text-neutral-700">{label}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── 7. AI Signal Highlights ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Top Performer */}
        {topProject && (
          <div
            className="cursor-pointer rounded-xl border border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 p-5"
            onClick={() => router.push(`/projects/${topProject.id}/signal-score`)}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <p className="text-xs font-semibold uppercase tracking-wide text-green-700">
                Top Performer
              </p>
            </div>
            <p className="mt-3 truncate text-base font-bold text-neutral-900">{topProject.name}</p>
            <p className="mt-0.5 text-xs text-neutral-500">
              {projectTypeLabel(topProject.project_type)}
            </p>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-green-700">
                {topProject.latest_signal_score ?? 0}
              </span>
              <span className="text-sm text-green-600">/100</span>
            </div>
          </div>
        )}

        {/* Needs Attention */}
        {lowProject && lowProject.id !== topProject?.id && (
          <div
            className="cursor-pointer rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50 p-5"
            onClick={() => router.push(`/projects/${lowProject.id}/signal-score`)}
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                Needs Attention
              </p>
            </div>
            <p className="mt-3 truncate text-base font-bold text-neutral-900">{lowProject.name}</p>
            <p className="mt-0.5 text-xs text-neutral-500">
              {projectTypeLabel(lowProject.project_type)}
            </p>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-amber-700">
                {lowProject.latest_signal_score ?? 0}
              </span>
              <span className="text-sm text-amber-600">/100</span>
            </div>
          </div>
        )}

        {/* Ask Ralph CTA */}
        <div
          className="cursor-pointer rounded-xl border border-[#243660]/20 bg-gradient-to-br from-[#1B2A4A] to-[#243660] p-5"
          onClick={toggleRalph}
        >
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-300" />
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-300">
              AI Assistant
            </p>
          </div>
          <p className="mt-3 text-base font-bold text-white">Ask Ralph</p>
          <p className="mt-0.5 text-xs text-indigo-200">
            Get AI-powered insights on your projects, scores, and investor readiness
          </p>
          <div className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-white">
            Start a conversation <ArrowRight className="h-3 w-3" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Investor Dashboard ────────────────────────────────────────────────────────

function InvestorDashboard() {
  const router = useRouter();
  const { data: portfolios, isLoading } = usePortfolios();
  const firstPortfolio = portfolios?.items[0];
  const { data: metrics } = usePortfolioMetrics(firstPortfolio?.id);
  const { data: allocation } = useAllocation(firstPortfolio?.id);
  const { data: holdings } = useHoldings(firstPortfolio?.id);
  const { data: domainRisk } = useDomainScores(firstPortfolio?.id);

  // Chart data from allocation
  const assetTypeData = (allocation?.by_asset_type ?? []).map((a) => ({
    name: assetTypeLabel(a.name as AssetType) ?? a.name,
    value: parseFloat(a.percentage),
  }));
  const geographyData = (allocation?.by_geography ?? []).map((a) => ({
    geography: a.name,
    pct: parseFloat(a.percentage),
  }));
  const stageData = (allocation?.by_stage ?? []).map((a) => ({
    stage: a.name,
    pct: parseFloat(a.percentage),
  }));

  const riskDomains = (domainRisk?.domains ?? [])
    .filter((d) => d.score !== null)
    .map((d) => ({ dimension: d.domain, value: d.score as number }));

  // Recent holdings sorted by updated_at
  const recentHoldings = [...(holdings?.items ?? [])]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 5);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (!firstPortfolio) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
          <p className="mt-1 text-sm text-neutral-500">Your investment overview</p>
        </div>
        <EmptyState
          icon={<Briefcase className="h-12 w-12 text-neutral-400" />}
          title="No portfolio yet"
          description="Create a portfolio to start tracking your alternative investments."
          action={
            <Button onClick={() => router.push("/portfolio")}>
              <Plus className="mr-2 h-4 w-4" /> Create Portfolio
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {firstPortfolio.name} · {firstPortfolio.strategy.replace(/_/g, " ")}
          </p>
        </div>
        <Button variant="outline" onClick={() => router.push("/portfolio")}>
          View Portfolio <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>

      {/* Portfolio KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Value (NAV)"
          value={
            metrics
              ? formatCurrency(metrics.total_value, firstPortfolio.currency)
              : "—"
          }
        />
        <MetricCard
          label="Total Invested"
          value={
            metrics
              ? formatCurrency(metrics.total_invested, firstPortfolio.currency)
              : "—"
          }
        />
        <MetricCard
          label="Total Distributions"
          value={
            metrics
              ? formatCurrency(metrics.total_distributions, firstPortfolio.currency)
              : "—"
          }
        />
        <MetricCard
          label="Target AUM"
          value={formatCurrency(firstPortfolio.target_aum, firstPortfolio.currency)}
        />
      </div>

      {/* Private Market Metrics */}
      <div>
        <h2 className="mb-3 text-base font-semibold text-neutral-900">
          Performance Metrics
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <PerfMetric
            label="MOIC"
            value={metrics?.moic ? formatMultiple(metrics.moic) : "—"}
          />
          <PerfMetric
            label="DPI"
            value={metrics?.dpi ? formatMultiple(metrics.dpi) : "—"}
          />
          <PerfMetric
            label="RVPI"
            value={metrics?.rvpi ? formatMultiple(metrics.rvpi) : "—"}
          />
          <PerfMetric
            label="IRR (Net)"
            value={
              metrics?.irr_net
                ? `${parseFloat(metrics.irr_net).toFixed(1)}%`
                : "—"
            }
          />
        </div>
      </div>

      {/* Allocations + Risk */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Allocations — 2/3 width */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Allocations</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Tabs defaultValue="asset-class">
              <div className="border-b border-neutral-100 px-6 pt-2">
                <TabsList className="gap-4 bg-transparent p-0">
                  <TabsTrigger value="asset-class" className="pb-2 text-xs">
                    Asset Class
                  </TabsTrigger>
                  <TabsTrigger value="geography" className="pb-2 text-xs">
                    Geography
                  </TabsTrigger>
                  <TabsTrigger value="stage" className="pb-2 text-xs">
                    Stage
                  </TabsTrigger>
                </TabsList>
              </div>
              <TabsContent value="asset-class" className="px-6 py-4">
                {assetTypeData.length > 0 ? (
                  <DonutChart
                    data={assetTypeData}
                    nameKey="name"
                    valueKey="value"
                    height={220}
                    innerRadius={55}
                    outerRadius={85}
                  />
                ) : (
                  <ChartPlaceholder />
                )}
              </TabsContent>
              <TabsContent value="geography" className="px-6 py-4">
                {geographyData.length > 0 ? (
                  <BarChart
                    data={geographyData}
                    xKey="geography"
                    yKeys={["pct"]}
                    yLabels={{ pct: "% Allocation" }}
                    height={220}
                  />
                ) : (
                  <ChartPlaceholder />
                )}
              </TabsContent>
              <TabsContent value="stage" className="px-6 py-4">
                {stageData.length > 0 ? (
                  <BarChart
                    data={stageData}
                    xKey="stage"
                    yKeys={["pct"]}
                    yLabels={{ pct: "% Allocation" }}
                    height={220}
                  />
                ) : (
                  <ChartPlaceholder />
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Risk Overview — 1/3 width */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Overview</CardTitle>
          </CardHeader>
          <CardContent>
            {riskDomains.length === 0 ? (
              <p className="py-8 text-center text-xs text-neutral-400">
                No risk assessment data yet.{" "}
                <button onClick={() => router.push("/risk")} className="underline hover:text-neutral-600">
                  Run an assessment
                </button>
              </p>
            ) : (
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={riskDomains}>
                <PolarGrid stroke="#E0E0E0" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fontSize: 11, fill: "#9E9E9E" }}
                />
                <Radar
                  dataKey="value"
                  stroke="#1B3A5C"
                  fill="#1B3A5C"
                  fillOpacity={0.25}
                  strokeWidth={2}
                />
                <RadarTooltip />
              </RadarChart>
            </ResponsiveContainer>
            )}
            <div className="mt-3 space-y-1">
              {riskDomains.map((d) => (
                <div
                  key={d.dimension}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-neutral-500">{d.dimension}</span>
                  <span
                    className={cn(
                      "font-medium",
                      d.value >= 70
                        ? "text-green-600"
                        : d.value >= 50
                          ? "text-amber-600"
                          : "text-red-600"
                    )}
                  >
                    {d.value}/100
                  </span>
                </div>
              ))}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="mt-3 w-full"
              onClick={() => router.push("/risk")}
            >
              Full Risk Report <ArrowRight className="ml-1 h-3 w-3" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Investments + Impact */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Holdings */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Investments</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-neutral-100 p-0">
            {recentHoldings.length > 0 ? (
              <>
                {recentHoldings.map((holding) => (
                  <div
                    key={holding.id}
                    className="flex cursor-pointer items-center gap-3 px-6 py-3 hover:bg-neutral-50"
                    onClick={() => router.push(`/portfolio/${firstPortfolio.id}`)}
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100">
                      <Building className="h-4 w-4 text-primary-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-neutral-900">
                        {holding.asset_name}
                      </p>
                      <p className="text-xs text-neutral-500">
                        {assetTypeLabel(holding.asset_type)} ·{" "}
                        {formatCurrency(holding.investment_amount, holding.currency)}
                      </p>
                    </div>
                    {holding.moic && (
                      <span className="text-sm font-semibold text-neutral-700">
                        {formatMultiple(holding.moic)}
                      </span>
                    )}
                  </div>
                ))}
                {(holdings?.total ?? 0) > 5 && (
                  <div className="px-6 py-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => router.push(`/portfolio/${firstPortfolio.id}`)}
                    >
                      View all {holdings!.total} holdings{" "}
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                )}
              </>
            ) : (
              <p className="px-6 py-4 text-sm text-neutral-400">
                No holdings yet
              </p>
            )}
          </CardContent>
        </Card>

        {/* Impact & Efficiency */}
        <Card>
          <CardHeader>
            <CardTitle>Impact & Efficiency</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {metrics?.carbon_reduction_tons && (
              <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                <div className="flex items-center gap-3">
                  <Leaf className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="text-xs font-medium text-green-600">
                      Carbon Reduction
                    </p>
                    <p className="text-lg font-bold text-green-800">
                      {parseFloat(metrics.carbon_reduction_tons).toLocaleString()} tCO₂e
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Portfolio Details
              </p>
              <div className="mt-2 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-600">Holdings</span>
                  <span className="font-medium">{holdings?.total ?? "—"}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-600">SFDR</span>
                  <Badge variant="neutral">
                    {sfdrLabel(firstPortfolio.sfdr_classification)}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-600">Fund Type</span>
                  <span className="font-medium capitalize">
                    {firstPortfolio.fund_type.replace(/_/g, " ")}
                  </span>
                </div>
                {firstPortfolio.vintage_year && (
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">Vintage</span>
                    <span className="font-medium">{firstPortfolio.vintage_year}</span>
                  </div>
                )}
              </div>
            </div>

            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => router.push("/deals")}
            >
              Browse New Opportunities <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────

function PerfMetric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="py-4 text-center">
        <p className="text-xs font-medium uppercase tracking-wider text-neutral-500">
          {label}
        </p>
        <p className="mt-1 text-2xl font-bold tabular-nums text-neutral-900">
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

function ChartPlaceholder() {
  return (
    <div className="flex h-[220px] items-center justify-center text-sm text-neutral-400">
      No data yet
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user, isLoaded, isLoading } = useSCRUser();
  const { mode: storedMode } = usePlatformModeStore();

  if (!isLoaded || isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  const effectiveMode = storedMode ?? (user?.org_type === "investor" ? "investor" : "ally");

  if (effectiveMode === "investor") return <InvestorDashboard />;
  return <AllyDashboard />;
}
