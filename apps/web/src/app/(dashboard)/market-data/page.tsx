"use client";

import { useState } from "react";
import {
  BarChart2,
  Loader2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
} from "@scr/ui";
import {
  useMarketDataSummary,
  useMarketDataSeries,
  useSeriesHistory,
  useRefreshMarketData,
  formatIndicatorValue,
  changePctColor,
  SOURCE_LABELS,
  type MarketDataSummary,
  type ExternalDataPoint,
} from "@/lib/market-data";

// ── Key indicator card ────────────────────────────────────────────────────────

function IndicatorCard({ indicator }: { indicator: MarketDataSummary }) {
  const changeColor = changePctColor(indicator.change_pct, indicator.series_id);
  const isUp = indicator.change_pct !== null && indicator.change_pct > 0;
  const isDown = indicator.change_pct !== null && indicator.change_pct < 0;

  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-gray-500 truncate mb-1">{indicator.series_name}</p>
        <p className="text-2xl font-semibold text-gray-900 tabular-nums">
          {formatIndicatorValue(indicator.latest_value, indicator.unit)}
        </p>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-gray-400">as of {indicator.latest_date}</span>
          {indicator.change_pct !== null ? (
            <span className={`flex items-center gap-0.5 text-xs font-medium ${changeColor}`}>
              {isUp ? <TrendingUp className="h-3 w-3" /> : isDown ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
              {Math.abs(indicator.change_pct).toFixed(3)}%
            </span>
          ) : (
            <span className="text-xs text-gray-400">no change</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Inline sparkline (SVG) ────────────────────────────────────────────────────

function Sparkline({ points }: { points: ExternalDataPoint[] }) {
  if (points.length < 2) return null;

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 200;
  const H = 40;
  const step = W / (points.length - 1);

  const path = points
    .map((p, i) => {
      const x = i * step;
      const y = H - ((p.value - min) / range) * H;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

  const lastY = H - ((values[values.length - 1] - min) / range) * H;
  const isUp = values[values.length - 1] >= values[0];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-10" preserveAspectRatio="none">
      <path d={path} fill="none" stroke={isUp ? "#10b981" : "#ef4444"} strokeWidth="1.5" />
      <circle cx={W} cy={lastY} r="2" fill={isUp ? "#10b981" : "#ef4444"} />
    </svg>
  );
}

// ── Series history chart card ──────────────────────────────────────────────────

function SeriesCard({ source, seriesId, seriesName, unit }: {
  source: string;
  seriesId: string;
  seriesName: string;
  unit: string | null;
}) {
  const { data: points, isLoading } = useSeriesHistory(source, seriesId, 90);

  const latest = points?.[points.length - 1];
  const oldest = points?.[0];
  const changePct =
    oldest && latest && oldest.value !== 0
      ? ((latest.value - oldest.value) / Math.abs(oldest.value)) * 100
      : null;

  return (
    <Card>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-medium text-gray-700 leading-tight">{seriesName}</p>
            <p className="text-xs text-gray-400">{source.toUpperCase()} · {seriesId}</p>
          </div>
          {latest && (
            <span className="text-sm font-semibold text-gray-900 tabular-nums shrink-0">
              {formatIndicatorValue(latest.value, unit)}
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="h-10 flex items-center justify-center">
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          </div>
        ) : points && points.length > 1 ? (
          <Sparkline points={points} />
        ) : (
          <div className="h-10 flex items-center text-xs text-gray-400">No data</div>
        )}

        {changePct !== null && (
          <p className={`text-xs text-right ${changePctColor(changePct, seriesId)}`}>
            90d: {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Source filter badge ───────────────────────────────────────────────────────

function SourceBadge({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
        active
          ? "bg-indigo-600 text-white"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      }`}
    >
      {label}
    </button>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function MarketDataPage() {
  const [activeSource, setActiveSource] = useState<string | null>(null);

  const { data: summary, isLoading: summaryLoading } = useMarketDataSummary();
  const { data: seriesGroups, isLoading: seriesLoading } = useMarketDataSeries();
  const { mutate: refresh, isPending: refreshing } = useRefreshMarketData();

  const availableSources = seriesGroups?.map((g) => g.source) ?? [];

  const filteredGroups =
    activeSource === null
      ? seriesGroups ?? []
      : (seriesGroups ?? []).filter((g) => g.source === activeSource);

  const totalSeries = filteredGroups.reduce((n, g) => n + g.series.length, 0);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <BarChart2 className="h-6 w-6 text-indigo-500" />
            Market Intelligence
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Public economic indicators — FRED, World Bank
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refresh()}
          disabled={refreshing}
        >
          {refreshing ? (
            <Loader2 className="h-3 w-3 animate-spin mr-1.5" />
          ) : (
            <RefreshCw className="h-3 w-3 mr-1.5" />
          )}
          Refresh
        </Button>
      </div>

      {/* Key indicators row */}
      <section>
        <h2 className="text-sm font-medium text-gray-700 mb-3">Key Indicators</h2>
        {summaryLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading indicators…
          </div>
        ) : !summary?.indicators.length ? (
          <EmptyState
            title="No indicators available"
            description="Run a data refresh to populate market indicators."
          />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {summary.indicators.map((ind) => (
              <IndicatorCard key={`${ind.source}/${ind.series_id}`} indicator={ind} />
            ))}
          </div>
        )}
      </section>

      {/* Source filter */}
      {availableSources.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500">Source:</span>
          <SourceBadge
            label="All"
            active={activeSource === null}
            onClick={() => setActiveSource(null)}
          />
          {availableSources.map((src) => (
            <SourceBadge
              key={src}
              label={SOURCE_LABELS[src] ?? src.toUpperCase()}
              active={activeSource === src}
              onClick={() => setActiveSource(src)}
            />
          ))}
        </div>
      )}

      {/* Series grid */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-gray-700">
            Economic Series
            {totalSeries > 0 && (
              <span className="ml-2 text-xs text-gray-400 font-normal">{totalSeries} series</span>
            )}
          </h2>
        </div>

        {seriesLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading series…
          </div>
        ) : filteredGroups.length === 0 ? (
          <EmptyState
            title="No data yet"
            description="Click Refresh to fetch FRED and World Bank data."
          />
        ) : (
          <div className="space-y-6">
            {filteredGroups.map((group) => (
              <div key={group.source}>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  {SOURCE_LABELS[group.source] ?? group.source}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {group.series.map((s) => (
                    <SeriesCard
                      key={`${group.source}/${s.series_id}`}
                      source={group.source}
                      seriesId={s.series_id}
                      seriesName={s.series_name}
                      unit={s.unit}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
