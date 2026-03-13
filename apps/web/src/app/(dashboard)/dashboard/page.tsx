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
  AlertTriangle,
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
  Shield,
  Calendar,
  Download,
  Globe,
  BarChart3,
  Activity,
  Landmark,
} from "lucide-react";
import {
  ResponsiveContainer,
  Bar,
  BarChart as RBarChart,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
} from "recharts";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  EmptyState,
  DonutChart,
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
import { formatCurrency } from "@/lib/portfolio";

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

  type ActionItem = {
    icon: React.ElementType;
    color: string;
    bg: string;
    text: string;
    action: string | null;
    href: string | null;
  };

  // Static platform-surfaced actions always shown alongside dynamic project items
  const staticActionItems: ActionItem[] = [
    {
      icon: Zap,
      color: "text-indigo-600",
      bg: "bg-indigo-50",
      text: "2 new investor matches above 85% compatibility — respond to unlock warm introductions",
      action: "View Matches",
      href: "/matching",
    },
    {
      icon: FileText,
      color: "text-purple-600",
      bg: "bg-purple-50",
      text: "ITC §48 tax credit certification available for Solvatten Solar — est. $4.2M, +4.2 Signal Score pts",
      action: "Start Application",
      href: "/tax-credits",
    },
    {
      icon: Database,
      color: "text-blue-600",
      bg: "bg-blue-50",
      text: "Väst Wind 120MW Data Room is missing 3 investor documents ahead of the EIB site visit (Apr 28)",
      action: "Open Data Room",
      href: "/data-room",
    },
  ];

  const actionItems: ActionItem[] = [...staticActionItems];
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
              <div className="flex h-[220px] items-center justify-center text-sm text-neutral-400">No data yet</div>
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

// ── Investor Dashboard — Mock Data ────────────────────────────────────────────

const FUND = {
  name: "SCR Sustainable Infrastructure Fund I",
  strategy: "Sustainable Infrastructure · EU Focus",
  vintage: 2024,
  net_irr: 14.2,
  tvpi: 1.34,
  dpi: 0.18,
  rvpi: 1.16,
  committed: 500_000_000,
  deployed: 238_000_000,
  remaining: 262_000_000,
  next_call_amount: 35_000_000,
  next_call_date: "Apr 15, 2026",
  distributions_ytd: 12_500_000,
  cash_reserves: 8_200_000,
  avg_signal_score: 78,
  active_investments: 7,
  lp_count: 23,
};

const INV_HOLDINGS = [
  { id: "h1", name: "Helios Solar Portfolio Iberia", sector: "Solar", geo: "Spain", amount: 45_000_000, valuation: 54_200_000, signal_score: 87, risk_score: 82, irr: 16.1, multiple: 1.38, status: "performing" },
  { id: "h2", name: "Nordvik Wind Farm II", sector: "Wind", geo: "Norway", amount: 32_000_000, valuation: 35_600_000, signal_score: 74, risk_score: 71, irr: 11.8, multiple: 1.22, status: "performing" },
  { id: "h3", name: "Adriatic Infrastructure Holdings", sector: "Infrastructure", geo: "Italy", amount: 38_000_000, valuation: 44_100_000, signal_score: 82, risk_score: 78, irr: 13.4, multiple: 1.29, status: "performing" },
  { id: "h4", name: "Baltic BESS Grid Storage", sector: "BESS", geo: "Lithuania", amount: 18_000_000, valuation: 17_200_000, signal_score: 65, risk_score: 55, irr: 9.2, multiple: 1.08, status: "watch_list" },
  { id: "h5", name: "Alpine Hydro Partners", sector: "Hydro", geo: "Switzerland", amount: 52_000_000, valuation: 65_400_000, signal_score: 91, risk_score: 88, irr: 17.6, multiple: 1.52, status: "performing" },
  { id: "h6", name: "Nordic Biomass Energy", sector: "Biomass", geo: "Sweden", amount: 12_000_000, valuation: 12_800_000, signal_score: 71, risk_score: 68, irr: 10.5, multiple: 1.14, status: "performing" },
  { id: "h7", name: "Thames Clean Energy Hub", sector: "Wind", geo: "UK", amount: 41_000_000, valuation: 46_700_000, signal_score: 78, risk_score: 74, irr: 12.9, multiple: 1.25, status: "performing" },
];

