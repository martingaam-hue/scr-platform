/**
 * Alley Analytics — types and React Query hooks.
 * Covers portfolio-level analytics endpoints under /alley/analytics.
 */

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  MOCK_ALLEY_OVERVIEW,
  MOCK_STAGE_DISTRIBUTION,
  MOCK_SCORE_DISTRIBUTION,
  MOCK_DOC_COMPLETENESS,
} from "@/lib/mock-data";

// ── Types ──────────────────────────────────────────────────────────────────

export interface PipelineOverview {
  total_projects: number;
  total_mw: number;
  total_value: number;
  currency: string;
  scored_projects: number;
  avg_score: number;
  stage_counts: Record<string, number>;
}

export interface StageDistributionItem {
  stage: string;
  count: number;
  total_mw: number;
  total_value: number;
}

export interface ScoreDistributionItem {
  bucket: string;
  count: number;
}

export interface RiskHeatmapCell {
  project_id: string;
  project_name: string;
  technical: number;
  financial: number;
  regulatory: number;
  esg: number;
  market: number;
  overall_risk_level: string;
}

export interface DocumentCompletenessItem {
  project_id: string;
  project_name: string;
  uploaded_count: number;
  expected_count: number;
  completeness_pct: number;
  missing_types: string[];
}

export interface ProjectCompareItem {
  project_id: string;
  project_name: string;
  stage: string;
  asset_type: string;
  geography: string;
  overall_score: number;
  total_investment: number;
  currency: string;
  capacity_mw: number;
  risk_level: string;
}

// ── Query key factory ──────────────────────────────────────────────────────

export const alleyAnalyticsKeys = {
  all: ["alley-analytics"] as const,
  overview: () => [...alleyAnalyticsKeys.all, "overview"] as const,
  stageDistribution: () =>
    [...alleyAnalyticsKeys.all, "stage-distribution"] as const,
  scoreDistribution: () =>
    [...alleyAnalyticsKeys.all, "score-distribution"] as const,
  riskHeatmap: () => [...alleyAnalyticsKeys.all, "risk-heatmap"] as const,
  documentCompleteness: () =>
    [...alleyAnalyticsKeys.all, "document-completeness"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useAlleyOverview() {
  return useQuery({
    queryKey: alleyAnalyticsKeys.overview(),
    queryFn: () =>
      api
        .get<PipelineOverview>("/alley/analytics")
        .then((r) => r.data)
        .catch(() => MOCK_ALLEY_OVERVIEW),
  });
}

export function useStageDistribution() {
  return useQuery({
    queryKey: alleyAnalyticsKeys.stageDistribution(),
    queryFn: () =>
      api
        .get<StageDistributionItem[]>("/alley/analytics/stage-distribution")
        .then((r) => (r.data?.length ? r.data : MOCK_STAGE_DISTRIBUTION))
        .catch(() => MOCK_STAGE_DISTRIBUTION),
  });
}

export function useScoreDistribution() {
  return useQuery({
    queryKey: alleyAnalyticsKeys.scoreDistribution(),
    queryFn: () =>
      api
        .get<ScoreDistributionItem[]>("/alley/analytics/score-distribution")
        .then((r) => (r.data?.length ? r.data : MOCK_SCORE_DISTRIBUTION))
        .catch(() => MOCK_SCORE_DISTRIBUTION),
  });
}

export function useRiskHeatmap() {
  return useQuery({
    queryKey: alleyAnalyticsKeys.riskHeatmap(),
    queryFn: () =>
      api
        .get<RiskHeatmapCell[]>("/alley/analytics/risk-heatmap")
        .then((r) => r.data),
  });
}

export function useDocumentCompleteness() {
  return useQuery({
    queryKey: alleyAnalyticsKeys.documentCompleteness(),
    queryFn: () =>
      api
        .get<DocumentCompletenessItem[]>(
          "/alley/analytics/document-completeness"
        )
        .then((r) => (r.data?.length ? r.data : MOCK_DOC_COMPLETENESS))
        .catch(() => MOCK_DOC_COMPLETENESS),
  });
}

export function useCompareProjects() {
  return useMutation({
    mutationFn: (projectIds: string[]) =>
      api
        .post<ProjectCompareItem[]>("/alley/analytics/compare", {
          project_ids: projectIds,
        })
        .then((r) => r.data),
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function riskLevelColor(level: string): string {
  switch (level.toLowerCase()) {
    case "critical":
    case "high":
      return "text-red-600";
    case "medium":
      return "text-amber-600";
    case "low":
      return "text-green-600";
    default:
      return "text-neutral-500";
  }
}

export function riskCellBg(score: number): string {
  if (score >= 70) return "bg-red-100 text-red-700";
  if (score >= 40) return "bg-amber-100 text-amber-700";
  return "bg-green-100 text-green-700";
}

export function formatCurrency(
  value: number,
  currency: string = "USD"
): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B ${currency}`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M ${currency}`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K ${currency}`;
  }
  return `${value.toLocaleString()} ${currency}`;
}
