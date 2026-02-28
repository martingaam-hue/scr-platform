/**
 * Insurance module — types and React Query hooks.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface CoverageRecommendation {
  policy_type: string;
  label: string;
  is_mandatory: boolean;
  typical_coverage_pct: number;
  rationale: string;
  priority: "critical" | "high" | "medium" | "low";
}

export interface InsuranceImpactResponse {
  project_id: string;
  project_name: string;
  project_type: string;
  geography: string;
  total_investment: number;
  currency: string;
  recommended_coverage_types: string[];
  estimated_annual_premium_pct: number;
  estimated_annual_premium: number;
  risk_reduction_score: number;
  coverage_adequacy: "excellent" | "good" | "partial" | "insufficient";
  uncovered_risk_areas: string[];
  irr_impact_bps: number;
  npv_premium_cost: number;
  recommendations: CoverageRecommendation[];
  ai_narrative: string;
  analyzed_at: string;
}

export interface InsuranceSummaryResponse {
  project_id: string;
  coverage_adequacy: string;
  risk_reduction_score: number;
  estimated_annual_premium: number;
  currency: string;
  coverage_gaps: string[];
  top_recommendation: string | null;
}

// ── Query Keys ───────────────────────────────────────────────────────────────

export const insuranceKeys = {
  all: ["insurance"] as const,
  impact: (projectId: string) =>
    [...insuranceKeys.all, "impact", projectId] as const,
  summary: (projectId: string) =>
    [...insuranceKeys.all, "summary", projectId] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useInsuranceImpact(projectId: string | undefined) {
  return useQuery({
    queryKey: insuranceKeys.impact(projectId ?? ""),
    queryFn: () =>
      api
        .get<InsuranceImpactResponse>(`/insurance/projects/${projectId}/impact`)
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useInsuranceSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: insuranceKeys.summary(projectId ?? ""),
    queryFn: () =>
      api
        .get<InsuranceSummaryResponse>(
          `/insurance/projects/${projectId}/summary`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
}
