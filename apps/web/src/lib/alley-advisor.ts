/**
 * Alley Development Advisor — types and React Query hooks.
 * Covers AI strategic guidance endpoints under /alley/advisor.
 */

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface AdvisorQueryResponse {
  response: string;
  project_id: string;
  query: string;
  generated_at: string;
}

export interface FinancingReadinessResponse {
  project_id: string;
  readiness_score: number;
  readiness_label: string;
  strengths: string[];
  gaps: string[];
  recommended_instruments: string[];
  next_steps: string[];
  generated_at: string;
}

export interface MarketPositioningResponse {
  project_id: string;
  positioning_summary: string;
  competitive_advantages: string[];
  market_risks: string[];
  target_investor_profiles: string[];
  generated_at: string;
}

export interface MilestonePlanResponse {
  project_id: string;
  milestones: Array<{
    title: string;
    description: string;
    target_months: number;
    status: string;
    dependencies: string[];
  }>;
  generated_at: string;
}

export interface RegulatoryGuidanceResponse {
  project_id: string;
  jurisdiction: string;
  key_requirements: string[];
  approvals_needed: string[];
  timeline_estimate: string;
  risk_areas: string[];
  generated_at: string;
}

// ── Query key factory ──────────────────────────────────────────────────────

export const alleyAdvisorKeys = {
  financing: (id: string) => ["alley-advisor", "financing", id] as const,
  positioning: (id: string) => ["alley-advisor", "positioning", id] as const,
  milestones: (id: string) => ["alley-advisor", "milestones", id] as const,
  regulatory: (id: string) => ["alley-advisor", "regulatory", id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useAdvisorQuery() {
  return useMutation({
    mutationFn: ({ id, query }: { id: string; query: string }) =>
      api
        .post<AdvisorQueryResponse>(`/alley/advisor/${id}/query`, { query })
        .then((r) => r.data),
  });
}

export function useFinancingReadiness(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyAdvisorKeys.financing(projectId ?? ""),
    queryFn: () =>
      api
        .get<FinancingReadinessResponse>(`/alley/advisor/${projectId}/financing`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useMarketPositioning(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyAdvisorKeys.positioning(projectId ?? ""),
    queryFn: () =>
      api
        .get<MarketPositioningResponse>(
          `/alley/advisor/${projectId}/positioning`
        )
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useMilestonePlan(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyAdvisorKeys.milestones(projectId ?? ""),
    queryFn: () =>
      api
        .get<MilestonePlanResponse>(`/alley/advisor/${projectId}/milestones`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useRegulatoryGuidance(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyAdvisorKeys.regulatory(projectId ?? ""),
    queryFn: () =>
      api
        .get<RegulatoryGuidanceResponse>(
          `/alley/advisor/${projectId}/regulatory`
        )
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function milestoneStatusVariant(
  status: string
): "success" | "warning" | "neutral" | "error" {
  switch (status.toLowerCase()) {
    case "completed":
    case "done":
      return "success";
    case "in_progress":
    case "active":
      return "warning";
    case "blocked":
      return "error";
    default:
      return "neutral";
  }
}
