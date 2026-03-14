"use client";

import { useState } from "react";
import {
  ArrowUpDown,
  BarChart3,
  DollarSign,
  PieChart,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  DataTable,
  EmptyState,
  InfoBanner,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
  cn,
} from "@scr/ui";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { useCashflowPacing } from "@/lib/metrics";
import { usePermission } from "@/lib/auth";
import {
  usePortfolios,
  usePortfolio,
  usePortfolioMetrics,
  useHoldings,
  useCashFlows,
  useAllocation,
  type HoldingResponse,
  type AllocationBreakdown,
  type PortfolioStrategy,
  type SFDRClassification,
  formatCurrency,
  formatPercent,
  formatMultiple,
  strategyLabel,
  sfdrLabel,
  assetTypeLabel,
  holdingStatusColor,
} from "@/lib/portfolio";

// ── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_PORTFOLIO = {
  id: "mock-portfolio-1",
  name: "SCR Sustainable Infrastructure Fund I",
  strategy: "sustainable_infrastructure" as PortfolioStrategy,
  sfdr_classification: "article_9" as SFDRClassification,
  current_aum: "275600000",
  currency: "EUR",
};

const MOCK_PORTFOLIO_LIST = {
  items: [MOCK_PORTFOLIO],
  total: 1,
};

const MOCK_HOLDINGS = [
  {
    id: "h1",
    asset_name: "Helios Solar Portfolio Iberia",
    asset_type: "solar",
    status: "active",
    investment_date: "2024-03-15",
    investment_amount: "45000000",
    current_value: "54200000",
    moic: "1.42",
    currency: "EUR",
    geography: "Spain",
  },
  {
    id: "h2",
    asset_name: "Nordvik Wind Farm II",
    asset_type: "wind",
    status: "active",
    investment_date: "2024-05-20",
    investment_amount: "32000000",
    current_value: "35600000",
    moic: "1.18",
    currency: "EUR",
    geography: "Norway",
  },
  {
    id: "h3",
    asset_name: "Adriatic Infrastructure Holdings",
    asset_type: "infrastructure",
    status: "active",
    investment_date: "2024-04-10",
    investment_amount: "38000000",
    current_value: "44100000",
    moic: "1.31",
    currency: "EUR",
    geography: "Italy",
  },
  {
    id: "h4",
    asset_name: "Baltic BESS Grid Storage",
    asset_type: "bess",
    status: "active",
    investment_date: "2024-07-01",
    investment_amount: "18000000",
    current_value: "17200000",
    moic: "1.08",
    currency: "EUR",
    geography: "Lithuania",
  },
  {
    id: "h5",
    asset_name: "Alpine Hydro Partners",
    asset_type: "hydro",
    status: "active",
    investment_date: "2024-02-28",
    investment_amount: "52000000",
    current_value: "65400000",
    moic: "1.56",
    currency: "EUR",
    geography: "Switzerland",
  },
  {
    id: "h6",
    asset_name: "Nordic Biomass Energy",
    asset_type: "biomass",
    status: "active",
    investment_date: "2024-08-15",
    investment_amount: "12000000",
    current_value: "12800000",
    moic: "1.14",
    currency: "EUR",
    geography: "Sweden",
  },
  {
    id: "h7",
    asset_name: "Thames Clean Energy Hub",
    asset_type: "wind",
    status: "active",
    investment_date: "2024-06-05",
    investment_amount: "41000000",
    current_value: "46700000",
    moic: "1.25",
    currency: "EUR",
    geography: "UK",
  },
] as unknown as HoldingResponse[];

const MOCK_HOLDINGS_DATA = {
  items: MOCK_HOLDINGS,
  total: 7,
  totals: {
    total_invested: "238000000",
    total_current_value: "276000000",
    weighted_moic: "1.31",
  },
};

const MOCK_METRICS = {
  irr_gross: "14.2",
  irr_net: "12.8",
  moic: "1.31",
  tvpi: "1.31",
  dpi: "0.18",
  rvpi: "1.13",
  total_distributions: "42840000",
};

