/**
 * Investor Signal Score types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface CriterionResult {
  name: string;
  description: string;
  points: number;
  max_points: number;
  met: boolean;
  details: string;
}

export interface DimensionScore {
  score: number;
  weight: number;
  details: Record<string, unknown> | null;
  gaps: string[];
  recommendations: string[];
}

export interface DimensionDetail {
  score: number;
  weight: number;
  gaps: string[];
  recommendations: string[];
  details: Record<string, unknown> | null;
  criteria: CriterionResult[];
}

export interface InvestorSignalScore {
  id: string;
  org_id: string;
  overall_score: number;
  financial_capacity: DimensionScore;
  risk_management: DimensionScore;
  investment_strategy: DimensionScore;
  team_experience: DimensionScore;
  esg_commitment: DimensionScore;
  platform_readiness: DimensionScore;
  score_change: number | null;
  previous_score: number | null;
  calculated_at: string;
}

export interface DealAlignmentRequest {
  project_id: string;
}

export interface DealAlignmentFactor {
  dimension: string;
  investor_score: number;
  project_score: number;
  score: number;
  impact: string;
}

export interface DealAlignment {
  project_id: string;
  investor_score: number;
  alignment_score: number;
  alignment_factors: DealAlignmentFactor[];
  recommendation: string;
}

export interface ImprovementAction {
  title: string;
  description: string;
  estimated_impact: number;
  effort_level: "low" | "medium" | "high";
  category: string;
  link_to: string | null;
}

export interface ScoreFactorItem {
  label: string;
  impact: "positive" | "negative";
  value: string;
  dimension: string;
}

export interface ScoreHistoryItem {
  id: string;
  overall_score: number;
  score_change: number | null;
  calculated_at: string;
}

export interface BenchmarkData {
  your_score: number;
  platform_average: number;
  top_quartile: number;
  percentile: number;
}

export interface TopMatchItem {
  project_id: string;
  project_name: string;
  alignment_score: number;
  recommendation: string;
  project_type: string | null;
  geography_country: string | null;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const investorSignalKeys = {
  all: ["investor-signal-score"] as const,
  latest: () => [...investorSignalKeys.all, "latest"] as const,
  history: () => [...investorSignalKeys.all, "history"] as const,
  improvementPlan: () => [...investorSignalKeys.all, "improvement-plan"] as const,
  factors: () => [...investorSignalKeys.all, "factors"] as const,
  benchmark: () => [...investorSignalKeys.all, "benchmark"] as const,
  topMatches: () => [...investorSignalKeys.all, "top-matches"] as const,
  dimension: (dim: string) => [...investorSignalKeys.all, "dimension", dim] as const,
  alignment: (projectId: string) =>
    [...investorSignalKeys.all, "alignment", projectId] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useInvestorSignalScore() {
  return useQuery({
    queryKey: investorSignalKeys.latest(),
    queryFn: () =>
      api
        .get<InvestorSignalScore>("/investor-signal-score")
        .then((r) => r.data),
    retry: false,
  });
}

export function useCalculateInvestorScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api
        .post<InvestorSignalScore>("/investor-signal-score/calculate")
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: investorSignalKeys.all });
    },
  });
}

export function useScoreHistory(limit = 12) {
  return useQuery({
    queryKey: [...investorSignalKeys.history(), limit],
    queryFn: () =>
      api
        .get<ScoreHistoryItem[]>(`/investor-signal-score/history?limit=${limit}`)
        .then((r) => r.data),
    retry: false,
  });
}

export function useImprovementPlan() {
  return useQuery({
    queryKey: investorSignalKeys.improvementPlan(),
    queryFn: () =>
      api
        .get<ImprovementAction[]>("/investor-signal-score/improvement-plan")
        .then((r) => r.data),
    retry: false,
  });
}

export function useScoreFactors() {
  return useQuery({
    queryKey: investorSignalKeys.factors(),
    queryFn: () =>
      api
        .get<ScoreFactorItem[]>("/investor-signal-score/factors")
        .then((r) => r.data),
    retry: false,
  });
}

export function useBenchmark() {
  return useQuery({
    queryKey: investorSignalKeys.benchmark(),
    queryFn: () =>
      api
        .get<BenchmarkData>("/investor-signal-score/benchmark")
        .then((r) => r.data),
    retry: false,
  });
}

export function useTopMatches(limit = 5) {
  return useQuery({
    queryKey: [...investorSignalKeys.topMatches(), limit],
    queryFn: () =>
      api
        .get<TopMatchItem[]>(`/investor-signal-score/top-matches?limit=${limit}`)
        .then((r) => r.data),
    retry: false,
  });
}

export function useDimensionDetails(dimension: string) {
  return useQuery({
    queryKey: investorSignalKeys.dimension(dimension),
    queryFn: () =>
      api
        .get<DimensionDetail>(`/investor-signal-score/details/${dimension}`)
        .then((r) => r.data),
    retry: false,
    enabled: !!dimension,
  });
}

export function useDealAlignment(projectId?: string) {
  return useQuery({
    queryKey: investorSignalKeys.alignment(projectId ?? ""),
    queryFn: () =>
      api
        .post<DealAlignment>("/investor-signal-score/deal-alignment", {
          project_id: projectId,
        })
        .then((r) => r.data),
    enabled: !!projectId,
    retry: false,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export function scoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-50 dark:bg-green-950/20";
  if (score >= 60) return "bg-amber-50 dark:bg-amber-950/20";
  return "bg-red-50 dark:bg-red-950/20";
}

export function scoreBorderColor(score: number): string {
  if (score >= 80) return "border-green-200 dark:border-green-900";
  if (score >= 60) return "border-amber-200 dark:border-amber-900";
  return "border-red-200 dark:border-red-900";
}

export function scoreBarColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-500";
}

export function recommendationColor(
  rec: string
): "success" | "info" | "warning" | "error" {
  switch (rec) {
    case "strong_fit":
      return "success";
    case "good_fit":
      return "info";
    case "marginal_fit":
      return "warning";
    default:
      return "error";
  }
}

export function recommendationLabel(rec: string): string {
  const labels: Record<string, string> = {
    strong_fit: "Strong Fit",
    good_fit: "Good Fit",
    marginal_fit: "Marginal Fit",
    poor_fit: "Poor Fit",
  };
  return labels[rec] ?? rec;
}

export function dimensionLabel(key: string): string {
  const labels: Record<string, string> = {
    financial_capacity: "Financial Capacity",
    risk_management: "Risk Management",
    investment_strategy: "Investment Strategy",
    team_experience: "Team Experience",
    esg_commitment: "ESG Commitment",
    platform_readiness: "Platform Readiness",
  };
  return labels[key] ?? key;
}

export function dimensionIcon(key: string): string {
  const icons: Record<string, string> = {
    financial_capacity: "DollarSign",
    risk_management: "ShieldCheck",
    investment_strategy: "Target",
    team_experience: "Users",
    esg_commitment: "Leaf",
    platform_readiness: "BarChart3",
  };
  return icons[key] ?? "Circle";
}

export const DIMENSION_KEYS: Array<keyof InvestorSignalScore> = [
  "financial_capacity",
  "risk_management",
  "investment_strategy",
  "team_experience",
  "esg_commitment",
  "platform_readiness",
];
