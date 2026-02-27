/**
 * Capital Efficiency types and React Query hooks.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface EfficiencyMetrics {
  id: string;
  org_id: string;
  portfolio_id: string | null;
  period_start: string;
  period_end: string;
  due_diligence_savings: number;
  legal_automation_savings: number;
  risk_analytics_savings: number;
  tax_credit_value_captured: number;
  time_saved_hours: number;
  deals_screened: number;
  deals_closed: number;
  avg_time_to_close_days: number;
  portfolio_irr_improvement: number | null;
  industry_avg_dd_cost: number;
  industry_avg_time_to_close: number;
  platform_efficiency_score: number;
  total_savings: number;
  breakdown: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface BreakdownCategory {
  name: string;
  value: number;
  percentage: number;
  vs_industry: string;
}

export interface EfficiencyBreakdown {
  categories: BreakdownCategory[];
  totals: Record<string, number>;
}

export interface Benchmark {
  platform: Record<string, number>;
  industry_avg: Record<string, number>;
  percentile: number;
  outperforming: string[];
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const capitalEfficiencyKeys = {
  all: ["capital-efficiency"] as const,
  metrics: (portfolioId?: string) =>
    [...capitalEfficiencyKeys.all, "metrics", portfolioId ?? "org"] as const,
  breakdown: () => [...capitalEfficiencyKeys.all, "breakdown"] as const,
  benchmark: () => [...capitalEfficiencyKeys.all, "benchmark"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useCapitalEfficiency(portfolioId?: string) {
  return useQuery({
    queryKey: capitalEfficiencyKeys.metrics(portfolioId),
    queryFn: () => {
      const params = portfolioId ? `?portfolio_id=${portfolioId}` : "";
      return api
        .get<EfficiencyMetrics>(`/capital-efficiency${params}`)
        .then((r) => r.data);
    },
  });
}

export function useEfficiencyBreakdown() {
  return useQuery({
    queryKey: capitalEfficiencyKeys.breakdown(),
    queryFn: () =>
      api
        .get<EfficiencyBreakdown>("/capital-efficiency/breakdown")
        .then((r) => r.data),
  });
}

export function useEfficiencyBenchmark() {
  return useQuery({
    queryKey: capitalEfficiencyKeys.benchmark(),
    queryFn: () =>
      api
        .get<Benchmark>("/capital-efficiency/benchmark")
        .then((r) => r.data),
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function formatSavings(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function efficiencyScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export function efficiencyScoreBg(score: number): string {
  if (score >= 80) return "bg-green-50 border-green-200";
  if (score >= 60) return "bg-amber-50 border-amber-200";
  return "bg-red-50 border-red-200";
}

export function percentileLabel(percentile: number): string {
  if (percentile >= 90) return "Top 10%";
  if (percentile >= 75) return "Top 25%";
  if (percentile >= 50) return "Above Average";
  return "Below Average";
}