const INV_ACTIVITY = [
  { id: "a1", project: "Sahara CSP Development", action: "Passed — screening score below threshold", date: "today", type: "passed" },
  { id: "a2", project: "Baltic BESS Grid Storage", action: "Risk alert raised — regulatory permit delay", date: "1 day ago", type: "alert" },
  { id: "a3", project: "Nordvik Wind Farm II", action: "Term sheet sent — awaiting countersignature", date: "2 days ago", type: "term_sheet" },
  { id: "a4", project: "Alpine Hydro Partners", action: "Q1 LP report generated and distributed", date: "3 days ago", type: "report" },
  { id: "a5", project: "East Aegean Solar", action: "Due diligence started — IM received", date: "5 days ago", type: "due_diligence" },
  { id: "a6", project: "Alpine Hydro Partners", action: "Investment committee approved — $52M committed", date: "1 week ago", type: "approved" },
  { id: "a7", project: "Iberian Wind Cluster", action: "Initial screening — score 79, strong fit", date: "1 week ago", type: "screening" },
  { id: "a8", project: "Nordic Biomass Energy", action: "KPI covenant met — Q4 targets confirmed", date: "2 weeks ago", type: "monitoring" },
];

const TOP_RISK_ALERTS = [
  { project: "Baltic BESS Grid Storage", alert: "Regulatory permit delay — grid connection approval pending", severity: "high" },
  { project: "Nordvik Wind Farm II", alert: "Weather events may impact Q1 generation targets by 8-12%", severity: "high" },
  { project: "Thames Clean Energy Hub", alert: "FX exposure — GBP/USD rate variance +2.1% vs budget", severity: "medium" },
];

const SCORE_DIST = [
  { range: "90-100", count: 1, color: "#22c55e" },
  { range: "80-89", count: 2, color: "#3b82f6" },
  { range: "70-79", count: 3, color: "#f59e0b" },
  { range: "60-69", count: 1, color: "#eab308" },
  { range: "<60",   count: 0, color: "#ef4444" },
];

const RISK_DOMAINS = [
  { domain: "Technical",   score: 81 },
  { domain: "Financial",   score: 74 },
  { domain: "Regulatory",  score: 68 },
  { domain: "ESG",         score: 85 },
  { domain: "Market",      score: 72 },
];

// ── Investor helpers ──────────────────────────────────────────────────────────