const MOCK_ALLOCATION = {
  by_asset_type: [
    { name: "Solar", value: "78540000", percentage: "33.0" },
    { name: "Wind", value: "73000000", percentage: "30.7" },
    { name: "Hydro", value: "52000000", percentage: "21.8" },
    { name: "Infrastructure", value: "38000000", percentage: "16.0" },
    { name: "BESS", value: "18000000", percentage: "7.6" },
    { name: "Biomass", value: "12000000", percentage: "5.0" },
  ] as AllocationBreakdown[],
  by_sector: [
    { name: "Renewable Energy", value: "191000000", percentage: "80.3" },
    { name: "Infrastructure", value: "38000000", percentage: "16.0" },
    { name: "Energy Storage", value: "18000000", percentage: "7.6" },
  ] as AllocationBreakdown[],
  by_geography: [
    { name: "Switzerland", value: "52000000", percentage: "21.8" },
    { name: "Spain", value: "45000000", percentage: "18.9" },
    { name: "UK", value: "41000000", percentage: "17.2" },
    { name: "Italy", value: "38000000", percentage: "16.0" },
    { name: "Norway", value: "32000000", percentage: "13.4" },
    { name: "Lithuania", value: "18000000", percentage: "7.6" },
    { name: "Sweden", value: "12000000", percentage: "5.0" },
  ] as AllocationBreakdown[],
  by_stage: [
    { name: "Investment Period", value: "238000000", percentage: "100.0" },
  ] as AllocationBreakdown[],
};

const MOCK_CASHFLOWS = {
  items: [
    { date: "2024-03-15", type: "capital_call", holding_name: "Helios Solar Portfolio Iberia", amount: "-45000000" },
    { date: "2024-04-10", type: "capital_call", holding_name: "Adriatic Infrastructure Holdings", amount: "-38000000" },
    { date: "2024-05-20", type: "capital_call", holding_name: "Nordvik Wind Farm II", amount: "-32000000" },
    { date: "2024-06-05", type: "capital_call", holding_name: "Thames Clean Energy Hub", amount: "-41000000" },
    { date: "2024-07-01", type: "capital_call", holding_name: "Baltic BESS Grid Storage", amount: "-18000000" },
    { date: "2024-08-15", type: "capital_call", holding_name: "Nordic Biomass Energy", amount: "-12000000" },
    { date: "2024-09-30", type: "distribution", holding_name: "Alpine Hydro Partners", amount: "5200000" },
    { date: "2024-12-15", type: "distribution", holding_name: "Helios Solar Portfolio Iberia", amount: "8100000" },
    { date: "2025-03-28", type: "distribution", holding_name: "Alpine Hydro Partners", amount: "6500000" },
    { date: "2025-06-30", type: "distribution", holding_name: "Thames Clean Energy Hub", amount: "5400000" },
    { date: "2025-09-30", type: "distribution", holding_name: "Nordvik Wind Farm II", amount: "4200000" },
    { date: "2025-12-31", type: "distribution", holding_name: "Adriatic Infrastructure Holdings", amount: "7800000" },
    { date: "2026-01-15", type: "capital_call", holding_name: "SCR Fund I — Management Fee", amount: "-5250000" },
    { date: "2026-03-10", type: "distribution", holding_name: "Helios Solar Portfolio Iberia", amount: "9100000" },
  ],
  total: 14,
};

const MOCK_PACING_DATA = {
  months: [
    { month: "2024-Q1", cumulative_drawn: 83000000, cumulative_distributed: 0, nav: 80100000 },
    { month: "2024-Q2", cumulative_drawn: 124000000, cumulative_distributed: 0, nav: 120800000 },
    { month: "2024-Q3", cumulative_drawn: 154000000, cumulative_distributed: 5200000, nav: 151400000 },
    { month: "2024-Q4", cumulative_drawn: 238000000, cumulative_distributed: 13300000, nav: 232500000 },
    { month: "2025-Q1", cumulative_drawn: 243250000, cumulative_distributed: 19800000, nav: 248900000 },
    { month: "2025-Q2", cumulative_drawn: 243250000, cumulative_distributed: 25200000, nav: 258200000 },
    { month: "2025-Q3", cumulative_drawn: 243250000, cumulative_distributed: 29400000, nav: 265700000 },
    { month: "2025-Q4", cumulative_drawn: 243250000, cumulative_distributed: 37200000, nav: 271800000 },
    { month: "2026-Q1", cumulative_drawn: 248500000, cumulative_distributed: 46300000, nav: 276000000 },
  ],
};

