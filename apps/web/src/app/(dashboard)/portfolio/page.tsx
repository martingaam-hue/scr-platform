"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowUpDown,
  BarChart3,
  DollarSign,
  Leaf,
  PieChart,
  Plus,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  DataTable,
  EmptyState,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
  cn,
} from "@scr/ui";
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
  formatCurrency,
  formatPercent,
  formatMultiple,
  strategyLabel,
  sfdrLabel,
  assetTypeLabel,
  holdingStatusColor,
} from "@/lib/portfolio";

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
  const router = useRouter();
  const canCreate = usePermission("create", "portfolio");

  // Load list of portfolios and select first one
  const { data: portfolioList } = usePortfolios();
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  const activeId = selectedId ?? portfolioList?.items[0]?.id;

  const { data: portfolio } = usePortfolio(activeId);
  const { data: metrics } = usePortfolioMetrics(activeId);
  const { data: holdings } = useHoldings(activeId);
  const { data: cashFlows } = useCashFlows(activeId);
  const { data: allocation } = useAllocation(activeId);

  if (!portfolioList?.items.length) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-neutral-900">Portfolio</h1>
        </div>
        <EmptyState
          icon={<Wallet className="h-12 w-12 text-neutral-400" />}
          title="No portfolios yet"
          description="Create your first portfolio to start tracking investments."
          action={
            canCreate ? (
              <Button onClick={() => {}}>
                <Plus className="mr-2 h-4 w-4" />
                New Portfolio
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header + portfolio selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
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
      </Tabs>
    </div>
  );
}