function fmtM(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function scoreColor(s: number) {
  if (s >= 80) return "text-green-600";
  if (s >= 70) return "text-blue-600";
  if (s >= 60) return "text-amber-600";
  if (s >= 50) return "text-yellow-600";
  return "text-red-600";
}

function scoreBarColor(s: number) {
  if (s >= 80) return "bg-green-500";
  if (s >= 70) return "bg-blue-500";
  if (s >= 60) return "bg-amber-500";
  if (s >= 50) return "bg-yellow-400";
  return "bg-red-400";
}

function invActivityMeta(type: string): { Icon: React.ElementType; color: string; bg: string } {
  switch (type) {
    case "passed":       return { Icon: AlertCircle,  color: "text-neutral-400", bg: "bg-neutral-100" };
    case "alert":        return { Icon: AlertTriangle, color: "text-red-500",     bg: "bg-red-50" };
    case "term_sheet":   return { Icon: FileText,      color: "text-blue-600",    bg: "bg-blue-50" };
    case "report":       return { Icon: Download,      color: "text-purple-600",  bg: "bg-purple-50" };
    case "due_diligence":return { Icon: Database,      color: "text-amber-600",   bg: "bg-amber-50" };
    case "approved":     return { Icon: CheckCircle2,  color: "text-green-600",   bg: "bg-green-50" };
    case "screening":    return { Icon: Target,        color: "text-indigo-600",  bg: "bg-indigo-50" };
    case "monitoring":   return { Icon: Activity,      color: "text-teal-600",    bg: "bg-teal-50" };
    default:             return { Icon: Activity,      color: "text-neutral-500", bg: "bg-neutral-100" };
  }
}

// ── Investor Dashboard ────────────────────────────────────────────────────────

function InvestorDashboard() {
  const router = useRouter();
  const { user } = useSCRUser();
  const { toggle: toggleRalph } = useRalphStore();

  const deployedPct = Math.round((FUND.deployed / FUND.committed) * 100);
  const totalNAV = INV_HOLDINGS.reduce((s, h) => s + h.valuation, 0);
  const totalCost = INV_HOLDINGS.reduce((s, h) => s + h.amount, 0);
  const unrealizedGain = totalNAV - totalCost;

  const firstName = user?.full_name?.split(" ")[0] ?? "there";
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="space-y-6">

      {/* ── 1. Greeting header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            {greeting()}, {firstName}
          </h1>
          <p className="mt-1 text-sm text-neutral-500">{today} · Your portfolio overview</p>
        </div>
        <Button onClick={() => router.push("/portfolio")}>
          <Briefcase className="mr-2 h-4 w-4" /> View Fund
        </Button>
      </div>

      {/* ── 2. Fund overview card ──────────────────────────────────────────── */}
      <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-primary-600">
              {FUND.strategy}
            </p>
            <p className="mt-1 text-lg font-bold leading-tight text-neutral-900">
              {FUND.name}
            </p>
            <p className="mt-0.5 text-xs text-neutral-400">
              Vintage {FUND.vintage} · {FUND.lp_count} LPs
            </p>
          </div>
          <Badge variant="success">Deploying</Badge>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {[
            { label: "Fund Size",    value: fmtM(FUND.committed),         sub: "committed capital" },
            { label: "Deployed",     value: fmtM(FUND.deployed),          sub: `${deployedPct}% of fund` },
            { label: "Total NAV",    value: fmtM(totalNAV),               sub: "portfolio fair value" },
            { label: "Net IRR",      value: `${FUND.net_irr}%`,           sub: "since inception" },
            { label: "TVPI",         value: `${FUND.tvpi}×`,              sub: "total value / paid-in" },
            { label: "Active Deals", value: `${FUND.active_investments}`, sub: `avg score ${FUND.avg_signal_score}` },
          ].map(({ label, value, sub }) => (
            <div key={label} className="rounded-xl bg-neutral-50 px-4 py-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">{label}</p>
              <p className="mt-1 text-xl font-bold tabular-nums text-neutral-900">{value}</p>
              <p className="text-[10px] text-neutral-400">{sub}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── 3. Fund performance + capital deployment ───────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* Performance multiples */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              Performance Multiples
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "TVPI", value: `${FUND.tvpi}×`, note: "Total value" },
                { label: "DPI",  value: `${FUND.dpi}×`,  note: "Distributions" },
                { label: "RVPI", value: `${FUND.rvpi}×`, note: "Remaining" },
              ].map(({ label, value, note }) => (
                <div key={label} className="rounded-lg bg-neutral-50 p-3 text-center">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{label}</p>
                  <p className="mt-1 text-2xl font-bold text-neutral-900">{value}</p>
                  <p className="text-[10px] text-neutral-400">{note}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 space-y-2.5 border-t border-neutral-100 pt-4">
              {[
                { label: "Net IRR",            value: `${FUND.net_irr}%`,           color: "text-green-600" },
                { label: "Unrealised gain",    value: `+${fmtM(unrealizedGain)}`,   color: "text-blue-600" },
                { label: "Distributions YTD",  value: fmtM(FUND.distributions_ytd), color: "text-indigo-600" },
                { label: "Cash reserves",      value: fmtM(FUND.cash_reserves),     color: "text-neutral-700" },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex items-center justify-between text-sm">
                  <span className="text-neutral-500">{label}</span>
                  <span className={cn("font-semibold", color)}>{value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Capital deployment */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Landmark className="h-4 w-4 text-primary-600" />
              Capital Deployment
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Progress bar */}
            <div className="mb-2 flex items-end justify-between">
              <div>
                <p className="text-2xl font-bold text-neutral-900">{fmtM(FUND.deployed)}</p>
                <p className="text-xs text-neutral-400">deployed of {fmtM(FUND.committed)}</p>
              </div>
              <p className="text-sm font-semibold text-neutral-600">{deployedPct}%</p>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-neutral-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-400 to-indigo-500 transition-all"
                style={{ width: `${deployedPct}%` }}
              />
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-neutral-400">
              <span>Deployed</span>
              <span>{fmtM(FUND.remaining)} remaining</span>
            </div>

            {/* Deployment by sector bar chart */}
            <div className="mt-5">
              <p className="mb-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide">By Sector</p>
              <ResponsiveContainer width="100%" height={160}>
                <RBarChart
                  data={INV_HOLDINGS.map((h) => ({ name: h.sector, deployed: Math.round(h.amount / 1_000_000) }))}
                  margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit="M" />
                  <ChartTooltip
                    formatter={(v) => [`$${v as number}M`, "Deployed"]}
                    contentStyle={{ fontSize: 11 }}
                  />
                  <Bar dataKey="deployed" radius={[4, 4, 0, 0]}>
                    {INV_HOLDINGS.map((h) => (
                      <Cell key={h.id} fill={scoreBarColor(h.signal_score)} />
                    ))}
                  </Bar>
                </RBarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-3 flex items-center gap-3 rounded-lg border border-amber-100 bg-amber-50 p-3">
              <Calendar className="h-4 w-4 shrink-0 text-amber-600" />
              <div>
                <p className="text-xs font-semibold text-amber-800">Next Capital Call</p>
                <p className="text-xs text-amber-600">{fmtM(FUND.next_call_amount)} · {FUND.next_call_date}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── 3. Deal pipeline + activity feed ──────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Deal pipeline stages */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-4 w-4 text-primary-600" />
              Deal Pipeline
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { stage: "Sourcing",       count: 14, color: "bg-neutral-400" },
              { stage: "Screening",      count: 6,  color: "bg-blue-400" },
              { stage: "Due Diligence",  count: 3,  color: "bg-amber-400" },
              { stage: "IC Review",      count: 2,  color: "bg-indigo-500" },
              { stage: "Committed",      count: 7,  color: "bg-green-500" },
            ].map(({ stage, count, color }) => (
              <div key={stage} className="flex items-center gap-3">
                <div className={cn("h-2 w-2 rounded-full", color)} />
                <span className="w-28 text-sm text-neutral-600">{stage}</span>
                <div className="flex-1 rounded-full bg-neutral-100 h-2 overflow-hidden">
                  <div
                    className={cn("h-full rounded-full", color)}
                    style={{ width: `${Math.min((count / 14) * 100, 100)}%` }}
                  />
                </div>
                <span className="w-5 text-right text-sm font-semibold text-neutral-700">{count}</span>
              </div>
            ))}
            <div className="mt-2 pt-2 border-t border-neutral-100 flex justify-between text-xs text-neutral-400">
              <span>32 total active opportunities</span>
              <button onClick={() => router.push("/deals")} className="text-primary-600 hover:underline font-medium">
                View all <ArrowRight className="inline h-3 w-3" />
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Activity feed */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary-600" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-neutral-100 p-0">
            {INV_ACTIVITY.slice(0, 6).map((item) => {
              const { Icon, color, bg } = invActivityMeta(item.type);
              return (
                <div key={item.id} className="flex items-start gap-3 px-6 py-3 hover:bg-neutral-50">
                  <div className={cn("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full", bg)}>
                    <Icon className={cn("h-3.5 w-3.5", color)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-neutral-800">{item.project}</p>
                    <p className="text-xs text-neutral-500 leading-tight">{item.action}</p>
                  </div>
                  <span className="shrink-0 text-[10px] text-neutral-400 whitespace-nowrap">{item.date}</span>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* ── 4. Portfolio holdings table ───────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-6">
            <CardTitle className="flex items-center gap-2">
              <Building className="h-4 w-4 text-primary-600" />
              Portfolio Holdings
            </CardTitle>
            <Button variant="outline" size="sm" onClick={() => router.push("/portfolio")}>
              <Download className="mr-1.5 h-3.5 w-3.5" /> Export
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-100 bg-neutral-50">
                  <th className="px-6 py-2.5 text-left text-xs font-semibold text-neutral-500">Company</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500">Sector · Geo</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-neutral-500">Cost</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-neutral-500">NAV</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-neutral-500">IRR</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-neutral-500">Signal</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-neutral-500">Status</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-neutral-400">
                    <span className="flex items-center justify-center gap-1">
                      Details <ChevronRight className="h-3 w-3" />
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-50">
                {INV_HOLDINGS.map((h) => (
                  <tr
                    key={h.id}
                    className="cursor-pointer hover:bg-neutral-50 transition-colors"
                    onClick={() => router.push("/portfolio")}
                  >
                    <td className="px-6 py-3 font-medium text-neutral-900">{h.name}</td>
                    <td className="px-3 py-3 text-neutral-500">
                      <span>{h.sector}</span>
                      <span className="mx-1 text-neutral-300">·</span>
                      <span className="flex items-center gap-1 inline-flex">
                        <Globe className="h-3 w-3" />{h.geo}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums text-neutral-700">{fmtM(h.amount)}</td>
                    <td className="px-3 py-3 text-right tabular-nums font-semibold text-neutral-900">{fmtM(h.valuation)}</td>
                    <td className="px-3 py-3 text-right tabular-nums text-neutral-700">{h.irr.toFixed(1)}%</td>
                    <td className="px-3 py-3 text-center">
                      <span className={cn("font-bold text-sm", scoreColor(h.signal_score))}>
                        {h.signal_score}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <Badge variant={h.status === "performing" ? "success" : "warning"}>
                        {h.status === "performing" ? "Performing" : "Watch"}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <ChevronRight className="h-4 w-4 text-neutral-300 inline" />
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-neutral-200 bg-neutral-50">
                  <td colSpan={2} className="px-6 py-2.5 text-xs font-semibold text-neutral-600">Total ({INV_HOLDINGS.length} holdings)</td>
                  <td className="px-3 py-2.5 text-right text-xs font-semibold text-neutral-700">{fmtM(totalCost)}</td>
                  <td className="px-3 py-2.5 text-right text-xs font-semibold text-neutral-900">{fmtM(totalNAV)}</td>
                  <td colSpan={4} className="px-3 py-2.5 text-right text-xs text-green-600 font-semibold">+{fmtM(unrealizedGain)} unrealised</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ── 5. Signal scores + risk exposure ──────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Score distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary-600" />
              Signal Score Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-3">
            <div className="mb-1 flex items-end justify-between">
              <p className="text-3xl font-bold text-neutral-900">{FUND.avg_signal_score}</p>
              <p className="text-xs text-neutral-400">portfolio avg</p>
            </div>
            <ResponsiveContainer width="100%" height={148}>
              <RBarChart data={SCORE_DIST} margin={{ top: 4, right: 0, left: -28, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f5f5f5" />
                <XAxis dataKey="range" tick={{ fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                <ChartTooltip contentStyle={{ fontSize: 11 }} formatter={(v) => [v as number, "Holdings"]} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {SCORE_DIST.map((d) => (
                    <Cell key={d.range} fill={d.color} />
                  ))}
                </Bar>
              </RBarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Risk exposure by domain */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary-600" />
                Risk Exposure
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => router.push("/risk")}>
                Full report <ChevronRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {RISK_DOMAINS.map((d) => (
              <div key={d.domain}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-neutral-600">{d.domain}</span>
                  <span className={cn("font-semibold", scoreColor(d.score))}>{d.score}/100</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
                  <div
                    className={cn("h-full rounded-full transition-all", scoreBarColor(d.score))}
                    style={{ width: `${d.score}%` }}
                  />
                </div>
              </div>
            ))}

            {/* Risk alerts */}
            <div className="mt-4 space-y-2 border-t border-neutral-100 pt-3">
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Active Alerts</p>
              {TOP_RISK_ALERTS.map((a, i) => (
                <div key={i} className={cn(
                  "flex items-start gap-2 rounded-lg p-2 text-xs",
                  a.severity === "high" ? "bg-red-50" : "bg-amber-50"
                )}>
                  <AlertTriangle className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", a.severity === "high" ? "text-red-500" : "text-amber-500")} />
                  <div>
                    <p className="font-medium text-neutral-800">{a.project}</p>
                    <p className="text-neutral-500 leading-tight">{a.alert}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── 6. ESG snapshot + LP reporting ────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* ESG snapshot */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Leaf className="h-4 w-4 text-green-600" />
              ESG Portfolio Snapshot
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                { label: "Avg ESG Score",       value: "81/100",     color: "text-green-600", bg: "bg-green-50"  },
                { label: "SFDR Art. 9",          value: "5 / 7",      color: "text-indigo-600", bg: "bg-indigo-50" },
                { label: "CO₂ Avoided (YTD)",    value: "142k tCO₂e", color: "text-teal-600",  bg: "bg-teal-50"  },
                { label: "Renewable Capacity",   value: "423 MW",     color: "text-blue-600",  bg: "bg-blue-50"  },
              ].map(({ label, value, color, bg }) => (
                <div key={label} className={cn("rounded-xl p-4", bg)}>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{label}</p>
                  <p className={cn("mt-1.5 text-xl font-bold", color)}>{value}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3">
              {INV_HOLDINGS.slice(0, 3).map((h) => (
                <div key={h.id} className="rounded-lg border border-neutral-100 p-3">
                  <p className="truncate text-xs font-semibold text-neutral-700">{h.name.split(" ").slice(0, 2).join(" ")}</p>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <div className="flex-1 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                      <div className="h-full rounded-full bg-green-400" style={{ width: `${h.signal_score}%` }} />
                    </div>
                    <span className={cn("text-xs font-bold", scoreColor(h.signal_score))}>{h.signal_score}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* LP reporting */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary-600" />
              LP Reporting
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Q4 2025 Report",   status: "Sent",     date: "Jan 15",   variant: "success"  as const },
              { label: "Q3 2025 Report",   status: "Sent",     date: "Oct 12",   variant: "success"  as const },
              { label: "Q1 2026 Report",   status: "Due",      date: "Apr 30",   variant: "warning"  as const },
              { label: "Annual Accounts",  status: "In prep",  date: "Mar 31",   variant: "info"     as const },
            ].map(({ label, status, date, variant }) => (
              <div key={label} className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-neutral-800">{label}</p>
                  <p className="text-[10px] text-neutral-400">{date}</p>
                </div>
                <Badge variant={variant}>{status}</Badge>
              </div>
            ))}
            <div className="mt-2 border-t border-neutral-100 pt-3">
              <div className="flex items-center justify-between text-xs text-neutral-500">
                <span>{FUND.lp_count} LPs registered</span>
                <button onClick={() => router.push("/data-room")} className="text-primary-600 hover:underline font-medium">
                  Data Room <ArrowRight className="inline h-3 w-3" />
                </button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── 7. Quick actions + Ask Ralph ──────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Quick action buttons */}
        <div className="grid grid-cols-3 gap-3 lg:col-span-2">
          {[
            { label: "Browse Deals",    icon: Target,  path: "/deals", color: "text-indigo-600", bg: "bg-indigo-50" },
            { label: "Run ESG Report",  icon: Leaf,    path: "/esg",   color: "text-green-600",  bg: "bg-green-50"  },
            { label: "Risk Assessment", icon: Shield,  path: "/risk",  color: "text-red-600",    bg: "bg-red-50"    },
          ].map(({ label, icon: Icon, path, color, bg }) => (
            <button
              key={label}
              onClick={() => router.push(path)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border border-neutral-100 p-4 transition-all hover:shadow-md hover:-translate-y-0.5",
                bg
              )}
            >
              <div className={cn("flex h-9 w-9 items-center justify-center rounded-full bg-white shadow-sm", color)}>
                <Icon className="h-4 w-4" />
              </div>
              <span className="text-xs font-semibold text-neutral-700">{label}</span>
            </button>
          ))}
        </div>

        {/* Ask Ralph — ally-style dark navy card */}
        <div
          className="cursor-pointer rounded-xl border border-[#243660]/20 bg-gradient-to-br from-[#1B2A4A] to-[#243660] p-5 transition-all hover:shadow-lg"
          onClick={toggleRalph}
        >
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-300" />
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-300">AI Assistant</p>
          </div>
          <p className="mt-3 text-base font-bold text-white">Ask Ralph</p>
          <p className="mt-0.5 text-xs text-indigo-200">
            Get AI-powered insights on your portfolio, risk exposure, and deal pipeline
          </p>
          <div className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-white">
            Start a conversation <ArrowRight className="h-3 w-3" />
          </div>
        </div>
      </div>

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
