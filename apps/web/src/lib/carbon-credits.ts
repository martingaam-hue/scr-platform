/**
 * Carbon Credits — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface CarbonEstimateResult {
  annual_tons_co2e: number;
  methodology: string;
  methodology_label: string;
  assumptions: Record<string, unknown>;
  confidence: "low" | "medium" | "high";
  notes: string;
}

export interface CarbonCreditResponse {
  id: string;
  project_id: string;
  registry: string;
  methodology: string;
  vintage_year: number;
  quantity_tons: number;
  price_per_ton: number | null;
  currency: string;
  serial_number: string | null;
  verification_status: string;
  verification_body: string | null;
  issuance_date: string | null;
  retirement_date: string | null;
  estimated_annual_tons: number | null;
  suggested_methodology: string | null;
  revenue_projection: {
    annual_tons: number;
    scenarios: Record<
      string,
      { price_per_ton_usd: number; annual_revenue_usd: number; "10yr_revenue_usd": number }
    >;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface PricingTrendPoint {
  date: string;
  vcs_price: number;
  gold_standard_price: number;
  eu_ets_price: number;
}

export interface MethodologyItem {
  id: string;
  name: string;
  registry: string;
  applicable_project_types: string[];
  description: string;
  verification_complexity: "low" | "medium" | "high";
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const carbonKeys = {
  all: ["carbon"] as const,
  project: (projectId: string) => [...carbonKeys.all, projectId] as const,
  trends: () => [...carbonKeys.all, "trends"] as const,
  methodologies: () => [...carbonKeys.all, "methodologies"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useCarbonCredit(projectId: string | undefined) {
  return useQuery({
    queryKey: carbonKeys.project(projectId ?? ""),
    queryFn: () =>
      api
        .get<CarbonCreditResponse>(`/carbon/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useEstimateCarbonCredits(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api
        .post<{ estimate: CarbonEstimateResult; credit_record: CarbonCreditResponse }>(
          `/carbon/estimate/${projectId}`
        )
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: carbonKeys.project(projectId ?? "") });
    },
  });
}

export function useUpdateCarbonCredit(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<CarbonCreditResponse>) =>
      api
        .put<CarbonCreditResponse>(`/carbon/${projectId}`, body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: carbonKeys.project(projectId ?? "") });
    },
  });
}

export function useSubmitVerification(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post(`/carbon/${projectId}/submit-verification`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: carbonKeys.project(projectId ?? "") });
    },
  });
}

export function usePricingTrends() {
  return useQuery({
    queryKey: carbonKeys.trends(),
    queryFn: () =>
      api.get<PricingTrendPoint[]>("/carbon/pricing-trends").then((r) => r.data),
  });
}

export function useMethodologies() {
  return useQuery({
    queryKey: carbonKeys.methodologies(),
    queryFn: () =>
      api.get<MethodologyItem[]>("/carbon/methodologies").then((r) => r.data),
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

export const VERIFICATION_STATUS_LABELS: Record<string, string> = {
  estimated: "Estimated",
  submitted: "Submitted for Verification",
  verified: "Verified",
  issued: "Issued",
  retired: "Retired",
};

export function verificationStatusBadge(
  status: string
): "neutral" | "warning" | "success" | "error" {
  switch (status) {
    case "verified":
    case "issued":
      return "success";
    case "submitted":
      return "warning";
    case "retired":
      return "error";
    default:
      return "neutral";
  }
}

export function confidenceColor(confidence: string): string {
  switch (confidence) {
    case "high": return "text-green-600";
    case "medium": return "text-amber-600";
    default: return "text-red-600";
  }
}

export const SCENARIO_LABELS: Record<string, string> = {
  conservative: "Conservative",
  base_case: "Base Case",
  optimistic: "Optimistic",
  eu_ets: "EU ETS Reference",
};
