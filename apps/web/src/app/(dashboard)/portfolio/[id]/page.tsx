"use client";

import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  DollarSign,
  Link2,
  TrendingUp,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  cn,
} from "@scr/ui";
import {
  usePortfolio,
  useHoldings,
  usePortfolioMetrics,
  formatCurrency,
  formatMultiple,
  formatPercent,
  strategyLabel,
  fundTypeLabel,
  sfdrLabel,
  assetTypeLabel,
  holdingStatusColor,
  portfolioStatusColor,
} from "@/lib/portfolio";

// ── Page ────────────────────────────────────────────────────────────────────

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: portfolio, isLoading } = usePortfolio(id);
  const { data: metrics } = usePortfolioMetrics(id);
  const { data: holdings } = useHoldings(id);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!portfolio) {
    return (
      <EmptyState
        icon={<DollarSign className="h-12 w-12 text-neutral-400" />}
        title="Portfolio not found"
        description="This portfolio may have been deleted or you don't have access."
        action={
          <Button variant="outline" onClick={() => router.push("/portfolio")}>
            Back to Portfolio
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <button
          onClick={() => router.push("/portfolio")}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Portfolio
        </button>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-900">
                {portfolio.name}
              </h1>
              <Badge variant={portfolioStatusColor(portfolio.status)}>
                {portfolio.status.replace("_", " ")}
              </Badge>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-neutral-500">
              <span>{strategyLabel(portfolio.strategy)}</span>
              <span>{fundTypeLabel(portfolio.fund_type)}</span>
              {portfolio.vintage_year && (
                <span>Vintage {portfolio.vintage_year}</span>
              )}
              <Badge variant="neutral">
                {sfdrLabel(portfolio.sfdr_classification)}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-neutral-500">Target AUM</p>
            <p className="text-2xl font-semibold">
              {formatCurrency(portfolio.target_aum, portfolio.currency)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-neutral-500">Current AUM</p>
            <p className="text-2xl font-semibold">
              {formatCurrency(portfolio.current_aum, portfolio.currency)}
            </p>
            <div className="mt-2 h-2 rounded-full bg-neutral-200">
              <div
                className="h-2 rounded-full bg-primary-600"
                style={{
                  width: `${Math.min(
                    (parseFloat(portfolio.current_aum) /
                      parseFloat(portfolio.target_aum)) *
                      100,
                    100
                  )}%`,
                }}
              />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-neutral-500">Holdings</p>
            <p className="text-2xl font-semibold">
              {portfolio.holding_count}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-neutral-500">MOIC</p>
            <p className="text-2xl font-semibold">
              {metrics?.moic ? formatMultiple(metrics.moic) : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance metrics */}
      {metrics && (
        <Card>
          <CardContent className="p-6">
            <h3 className="mb-4 font-semibold text-neutral-900">
              Performance Metrics
            </h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <MetricItem
                label="IRR (Gross)"
                value={metrics.irr_gross ? formatPercent(metrics.irr_gross) : "—"}
              />
              <MetricItem
                label="IRR (Net)"
                value={metrics.irr_net ? formatPercent(metrics.irr_net) : "—"}
              />
              <MetricItem
                label="TVPI"
                value={metrics.tvpi ? formatMultiple(metrics.tvpi) : "—"}
              />
              <MetricItem
                label="DPI"
                value={metrics.dpi ? formatMultiple(metrics.dpi) : "—"}
              />
              <MetricItem
                label="RVPI"
                value={metrics.rvpi ? formatMultiple(metrics.rvpi) : "—"}
              />
              <MetricItem
                label="Total Value"
                value={formatCurrency(metrics.total_value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Holdings list */}
      <Card>
        <CardContent className="p-6">
          <h3 className="mb-4 font-semibold text-neutral-900">Holdings</h3>
          {!holdings?.items.length ? (
            <p className="text-sm text-neutral-400">No holdings yet.</p>
          ) : (
            <div className="space-y-3">
              {holdings.items.map((h) => {
                const moicVal = h.moic ? parseFloat(h.moic) : null;
                return (
                  <div
                    key={h.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <p className="font-medium text-neutral-900">
                          {h.asset_name}
                        </p>
                        <Badge variant={holdingStatusColor(h.status)}>
                          {h.status.replace("_", " ")}
                        </Badge>
                        <span className="text-xs text-neutral-400">
                          {assetTypeLabel(h.asset_type)}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-4 text-sm text-neutral-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(h.investment_date).toLocaleDateString()}
                        </span>
                        {h.project_id && (
                          <span className="flex items-center gap-1">
                            <Link2 className="h-3 w-3" />
                            Linked project
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-8 text-right">
                      <div>
                        <p className="text-xs text-neutral-500">Invested</p>
                        <p className="font-medium">
                          {formatCurrency(h.investment_amount, h.currency)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-500">Current</p>
                        <p className="font-medium">
                          {formatCurrency(h.current_value, h.currency)}
                        </p>
                      </div>
                      <div className="w-16">
                        <p className="text-xs text-neutral-500">MOIC</p>
                        <p
                          className={cn(
                            "font-semibold",
                            moicVal !== null && moicVal >= 1.5
                              ? "text-green-600"
                              : moicVal !== null && moicVal >= 1.0
                                ? "text-amber-600"
                                : moicVal !== null
                                  ? "text-red-600"
                                  : "text-neutral-400"
                          )}
                        >
                          {moicVal !== null ? formatMultiple(moicVal) : "—"}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Description */}
      {portfolio.description && (
        <Card>
          <CardContent className="p-6">
            <h3 className="mb-2 font-semibold text-neutral-900">About</h3>
            <p className="text-sm text-neutral-600 whitespace-pre-wrap">
              {portfolio.description}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-lg font-semibold text-neutral-900">{value}</p>
    </div>
  );
}
