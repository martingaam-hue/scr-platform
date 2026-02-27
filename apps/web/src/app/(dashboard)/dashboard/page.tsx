"use client";

import { useRouter } from "next/navigation";
import {
  FolderKanban,
  TrendingUp,
  DollarSign,
  Target,
  Plus,
  ArrowRight,
  Briefcase,
  Activity,
  Leaf,
  AlertCircle,
  Clock,
  CheckCircle2,
  ChevronRight,
  Building,
  Layers,
  Zap,
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
  ScoreGauge,
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
import {
  useProjects,
  useProjectStats,
  projectTypeLabel,
  projectStatusColor,
  stageLabel,
  type ProjectResponse,
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

// ── Ally Dashboard ───────────────────────────────────────────────────────────

function AllyDashboard() {
  const router = useRouter();
  const { data: stats } = useProjectStats();
  const { data: recent, isLoading: loadingRecent } = useProjects({
    page: 1,
    page_size: 6,
    sort_by: "updated_at",
    sort_order: "desc",
  });
  const { data: all } = useProjects({ page: 1, page_size: 50 });

  // Status distribution for BarChart
  const statusCounts: Record<string, number> = {};
  all?.items.forEach((p) => {
    const key = p.status.replace(/_/g, " ");
    statusCounts[key] = (statusCounts[key] ?? 0) + 1;
  });
  const statusData = Object.entries(statusCounts).map(([status, count]) => ({
    status,
    count,
  }));

  // Asset type distribution for DonutChart
  const typeCounts: Record<string, number> = {};
  all?.items.forEach((p) => {
    const label = projectTypeLabel(p.project_type);
    typeCounts[label] = (typeCounts[label] ?? 0) + 1;
  });
  const typeData = Object.entries(typeCounts).map(([name, count]) => ({
    name,
    count,
  }));

  // Action items derived from project state
  const actionItems: Array<{
    icon: React.ElementType;
    color: string;
    text: string;
    action: string | null;
    href: string | null;
  }> = [];
  const noScore = all?.items.filter((p) => p.latest_signal_score === null) ?? [];
  const onHold = all?.items.filter((p) => p.status === "on_hold") ?? [];
  const drafts = all?.items.filter((p) => p.status === "draft") ?? [];

  if (noScore.length > 0) {
    actionItems.push({
      icon: AlertCircle,
      color: "text-amber-500",
      text: `${noScore.length} project${noScore.length > 1 ? "s" : ""} missing a signal score`,
      action: "Go to Projects",
      href: "/projects",
    });
  }
  if (onHold.length > 0) {
    actionItems.push({
      icon: Clock,
      color: "text-orange-500",
      text: `${onHold.length} project${onHold.length > 1 ? "s" : ""} currently on hold`,
      action: "Review",
      href: "/projects",
    });
  }
  if (drafts.length > 0) {
    actionItems.push({
      icon: Layers,
      color: "text-blue-500",
      text: `${drafts.length} draft project${drafts.length > 1 ? "s" : ""} not yet published`,
      action: "Publish",
      href: "/projects",
    });
  }
  if (actionItems.length === 0) {
    actionItems.push({
      icon: CheckCircle2,
      color: "text-green-500",
      text: "All projects are in good shape",
      action: null,
      href: null,
    });
  }

  // AI highlights — top and low scorers
  const scored = (all?.items ?? []).filter((p) => p.latest_signal_score !== null);
  const topScorers = [...scored]
    .sort((a, b) => (b.latest_signal_score ?? 0) - (a.latest_signal_score ?? 0))
    .slice(0, 2);
  const lowScorers = [...scored]
    .sort((a, b) => (a.latest_signal_score ?? 0) - (b.latest_signal_score ?? 0))
    .slice(0, 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Your alternative investment project portfolio at a glance
          </p>
        </div>
        <Button onClick={() => router.push("/projects/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Projects"
          value={stats?.total_projects?.toString() ?? "—"}
        />
        <MetricCard
          label="Active Fundraising"
          value={stats?.active_fundraising?.toString() ?? "—"}
        />
        <MetricCard
          label="Total Funding Needed"
          value={stats ? formatCurrency(stats.total_funding_needed) : "—"}
        />
        <MetricCard
          label="Avg Signal Score"
          value={stats?.avg_signal_score?.toFixed(0) ?? "—"}
        />
      </div>

      {/* Recent Projects Grid */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-neutral-900">Recent Projects</h2>
          <Button variant="ghost" size="sm" onClick={() => router.push("/projects")}>
            View all <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
        {loadingRecent ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="h-28 animate-pulse rounded-lg bg-neutral-100" />
              </Card>
            ))}
          </div>
        ) : !recent?.items.length ? (
          <EmptyState
            icon={<FolderKanban className="h-10 w-10 text-neutral-400" />}
            title="No projects yet"
            description="Create your first project to start tracking your pipeline."
            action={
              <Button onClick={() => router.push("/projects/new")}>
                <Plus className="mr-2 h-4 w-4" /> New Project
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {recent.items.map((project) => (
              <AllyProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </div>

      {/* Portfolio Summary */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Asset Type Distribution</CardTitle>
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

        <Card>
          <CardHeader>
            <CardTitle>Projects by Status</CardTitle>
          </CardHeader>
          <CardContent>
            {statusData.length > 0 ? (
              <BarChart
                data={statusData}
                xKey="status"
                yKeys={["count"]}
                yLabels={{ count: "Projects" }}
                height={220}
              />
            ) : (
              <ChartPlaceholder />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Activity + Action Items */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100">
                  <Activity className="h-4 w-4 text-primary-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-neutral-900">
                    {project.name}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {projectTypeLabel(project.project_type)} · {stageLabel(project.stage)}
                  </p>
                </div>
                <Badge variant={projectStatusColor(project.status)}>
                  {project.status.replace(/_/g, " ")}
                </Badge>
              </div>
            ))}
            {!recent?.items.length && (
              <p className="px-6 py-4 text-sm text-neutral-400">No recent activity</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Action Items</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-neutral-100 p-0">
            {actionItems.map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={i} className="flex items-center gap-3 px-6 py-3">
                  <Icon className={cn("h-5 w-5 shrink-0", item.color)} />
                  <p className="flex-1 text-sm text-neutral-700">{item.text}</p>
                  {item.href && item.action && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => router.push(item.href!)}
                    >
                      {item.action}
                    </Button>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* AI Signal Highlights */}
      {scored.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                AI Signal Highlights
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {topScorers.map((project) => (
                <div
                  key={project.id}
                  className="cursor-pointer rounded-lg border border-green-100 bg-green-50 p-4"
                  onClick={() => router.push(`/projects/${project.id}`)}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium uppercase tracking-wide text-green-600">
                      Top Performer
                    </p>
                    <span className="text-sm font-bold text-green-700">
                      {project.latest_signal_score}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm font-semibold text-neutral-900">
                    {project.name}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {projectTypeLabel(project.project_type)}
                  </p>
                </div>
              ))}
              {lowScorers.map((project) => (
                <div
                  key={project.id}
                  className="cursor-pointer rounded-lg border border-amber-100 bg-amber-50 p-4"
                  onClick={() => router.push(`/projects/${project.id}`)}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium uppercase tracking-wide text-amber-600">
                      Needs Attention
                    </p>
                    <span className="text-sm font-bold text-amber-700">
                      {project.latest_signal_score}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm font-semibold text-neutral-900">
                    {project.name}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {projectTypeLabel(project.project_type)}
                  </p>
                </div>
              ))}
              <div
                className="cursor-pointer rounded-lg border border-neutral-100 bg-neutral-50 p-4"
                onClick={() => router.push("/ralph")}
              >
                <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                  AI Analysis
                </p>
                <p className="mt-1 text-sm font-semibold text-neutral-900">Ask Ralph AI</p>
                <p className="mt-0.5 text-xs text-neutral-500">
                  Get deeper insights on your portfolio performance
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Ally Project Card ────────────────────────────────────────────────────────

function AllyProjectCard({ project }: { project: ProjectResponse }) {
  const router = useRouter();
  const score = project.latest_signal_score;
  return (
    <Card
      hover
      className="cursor-pointer"
      onClick={() => router.push(`/projects/${project.id}`)}
    >
      <CardContent className="pb-5 pt-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-neutral-900">{project.name}</p>
            <p className="mt-0.5 text-xs text-neutral-500">
              {projectTypeLabel(project.project_type)} · {project.geography_country}
            </p>
          </div>
          {score !== null ? (
            <ScoreGauge score={score} size={48} strokeWidth={5} label="" />
          ) : (
            <span className="shrink-0 text-xs text-neutral-400">No score</span>
          )}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Badge variant={projectStatusColor(project.status)}>
            {project.status.replace(/_/g, " ")}
          </Badge>
          <span className="text-xs text-neutral-500">{stageLabel(project.stage)}</span>
        </div>
      </CardContent>
    </Card>
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

  // Risk radar — placeholder data (linked to /risk for full detail)
  const riskDomains = [
    { dimension: "Market", value: 65 },
    { dimension: "Climate", value: 45 },
    { dimension: "Regulatory", value: 72 },
    { dimension: "Technology", value: 58 },
    { dimension: "Liquidity", value: 80 },
  ];

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
  const { user, isLoading } = useSCRUser();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (user?.org_type === "investor") return <InvestorDashboard />;
  return <AllyDashboard />;
}
