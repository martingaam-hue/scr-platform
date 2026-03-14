"use client";

import { useState } from "react";
import {
  BarChart3,
  Loader2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Badge, Card, CardContent, InfoBanner, cn } from "@scr/ui";
import {
  usePortfolios,
  usePortfolioMetrics,
  useAllocation,
  useHoldings,
  formatCurrency,
  formatMultiple,
  type AllocationBreakdown,
  type HoldingResponse,
} from "@/lib/portfolio";

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_PORTFOLIOS = {
  items: [{ id: "mock-port-001", name: "SCR Infrastructure Fund I" }],
  total: 1,
};

const MOCK_METRICS = {
  total_invested: "238000000",
  total_value: "276000000",
  irr_net: "0.142",
  tvpi: "1.31",
  dpi: "0.00",
  moic: "1.31",
};

const MOCK_ALLOCATION = {
  by_asset_type: [
    { name: "Equity", percentage: "100.0", value: "238000000" },
  ] as AllocationBreakdown[],
  by_sector: [
    { name: "Solar", percentage: "33.1", value: "78800000" },
    { name: "Wind", percentage: "23.9", value: "56900000" },
    { name: "Infrastructure", percentage: "15.9", value: "37900000" },
    { name: "Hydro", percentage: "12.9", value: "30700000" },
    { name: "BESS", percentage: "7.2", value: "17100000" },
    { name: "Biomass", percentage: "7.0", value: "16600000" },
  ] as AllocationBreakdown[],
  by_geography: [
    { name: "Switzerland", percentage: "21.8", value: "52000000" },
    { name: "Spain", percentage: "18.9", value: "45000000" },
    { name: "UK", percentage: "17.2", value: "41000000" },
    { name: "Italy", percentage: "16.0", value: "38000000" },
    { name: "Norway", percentage: "13.4", value: "32000000" },
    { name: "Sweden", percentage: "5.0", value: "12000000" },
    { name: "Lithuania", percentage: "7.7", value: "18000000" },
  ] as AllocationBreakdown[],
  by_stage: [
    { name: "Active", percentage: "100.0", value: "238000000" },
  ] as AllocationBreakdown[],
};

const MOCK_HOLDINGS = [
  { id: "h1", asset_name: "Helios Solar Portfolio Iberia", asset_type: "solar", investment_amount: "45000000", current_value: "54200000", moic: "1.20", status: "active" },
  { id: "h2", asset_name: "Nordvik Wind Farm II", asset_type: "wind", investment_amount: "32000000", current_value: "35600000", moic: "1.11", status: "active" },
  { id: "h3", asset_name: "Adriatic Infrastructure Holdings", asset_type: "infrastructure", investment_amount: "38000000", current_value: "44100000", moic: "1.16", status: "active" },
  { id: "h4", asset_name: "Baltic BESS Grid Storage", asset_type: "bess", investment_amount: "18000000", current_value: "17200000", moic: "0.96", status: "active" },
  { id: "h5", asset_name: "Alpine Hydro Partners", asset_type: "hydro", investment_amount: "52000000", current_value: "65400000", moic: "1.26", status: "active" },
  { id: "h6", asset_name: "Nordic Biomass Energy", asset_type: "biomass", investment_amount: "12000000", current_value: "12800000", moic: "1.07", status: "active" },
  { id: "h7", asset_name: "Thames Clean Energy Hub", asset_type: "wind", investment_amount: "41000000", current_value: "46700000", moic: "1.14", status: "active" },
] as HoldingResponse[];

// ── Colours ───────────────────────────────────────────────────────────────────

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316", "#84cc16"];

// ── Metric Card ───────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <Card className={cn(highlight && "border-indigo-200 bg-indigo-50/40")}>
      <CardContent className="p-4">
        <p className="text-xs text-gray-500">{label}</p>
        <p className={cn("text-xl font-bold mt-0.5", highlight ? "text-indigo-700" : "text-gray-900")}>
          {value}
        </p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── Allocation Pie ────────────────────────────────────────────────────────────