// ── Pacing Tab ───────────────────────────────────────────────────────────────

type PacingScenario = "base" | "optimistic" | "pessimistic";

function PacingTab({ portfolioId }: { portfolioId: string }) {
  const [scenario, setScenario] = useState<PacingScenario>("base");
  const { data: apiData, isLoading } = useCashflowPacing(portfolioId, scenario);

  const data = apiData ?? MOCK_PACING_DATA;

  if (!portfolioId) {
    return (
      <EmptyState
        icon={<TrendingUp className="h-12 w-12 text-neutral-400" />}
        title="No portfolio selected"
        description="Select a portfolio to view pacing."
      />
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="h-64 animate-pulse rounded-lg bg-neutral-100" />
        </CardContent>
      </Card>
    );
  }

  const chartData = data.months.map((m) => ({
    month: m.month,
    "Drawn (cumulative)": m.cumulative_drawn,
    "Distributed (cumulative)": m.cumulative_distributed,
    NAV: m.nav,
  }));

  const fmtM = (v: number) => `€${(v / 1_000_000).toFixed(1)}M`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-900">
          Cashflow Pacing
        </h3>
        <select
          className="rounded-lg border border-neutral-300 px-3 py-1.5 text-sm"
          value={scenario}
          onChange={(e) => setScenario(e.target.value as PacingScenario)}
        >
          <option value="base">Base</option>
          <option value="optimistic">Optimistic</option>
          <option value="pessimistic">Pessimistic</option>
        </select>
      </div>
      <Card>
        <CardContent className="p-6">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart
              data={chartData}
              margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorDrawn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorDist" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorNAV" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis
                tickFormatter={fmtM}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={(v: number | undefined) =>
                  v != null ? fmtM(v) : "—"
                }
                contentStyle={{ fontSize: 12 }}
              />
              <Area
                type="monotone"
                dataKey="Drawn (cumulative)"
                stroke="#ef4444"
                strokeWidth={2}
                fill="url(#colorDrawn)"
              />
              <Area
                type="monotone"
                dataKey="Distributed (cumulative)"
                stroke="#22c55e"
                strokeWidth={2}
                fill="url(#colorDist)"
              />
              <Area
                type="monotone"
                dataKey="NAV"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#colorNAV)"
              />
            </AreaChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="mt-3 flex gap-5">
            {[
              { label: "Drawn (cumulative)", color: "#ef4444" },
              { label: "Distributed (cumulative)", color: "#22c55e" },
              { label: "NAV", color: "#3b82f6" },
            ].map(({ label, color }) => (
              <div key={label} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs text-neutral-500">{label}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Metric Card ─────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  subtitle,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary-100 text-primary-600">
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-neutral-500">{label}</p>
          <p className="text-2xl font-semibold text-neutral-900 truncate">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-neutral-400">{subtitle}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Allocation bar ──────────────────────────────────────────────────────────

function AllocationChart({
  title,
  data,
}: {
  title: string;
  data: AllocationBreakdown[];
}) {
  const COLORS = [
    "bg-primary-600",
    "bg-emerald-500",
    "bg-amber-500",
    "bg-rose-500",
    "bg-violet-500",
    "bg-sky-500",
    "bg-orange-500",
    "bg-teal-500",
  ];

  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-4 text-sm font-semibold text-neutral-900">{title}</h3>
        {!data.length ? (
          <p className="text-sm text-neutral-400">No data</p>
        ) : (
          <div className="space-y-3">
            {/* Stacked bar */}
            <div className="flex h-4 overflow-hidden rounded-full bg-neutral-100">
              {data.map((item, i) => (
                <div
                  key={item.name}
                  className={cn(COLORS[i % COLORS.length], "transition-all")}
                  style={{ width: `${parseFloat(item.percentage)}%` }}
                  title={`${item.name}: ${item.percentage}%`}
                />
              ))}
            </div>
            {/* Legend */}
            <div className="space-y-2">
              {data.map((item, i) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        "h-3 w-3 rounded-full",
                        COLORS[i % COLORS.length]
                      )}
                    />
                    <span className="text-neutral-600 capitalize">
                      {item.name.replace("_", " ")}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-neutral-900">
                      {formatCurrency(item.value)}
                    </span>
                    <span className="text-neutral-400 w-12 text-right">
                      {parseFloat(item.percentage).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Holdings columns ────────────────────────────────────────────────────────

const holdingColumns: ColumnDef<HoldingResponse>[] = [
  {
    accessorKey: "asset_name",
    header: "Asset",
    cell: ({ row }) => (
      <div className="min-w-0">
        <p className="font-medium text-neutral-900 truncate">
          {row.original.asset_name}
        </p>
        <p className="text-xs text-neutral-500">
          {assetTypeLabel(row.original.asset_type)}
        </p>
      </div>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={holdingStatusColor(row.original.status)}>
        {row.original.status.replace("_", " ")}
      </Badge>
    ),
  },
  {
    accessorKey: "investment_date",
    header: "Invested",
    cell: ({ row }) => (
      <span className="text-sm text-neutral-600">
        {new Date(row.original.investment_date).toLocaleDateString()}
      </span>
    ),
  },
  {
    accessorKey: "investment_amount",
    header: "Amount",
    cell: ({ row }) => (
      <span className="text-sm font-medium">
        {formatCurrency(row.original.investment_amount, row.original.currency)}
      </span>
    ),
  },
  {
    accessorKey: "current_value",
    header: "Current Value",
    cell: ({ row }) => (
      <span className="text-sm font-medium">
        {formatCurrency(row.original.current_value, row.original.currency)}
      </span>
    ),
  },
  {
    accessorKey: "moic",
    header: "MOIC",
    cell: ({ row }) => {
      const moic = row.original.moic;
      if (!moic) return <span className="text-neutral-400">—</span>;
      const val = parseFloat(moic);
      return (
        <span
          className={cn(
            "text-sm font-semibold",
            val >= 1.5
              ? "text-green-600"
              : val >= 1.0
                ? "text-amber-600"
                : "text-red-600"
          )}
        >
          {formatMultiple(moic)}
        </span>
      );
    },
  },
];

// ── Page ────────────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  usePermission("create", "portfolio");

  // Load list of portfolios and select first one
  const { data: apiPortfolioList } = usePortfolios();
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  const portfolioList = apiPortfolioList?.items?.length
    ? apiPortfolioList
    : MOCK_PORTFOLIO_LIST;

  const activeId = selectedId ?? portfolioList?.items[0]?.id;

  const { data: apiPortfolio } = usePortfolio(activeId);
  const { data: apiMetrics } = usePortfolioMetrics(activeId);
  const { data: apiHoldings } = useHoldings(activeId);
  const { data: apiCashFlows } = useCashFlows(activeId);
  const { data: apiAllocation } = useAllocation(activeId);

  const portfolio = apiPortfolio ?? (activeId === MOCK_PORTFOLIO.id ? MOCK_PORTFOLIO : null) ?? MOCK_PORTFOLIO;
  const metrics = apiMetrics ?? MOCK_METRICS;
  const holdings = apiHoldings ?? MOCK_HOLDINGS_DATA;
  const cashFlows = apiCashFlows ?? MOCK_CASHFLOWS;
  const allocation = apiAllocation ?? MOCK_ALLOCATION;

  return (
    <div className="space-y-6">
      {/* Header + portfolio selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Wallet className="h-6 w-6 text-primary-600" />
          </div>
          <h1 className="text-2xl font-bold text-neutral-900">Portfolio</h1>
          {portfolioList && portfolioList.items.length > 1 && (
            <select
              className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
              value={activeId ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {portfolioList.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>
        {portfolio && (
          <div className="flex items-center gap-3">
            <Badge variant="info">{strategyLabel(portfolio.strategy)}</Badge>
            <Badge variant="neutral">{sfdrLabel(portfolio.sfdr_classification)}</Badge>
          </div>
        )}
      </div>

      <InfoBanner>
        <strong>Portfolio</strong> provides a consolidated view of all your fund holdings, performance metrics, allocation breakdown, and cash flow pacing. Use the tabs below to drill into specific dimensions.
      </InfoBanner>

      {/* Metrics cards */}
      {metrics && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <MetricCard
            label="Total AUM"
            value={portfolio ? formatCurrency(portfolio.current_aum, portfolio.currency) : "—"}
            icon={Wallet}
          />
          <MetricCard
            label="Holdings"
            value={holdings?.total ?? 0}
            icon={BarChart3}
          />
          <MetricCard
            label="MOIC"
            value={metrics.moic ? formatMultiple(metrics.moic) : "—"}
            subtitle={metrics.tvpi ? `TVPI: ${formatMultiple(metrics.tvpi)}` : undefined}
            icon={TrendingUp}
          />
          <MetricCard
            label="Distributions"
            value={formatCurrency(metrics.total_distributions)}
            subtitle={metrics.dpi ? `DPI: ${formatMultiple(metrics.dpi)}` : undefined}
            icon={DollarSign}
          />
          <MetricCard
            label="IRR (Gross)"
            value={metrics.irr_gross ? formatPercent(metrics.irr_gross) : "—"}
            subtitle={metrics.irr_net ? `Net: ${formatPercent(metrics.irr_net)}` : undefined}
            icon={TrendingUp}
          />
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="holdings">
        <TabsList>
          <TabsTrigger value="holdings">
            Holdings ({holdings?.total ?? 0})
          </TabsTrigger>
          <TabsTrigger value="allocation">Allocation</TabsTrigger>
          <TabsTrigger value="cash-flows">Cash Flows</TabsTrigger>
          <TabsTrigger value="pacing">Pacing</TabsTrigger>
        </TabsList>

        {/* Holdings Tab */}
        <TabsContent value="holdings" className="mt-6 space-y-4">
          {/* Holdings summary bar */}
          {holdings?.totals && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-neutral-500">Total Invested</p>
                  <p className="text-lg font-semibold">
                    {formatCurrency(holdings.totals.total_invested)}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-neutral-500">Current Value</p>
                  <p className="text-lg font-semibold">
                    {formatCurrency(holdings.totals.total_current_value)}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-neutral-500">Weighted MOIC</p>
                  <p className="text-lg font-semibold">
                    {holdings.totals.weighted_moic
                      ? formatMultiple(holdings.totals.weighted_moic)
                      : "—"}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {!holdings?.items.length ? (
            <EmptyState
              icon={<BarChart3 className="h-12 w-12 text-neutral-400" />}
              title="No holdings"
              description="Add holdings to track portfolio investments."
            />
          ) : (
            <Card>
              <DataTable
                columns={holdingColumns}
                data={holdings.items}
              />
            </Card>
          )}
        </TabsContent>

        {/* Allocation Tab */}
        <TabsContent value="allocation" className="mt-6">
          {allocation ? (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <AllocationChart
                title="By Asset Type"
                data={allocation.by_asset_type}
              />
              <AllocationChart
                title="By Sector"
                data={allocation.by_sector}
              />
              <AllocationChart
                title="By Geography"
                data={allocation.by_geography}
              />
              <AllocationChart
                title="By Stage"
                data={allocation.by_stage}
              />
            </div>
          ) : (
            <EmptyState
              icon={<PieChart className="h-12 w-12 text-neutral-400" />}
              title="No allocation data"
              description="Add holdings to see allocation breakdowns."
            />
          )}
        </TabsContent>

        {/* Cash Flows Tab */}
        <TabsContent value="cash-flows" className="mt-6">
          {!cashFlows?.items.length ? (
            <EmptyState
              icon={<ArrowUpDown className="h-12 w-12 text-neutral-400" />}
              title="No cash flows"
              description="Cash flows will appear when holdings have investment or exit dates."
            />
          ) : (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-neutral-500">
                      <th className="px-4 py-3 font-medium">Date</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 font-medium">Holding</th>
                      <th className="px-4 py-3 font-medium text-right">
                        Amount
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cashFlows.items.map((flow, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="px-4 py-3 text-neutral-700">
                          {new Date(flow.date).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              flow.type === "distribution"
                                ? "success"
                                : "warning"
                            }
                          >
                            {flow.type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-neutral-600">
                          {flow.holding_name ?? "—"}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-3 text-right font-medium",
                            parseFloat(flow.amount) >= 0
                              ? "text-green-600"
                              : "text-red-600"
                          )}
                        >
                          {formatCurrency(
                            Math.abs(parseFloat(flow.amount)).toString()
                          )}
                          {parseFloat(flow.amount) < 0 && " (out)"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </TabsContent>

        {/* Pacing Tab */}
        <TabsContent value="pacing" className="mt-6">
          <PacingTab portfolioId={activeId ?? ""} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

