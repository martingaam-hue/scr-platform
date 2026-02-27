/**
 * Tax Credit Orchestrator module — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type TaxCreditQualification = "potential" | "qualified" | "claimed" | "transferred";

export interface TaxCreditResponse {
  id: string;
  project_id: string;
  org_id: string;
  credit_type: string;
  estimated_value: string;
  claimed_value: string | null;
  currency: string;
  qualification: TaxCreditQualification;
  qualification_details: Record<string, unknown> | null;
  effective_date: string | null;
  expiry_date: string | null;
  project_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaxCreditInventoryResponse {
  portfolio_id: string;
  total_estimated: number;
  total_claimed: number;
  credits_by_type: Record<string, number>;
  credits: TaxCreditResponse[];
  currency: string;
}

export interface IdentifiedCredit {
  credit_type: string;
  program_name: string;
  estimated_value: number;
  qualification: "qualified" | "potential";
  criteria_met: string[];
  criteria_missing: string[];
  notes: string;
  expiry_year: number | null;
}

export interface IdentificationResponse {
  project_id: string;
  project_name: string;
  identified: IdentifiedCredit[];
  total_estimated_value: number;
  currency: string;
}

export interface OptimizationAction {
  credit_id: string;
  project_name: string;
  credit_type: string;
  estimated_value: number;
  action: "claim" | "transfer";
  timing: string;
  reason: string;
}

export interface OptimizationResult {
  total_value: number;
  claim_value: number;
  transfer_value: number;
  actions: OptimizationAction[];
  summary: string;
  currency: string;
}

export interface TransferDocRequest {
  credit_id: string;
  transferee_name: string;
  transferee_ein?: string;
  transfer_price?: number;
}

export interface TransferDocResponse {
  report_id: string;
  status: string;
  message: string;
}

export interface TaxCreditSummaryResponse {
  entity_id: string;
  entity_type: string;
  total_estimated: number;
  total_claimed: number;
  total_transferred: number;
  by_qualification: Record<string, number>;
  by_credit_type: Record<string, number>;
  credits: TaxCreditResponse[];
  currency: string;
}

// ── Query Keys ───────────────────────────────────────────────────────────────

export const taxCreditKeys = {
  all: ["tax-credits"] as const,
  inventory: (portfolioId: string) =>
    [...taxCreditKeys.all, "inventory", portfolioId] as const,
  summary: (entityId: string) =>
    [...taxCreditKeys.all, "summary", entityId] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useTaxCreditInventory(portfolioId: string | undefined) {
  return useQuery({
    queryKey: taxCreditKeys.inventory(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<TaxCreditInventoryResponse>(`/tax-credits/inventory/${portfolioId}`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

export function useTaxCreditSummary(entityId: string | undefined) {
  return useQuery({
    queryKey: taxCreditKeys.summary(entityId ?? ""),
    queryFn: () =>
      api
        .get<TaxCreditSummaryResponse>(`/tax-credits/summary/${entityId}`)
        .then((r) => r.data),
    enabled: !!entityId,
  });
}

export function useIdentifyCredits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post<IdentificationResponse>(`/tax-credits/identify/${projectId}`, {})
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taxCreditKeys.all });
    },
  });
}

export function useRunOptimization() {
  return useMutation({
    mutationFn: (portfolioId: string) =>
      api
        .post<OptimizationResult>("/tax-credits/model", { portfolio_id: portfolioId })
        .then((r) => r.data),
  });
}

export function useGenerateTransferDocs() {
  return useMutation({
    mutationFn: (data: TransferDocRequest) =>
      api
        .post<TransferDocResponse>("/tax-credits/transfer-docs", data)
        .then((r) => r.data),
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function qualificationVariant(
  q: TaxCreditQualification
): "success" | "warning" | "info" | "neutral" {
  if (q === "claimed" || q === "qualified") return "success";
  if (q === "transferred") return "info";
  if (q === "potential") return "warning";
  return "neutral";
}

export const QUALIFICATION_LABELS: Record<TaxCreditQualification, string> = {
  potential: "Potential",
  qualified: "Qualified",
  claimed: "Claimed",
  transferred: "Transferred",
};

export const CREDIT_TYPE_DESCRIPTIONS: Record<string, string> = {
  ITC: "Investment Tax Credit (§48)",
  PTC: "Production Tax Credit (§45)",
  "45Y": "Clean Electricity Production Credit",
  "48E": "Clean Electricity Investment Credit",
  "45L": "Energy Efficient Home Credit",
  "179D": "Commercial Building Energy Efficiency",
  NMTC: "New Markets Tax Credit",
};

export function formatCreditValue(value: string | number, currency: string): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${currency} ${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${currency} ${(n / 1_000).toFixed(0)}K`;
  return `${currency} ${n.toFixed(0)}`;
}

export function actionVariant(
  action: "claim" | "transfer"
): "success" | "info" {
  return action === "transfer" ? "info" : "success";
}