function AllocationPie({
  data,
  title,
}: {
  data: AllocationBreakdown[];
  title: string;
}) {
  const chartData = data.map((d) => ({
    name: d.name,
    value: parseFloat(d.percentage),
    absValue: parseFloat(d.value),
  }));

  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm font-medium text-gray-700 mb-3">{title}</p>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label={({ name, value }) => `${name} ${value.toFixed(0)}%`}
              labelLine={false}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ── Holdings Bar Chart ────────────────────────────────────────────────────────

function HoldingsBarChart({ holdings }: { holdings: HoldingResponse[] }) {
  const data = holdings
    .slice(0, 10)
    .map((h) => ({
      name: h.asset_name.length > 14 ? h.asset_name.slice(0, 14) + "…" : h.asset_name,
      invested: parseFloat(h.investment_amount),
      current: parseFloat(h.current_value),
    }))
    .sort((a, b) => b.current - a.current);

  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm font-medium text-gray-700 mb-3">
          Holdings — Invested vs Current Value (top 10)
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" />
            <YAxis tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="invested" name="Invested" fill="#c7d2fe" radius={[3, 3, 0, 0]} />
            <Bar dataKey="current" name="Current" fill="#6366f1" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PortfolioAnalyticsPage() {
  const { data: portfolioListData, isLoading: loadingList } = usePortfolios();
  const portfolioList = portfolioListData ?? MOCK_PORTFOLIOS;
  const portfolios = portfolioList?.items ?? [];

  const [selectedId, setSelectedId] = useState<string>("");
  const activeId = selectedId || portfolios[0]?.id || "";

  const { data: metricsData, isLoading: loadingMetrics } = usePortfolioMetrics(
    activeId || undefined
  );
  const { data: allocationData, isLoading: loadingAlloc } = useAllocation(
    activeId || undefined
  );
  const { data: holdingsData, isLoading: loadingHoldings } = useHoldings(
    activeId || undefined
  );

  const metrics = metricsData ?? MOCK_METRICS;
  const allocation = allocationData ?? MOCK_ALLOCATION;

  if (loadingList && !portfolioListData) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  const holdings = holdingsData?.items ?? MOCK_HOLDINGS;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-indigo-500" />
            Portfolio Analytics
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Performance, allocation, and holdings breakdown
          </p>
        </div>

        {/* Portfolio selector */}
        <select
          value={activeId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {portfolios.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <InfoBanner>
        <strong>Portfolio Analytics</strong> provides performance, allocation, and risk breakdowns across
        your fund&apos;s holdings. Drill into sector, geography, and vintage diversification, and benchmark
        performance against your target return profile.
      </InfoBanner>

      {/* KPI row */}
      {loadingMetrics && !metricsData ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </div>
      ) : metrics ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <MetricCard label="Total Invested" value={formatCurrency(parseFloat(metrics.total_invested))} highlight />
          <MetricCard label="Total Value" value={formatCurrency(parseFloat(metrics.total_value))} />
          <MetricCard label="Net IRR" value={metrics.irr_net ? `${(parseFloat(metrics.irr_net) * 100).toFixed(1)}%` : "—"} />
          <MetricCard label="TVPI" value={formatMultiple(parseFloat(metrics.tvpi ?? "0"))} />
          <MetricCard label="DPI" value={formatMultiple(parseFloat(metrics.dpi ?? "0"))} />
          <MetricCard label="MOIC" value={formatMultiple(parseFloat(metrics.moic ?? "0"))} />
        </div>
      ) : (
        <p className="text-sm text-gray-400">No metrics available for this portfolio.</p>
      )}

      {/* Holdings chart */}
      {!loadingHoldings && holdings.length > 0 && (
        <HoldingsBarChart holdings={holdings} />
      )}

      {/* Allocation pies */}
      {loadingAlloc && !allocationData ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </div>
      ) : allocation ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {allocation.by_asset_type.length > 0 && (
            <AllocationPie data={allocation.by_asset_type} title="By Asset Type" />
          )}
          {allocation.by_sector.length > 0 && (
            <AllocationPie data={allocation.by_sector} title="By Sector" />
          )}
          {allocation.by_geography.length > 0 && (
            <AllocationPie data={allocation.by_geography} title="By Geography" />
          )}
          {allocation.by_stage.length > 0 && (
            <AllocationPie data={allocation.by_stage} title="By Stage" />
          )}
        </div>
      ) : null}

      {/* Holdings table */}
      {!loadingHoldings && holdings.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">
              Holdings ({holdings.length})
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-gray-500 text-xs">
                    <th className="text-left py-2 pr-4">Asset</th>
                    <th className="text-left py-2 pr-4">Type</th>
                    <th className="text-right py-2 pr-4">Invested</th>
                    <th className="text-right py-2 pr-4">Current Value</th>
                    <th className="text-right py-2 pr-4">MOIC</th>
                    <th className="text-left py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => {
                    const moic = h.moic ? parseFloat(h.moic) : null;
                    const gain =
                      parseFloat(h.current_value) - parseFloat(h.investment_amount);
                    return (
                      <tr key={h.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-2.5 pr-4 font-medium text-gray-900">{h.asset_name}</td>
                        <td className="py-2.5 pr-4 text-gray-500 capitalize">
                          {h.asset_type.replace(/_/g, " ")}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          {formatCurrency(parseFloat(h.investment_amount))}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          <span className={gain >= 0 ? "text-green-700" : "text-red-600"}>
                            {formatCurrency(parseFloat(h.current_value))}
                          </span>
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          {moic != null ? formatMultiple(moic) : "—"}
                        </td>
                        <td className="py-2.5">
                          <Badge
                            variant={
                              h.status === "active"
                                ? "success"
                                : h.status === "exited"
                                ? "neutral"
                                : "info"
                            }
                          >
                            {h.status}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
