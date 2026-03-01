/**
 * Market Data — React Query hooks for public economic indicators.
 * Backed by FRED (Federal Reserve Economic Data) and World Bank.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ExternalDataPoint {
  id: string;
  source: string;
  series_id: string;
  series_name: string;
  data_date: string;
  value: number;
  unit: string | null;
  fetched_at: string;
}

export interface MarketDataSummary {
  source: string;
  series_id: string;
  series_name: string;
  latest_date: string;
  latest_value: number;
  unit: string | null;
  change_pct: number | null;
}

export interface MarketDataSummaryResponse {
  indicators: MarketDataSummary[];
}

export interface SeriesGroup {
  source: string;
  series: {
    series_id: string;
    series_name: string;
    unit: string | null;
    latest_date: string | null;
    latest_value: number;
  }[];
}

export interface RefreshResponse {
  inserted: number;
  sources: string[];
  message: string;
}

// ── Query key factories ─────────────────────────────────────────────────────

export const marketDataKeys = {
  all: ["market-data"] as const,
  series: () => [...marketDataKeys.all, "series"] as const,
  seriesHistory: (source: string, seriesId: string, days?: number) =>
    [...marketDataKeys.all, "history", source, seriesId, days] as const,
  summary: () => [...marketDataKeys.all, "summary"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

/** List all available series grouped by source (fred, worldbank, ecb). */
export function useMarketDataSeries() {
  return useQuery({
    queryKey: marketDataKeys.series(),
    queryFn: async () => {
      const { data } = await api.get<SeriesGroup[]>("/market-data/series");
      return data;
    },
    staleTime: 15 * 60 * 1000, // 15 min
  });
}

/** Latest values + 1-day change for key indicators. */
export function useMarketDataSummary() {
  return useQuery({
    queryKey: marketDataKeys.summary(),
    queryFn: async () => {
      const { data } = await api.get<MarketDataSummaryResponse>("/market-data/summary");
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 min
    refetchInterval: 5 * 60 * 1000,
  });
}

/** Historical data for a specific source/series combination. */
export function useSeriesHistory(source: string, seriesId: string, days: number = 90) {
  return useQuery({
    queryKey: marketDataKeys.seriesHistory(source, seriesId, days),
    queryFn: async () => {
      const { data } = await api.get<ExternalDataPoint[]>(
        `/market-data/series/${encodeURIComponent(source)}/${encodeURIComponent(seriesId)}`,
        { params: { days } }
      );
      return data;
    },
    enabled: Boolean(source) && Boolean(seriesId),
    staleTime: 10 * 60 * 1000, // 10 min
  });
}

/** Manually trigger a market data refresh (admin). */
export function useRefreshMarketData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<RefreshResponse>("/market-data/refresh");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketDataKeys.all });
    },
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Format a value with appropriate precision and unit suffix. */
export function formatIndicatorValue(value: number, unit: string | null): string {
  if (unit === "percent") return `${value.toFixed(2)}%`;
  if (unit === "index") return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

/** Return a colour class based on whether a change is positive/negative for a given series. */
export function changePctColor(changePct: number | null, seriesId: string): string {
  if (changePct === null) return "text-gray-500";
  // For unemployment and inflation, up is bad; for most financial series up is good
  const badIfUp = ["UNRATE", "CPIAUCSL", "MORTGAGE30US"];
  const isNegative = changePct < 0;
  const isBadSeries = badIfUp.includes(seriesId);
  if (changePct === 0) return "text-gray-500";
  if (isBadSeries) return isNegative ? "text-emerald-600" : "text-red-600";
  return isNegative ? "text-red-600" : "text-emerald-600";
}

/** Short human-readable label for a source identifier. */
export const SOURCE_LABELS: Record<string, string> = {
  fred: "FRED (Federal Reserve)",
  worldbank: "World Bank",
  ecb: "ECB",
};
