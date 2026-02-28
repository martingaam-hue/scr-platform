/**
 * ESG Impact Dashboard — types, React Query hooks, and helpers.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface ESGMetricsResponse {
  id: string;
  project_id: string;
  org_id: string;
  period: string;

  // Environmental
  carbon_footprint_tco2e: number | null;
  carbon_avoided_tco2e: number | null;
  renewable_energy_mwh: number | null;
  water_usage_cubic_m: number | null;
  waste_diverted_tonnes: number | null;
  biodiversity_score: number | null;

  // Social
  jobs_created: number | null;
  jobs_supported: number | null;
  local_procurement_pct: number | null;
  community_investment_eur: number | null;
  gender_diversity_pct: number | null;
  health_safety_incidents: number | null;

  // Governance
  board_independence_pct: number | null;
  audit_completed: boolean;
  esg_reporting_standard: string | null;

  // EU Taxonomy
  taxonomy_eligible: boolean;
  taxonomy_aligned: boolean;
  taxonomy_activity: string | null;

  // SFDR
  sfdr_article: number | null;

  // SDG contributions
  sdg_contributions: Record<
    string,
    { contribution_level: string; name?: string }
  > | null;

  // AI narrative
  esg_narrative: string | null;

  created_at: string;
  updated_at: string;
}

export interface ESGMetricsHistoryResponse {
  project_id: string;
  records: ESGMetricsResponse[];
}

export interface SFDRDistribution {
  article_6: number;
  article_8: number;
  article_9: number;
  unclassified: number;
}

export interface TopSDG {
  sdg_id: number;
  name: string;
  project_count: number;
}

export interface CarbonTrendPoint {
  period: string;
  total_carbon_avoided_tco2e: number;
  total_carbon_footprint_tco2e: number;
}

export interface ESGPortfolioTotals {
  total_projects: number;
  total_carbon_avoided_tco2e: number;
  total_renewable_energy_mwh: number;
  total_jobs_created: number;
  taxonomy_aligned_count: number;
  taxonomy_aligned_pct: number;
}

export interface ESGPortfolioSummaryResponse {
  totals: ESGPortfolioTotals;
  sfdr_distribution: SFDRDistribution;
  taxonomy_alignment_pct: number;
  top_sdgs: TopSDG[];
  carbon_trend: CarbonTrendPoint[];
  project_rows: ESGMetricsResponse[];
}

export interface ESGMetricsUpsertRequest {
  period: string;
  carbon_footprint_tco2e?: number | null;
  carbon_avoided_tco2e?: number | null;
  renewable_energy_mwh?: number | null;
  water_usage_cubic_m?: number | null;
  waste_diverted_tonnes?: number | null;
  biodiversity_score?: number | null;
  jobs_created?: number | null;
  jobs_supported?: number | null;
  local_procurement_pct?: number | null;
  community_investment_eur?: number | null;
  gender_diversity_pct?: number | null;
  health_safety_incidents?: number | null;
  board_independence_pct?: number | null;
  audit_completed?: boolean;
  esg_reporting_standard?: string | null;
  taxonomy_eligible?: boolean;
  taxonomy_aligned?: boolean;
  taxonomy_activity?: string | null;
  sfdr_article?: number | null;
  sdg_contributions?: Record<string, unknown> | null;
  esg_narrative?: string | null;
  regenerate_narrative?: boolean;
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const esgKeys = {
  all: ["esg"] as const,
  portfolioSummary: (portfolioId?: string, period?: string) =>
    [...esgKeys.all, "portfolio-summary", portfolioId, period] as const,
  projectMetrics: (projectId: string) =>
    [...esgKeys.all, "project", projectId, "metrics"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useESGPortfolioSummary(
  portfolioId?: string,
  period?: string
) {
  const params = new URLSearchParams();
  if (portfolioId) params.set("portfolio_id", portfolioId);
  if (period) params.set("period", period);
  const qs = params.toString() ? `?${params.toString()}` : "";

  return useQuery({
    queryKey: esgKeys.portfolioSummary(portfolioId, period),
    queryFn: () =>
      api
        .get<ESGPortfolioSummaryResponse>(`/esg/portfolio-summary${qs}`)
        .then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useESGProjectMetrics(projectId: string) {
  return useQuery({
    queryKey: esgKeys.projectMetrics(projectId),
    queryFn: () =>
      api
        .get<ESGMetricsHistoryResponse>(
          `/esg/projects/${projectId}/metrics`
        )
        .then((r) => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!projectId,
  });
}

export function useUpsertESGMetrics() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      data,
    }: {
      projectId: string;
      data: ESGMetricsUpsertRequest;
    }) =>
      api
        .put<ESGMetricsResponse>(
          `/esg/projects/${projectId}/metrics`,
          data
        )
        .then((r) => r.data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: esgKeys.all });
      qc.invalidateQueries({
        queryKey: esgKeys.projectMetrics(variables.projectId),
      });
    },
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

export const SDG_COLORS: Record<number, string> = {
  1: "#e5243b",
  2: "#dda63a",
  3: "#4c9f38",
  4: "#c5192d",
  5: "#ff3a21",
  6: "#26bde2",
  7: "#fcc30b",
  8: "#a21942",
  9: "#fd6925",
  10: "#dd1367",
  11: "#fd9d24",
  12: "#bf8b2e",
  13: "#3f7e44",
  14: "#0a97d9",
  15: "#56c02b",
  16: "#00689d",
  17: "#19486a",
};

export const SDG_NAMES: Record<number, string> = {
  1: "No Poverty",
  2: "Zero Hunger",
  3: "Good Health",
  4: "Quality Education",
  5: "Gender Equality",
  6: "Clean Water",
  7: "Affordable Energy",
  8: "Decent Work",
  9: "Industry & Innovation",
  10: "Reduced Inequalities",
  11: "Sustainable Cities",
  12: "Responsible Consumption",
  13: "Climate Action",
  14: "Life Below Water",
  15: "Life on Land",
  16: "Peace & Justice",
  17: "Partnerships",
};

export const SFDR_COLORS: Record<string, string> = {
  article_6: "#94a3b8",   // slate-400
  article_8: "#3b82f6",   // blue-500
  article_9: "#22c55e",   // green-500
  unclassified: "#e5e7eb", // gray-200
};

export function formatNumber(
  value: number | null | undefined,
  unit?: string,
  decimals = 0
): string {
  if (value === null || value === undefined) return "—";
  const formatted =
    value >= 1_000_000
      ? `${(value / 1_000_000).toFixed(1)}M`
      : value >= 1_000
      ? `${(value / 1_000).toFixed(1)}K`
      : value.toFixed(decimals);
  return unit ? `${formatted} ${unit}` : formatted;
}

/** Build CSV download URL for the current period filter */
export function buildExportUrl(period?: string): string {
  const base =
    (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") +
    "/esg/portfolio-summary/export";
  return period ? `${base}?period=${encodeURIComponent(period)}` : base;
}
