/**
 * Insurance module — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

export interface QuoteCreate {
  project_id?: string;
  provider_name: string;
  coverage_type: string;
  coverage_amount: number;
  quoted_premium: number;
  currency?: string;
  valid_until?: string;
  terms?: Record<string, unknown>;
  side?: "ally" | "investor";
}

export interface QuoteResponse {
  id: string;
  org_id: string;
  project_id: string | null;
  provider_name: string;
  coverage_type: string;
  coverage_amount: string;
  quoted_premium: string;
  currency: string;
  valid_until: string | null;
  terms: Record<string, unknown> | null;
  side: string;
  created_at: string;
}

export interface PolicyCreate {
  quote_id: string;
  project_id?: string;
  portfolio_id?: string;
  policy_number: string;
  provider_name: string;
  coverage_type: string;
  coverage_amount: number;
  premium_amount: number;
  premium_frequency?: "monthly" | "quarterly" | "annual";
  start_date: string;
  end_date: string;
  side?: "ally" | "investor";
  terms?: Record<string, unknown>;
}

export interface PolicyResponse {
  id: string;
  org_id: string;
  quote_id: string;
  project_id: string | null;
  portfolio_id: string | null;
  policy_number: string;
  provider_name: string;
  coverage_type: string;
  coverage_amount: string;
  premium_amount: string;
  premium_frequency: string;
  start_date: string;
  end_date: string;
  status: string;
  risk_score_impact: string;
  side: string;
  created_at: string;
}

// ── Coverage helpers ──────────────────────────────────────────────────────────

export const COVERAGE_LABELS: Record<string, string> = {
  construction_all_risk: "Construction All-Risk (CAR)",
  operational_all_risk: "Operational All-Risk (OAR)",
  third_party_liability: "Third-Party Liability",
  business_interruption: "Business Interruption",
  political_risk: "Political Risk",
  environmental_liability: "Environmental Liability",
  directors_officers: "Directors & Officers (D&O)",
  cyber_liability: "Cyber Liability",
  machinery_breakdown: "Machinery Breakdown",
  weather_parametric: "Weather / Parametric",
};

export const ADEQUACY_BADGE: Record<string, string> = {
  excellent: "success",
  good: "info",
  partial: "warning",
  insufficient: "error",
};

export const PRIORITY_BADGE: Record<string, string> = {
  critical: "error",
  high: "warning",
  medium: "info",
  low: "neutral",
};

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

// ── Quote CRUD hooks ──────────────────────────────────────────────────────────

export function useInsuranceQuotes(projectId?: string) {
  return useQuery<QuoteResponse[]>({
    queryKey: ["insurance", "quotes", projectId ?? "all"],
    queryFn: () =>
      api
        .get<QuoteResponse[]>("/insurance/quotes", {
          params: projectId ? { project_id: projectId } : {},
        })
        .then((r) => r.data),
    staleTime: 2 * 60 * 1000,
  });
}

export function useCreateQuote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: QuoteCreate) =>
      api.post<QuoteResponse>("/insurance/quotes", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insurance", "quotes"] }),
  });
}

export function useDeleteQuote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (quoteId: string) => api.delete(`/insurance/quotes/${quoteId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insurance", "quotes"] }),
  });
}

// ── Policy CRUD hooks ─────────────────────────────────────────────────────────

export function useInsurancePolicies(projectId?: string) {
  return useQuery<PolicyResponse[]>({
    queryKey: ["insurance", "policies", projectId ?? "all"],
    queryFn: () =>
      api
        .get<PolicyResponse[]>("/insurance/policies", {
          params: projectId ? { project_id: projectId } : {},
        })
        .then((r) => r.data),
    staleTime: 2 * 60 * 1000,
  });
}

export function useCreatePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PolicyCreate) =>
      api.post<PolicyResponse>("/insurance/policies", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insurance", "policies"] }),
  });
}

export function useDeletePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (policyId: string) => api.delete(`/insurance/policies/${policyId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insurance", "policies"] }),
  });
}
