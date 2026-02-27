/**
 * Investor Signal Score types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface DimensionScore {
  score: number;
  weight: number;
  details: Record<string, unknown> | null;
  gaps: string[];
  recommendations: string[];
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

// ── Query keys ─────────────────────────────────────────────────────────────

export const investorSignalKeys = {
  all: ["investor-signal-score"] as const,
  latest: () => [...investorSignalKeys.all, "latest"] as const,
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
    retry: false, // 404 expected when no score yet
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
  if (score >= 80) return "bg-green-50";
  if (score >= 60) return "bg-amber-50";
  return "bg-red-50";
}

export function scoreBorderColor(score: number): string {
  if (score >= 80) return "border-green-300";
  if (score >= 60) return "border-amber-300";
  return "border-red-300";
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

export const DIMENSION_KEYS: Array<keyof InvestorSignalScore> = [
  "financial_capacity",
  "risk_management",
  "investment_strategy",
  "team_experience",
  "esg_commitment",
  "platform_readiness",
];
