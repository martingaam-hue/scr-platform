/**
 * Valuation Analysis module — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export type ValuationMethod = "dcf" | "comparables" | "replacement_cost" | "blended";
export type ValuationStatus = "draft" | "reviewed" | "approved" | "superseded";
export type TerminalMethod = "gordon" | "exit_multiple";

export interface YearlyPV {
  year: number;
  cash_flow: number;
  pv: number;
}

export interface DCFParams {
  cash_flows: number[];
  discount_rate: number;
  terminal_growth_rate?: number;
  terminal_method?: TerminalMethod;
  exit_multiple?: number | null;
  net_debt?: number;
}

export interface ComparableCompany {
  name: string;
  ev_ebitda?: number | null;
  ev_mw?: number | null;
  ev_revenue?: number | null;
  transaction_date?: string | null;
  geography?: string | null;
  notes?: string | null;
}

export interface ComparableParams {
  comparables: ComparableCompany[];
  subject_ebitda?: number | null;
  subject_capacity_mw?: number | null;
  subject_revenue?: number | null;
  net_debt?: number;
  multiple_types?: Array<"ev_ebitda" | "ev_mw" | "ev_revenue">;
}

export interface ReplacementCostParams {
  component_costs: Record<string, number>;
  land_value?: number;
  development_costs?: number;
  depreciation_pct?: number;
  net_debt?: number;
}

export interface BlendedComponent {
  method: string;
  enterprise_value: number;
  weight: number;
}

export interface BlendedParams {
  components: BlendedComponent[];
  net_debt?: number;
}

export interface ValuationCreateRequest {
  project_id: string;
  method: ValuationMethod;
  currency?: string;
  dcf_params?: DCFParams | null;
  comparable_params?: ComparableParams | null;
  replacement_params?: ReplacementCostParams | null;
  blended_params?: BlendedParams | null;
}

export interface ValuationUpdateRequest {
  dcf_params?: DCFParams | null;
  comparable_params?: ComparableParams | null;
  replacement_params?: ReplacementCostParams | null;
  blended_params?: BlendedParams | null;
}

export interface ValuationResponse {
  id: string;
  project_id: string;
  org_id: string;
  method: ValuationMethod;
  enterprise_value: string;
  equity_value: string;
  currency: string;
  status: ValuationStatus;
  version: number;
  valued_at: string;
  prepared_by: string;
  approved_by: string | null;
  assumptions: Record<string, unknown>;
  model_inputs: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ValuationListResponse {
  items: ValuationResponse[];
  total: number;
}

export interface ValuationReportResponse {
  report_id: string;
  status: string;
  message: string;
}

export interface AssumptionSuggestion {
  discount_rate: number;
  terminal_growth_rate: number;
  terminal_method: string;
  projection_years: number;
  comparable_multiples: Record<string, number>;
  reasoning: Record<string, string>;
}

export interface SuggestAssumptionsRequest {
  project_type: string;
  geography: string;
  stage: string;
}

export interface SensitivityMatrix {
  row_variable: string;
  col_variable: string;
  row_values: number[];
  col_values: number[];
  matrix: Array<Array<number | null>>;
  base_value: number;
  min_value: number;
  max_value: number;
}

export interface SensitivityRequest {
  base_params: DCFParams;
  row_variable: "discount_rate" | "terminal_growth_rate";
  row_values: number[];
  col_variable: "discount_rate" | "terminal_growth_rate";
  col_values: number[];
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const valuationKeys = {
  all: ["valuations"] as const,
  list: (projectId?: string) =>
    [...valuationKeys.all, "list", projectId ?? "all"] as const,
  detail: (id: string) => [...valuationKeys.all, "detail", id] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useValuations(projectId?: string) {
  const params = projectId ? `?project_id=${projectId}` : "";
  return useQuery({
    queryKey: valuationKeys.list(projectId),
    queryFn: () =>
      api
        .get<ValuationListResponse>(`/valuations${params}`)
        .then((r) => r.data),
  });
}

export function useValuation(id: string | undefined) {
  return useQuery({
    queryKey: valuationKeys.detail(id ?? ""),
    queryFn: () =>
      api.get<ValuationResponse>(`/valuations/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateValuation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ValuationCreateRequest) =>
      api
        .post<ValuationResponse>("/valuations", data)
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: valuationKeys.list(vars.project_id) });
      qc.invalidateQueries({ queryKey: valuationKeys.list() });
    },
  });
}

export function useUpdateValuation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      valuationId,
      ...data
    }: ValuationUpdateRequest & { valuationId: string }) =>
      api
        .put<ValuationResponse>(`/valuations/${valuationId}`, data)
        .then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: valuationKeys.detail(data.id) });
      qc.invalidateQueries({ queryKey: valuationKeys.list(data.project_id) });
    },
  });
}

export function useApproveValuation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valuationId: string) =>
      api
        .put<ValuationResponse>(`/valuations/${valuationId}/approve`, {})
        .then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: valuationKeys.detail(data.id) });
      qc.invalidateQueries({ queryKey: valuationKeys.list(data.project_id) });
    },
  });
}

export function useRunSensitivity() {
  return useMutation({
    mutationFn: ({
      valuationId,
      ...body
    }: SensitivityRequest & { valuationId: string }) =>
      api
        .post<SensitivityMatrix>(`/valuations/${valuationId}/sensitivity`, body)
        .then((r) => r.data),
  });
}

export function useTriggerReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valuationId: string) =>
      api
        .post<ValuationReportResponse>(`/valuations/${valuationId}/report`, {})
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: valuationKeys.all });
    },
  });
}

export function useSuggestAssumptions() {
  return useMutation({
    mutationFn: (body: SuggestAssumptionsRequest) =>
      api
        .post<AssumptionSuggestion>("/valuations/suggest-assumptions", body)
        .then((r) => r.data),
  });
}

export function useCompareValuations() {
  return useMutation({
    mutationFn: (ids: string[]) =>
      api
        .post<ValuationResponse[]>("/valuations/compare", ids)
        .then((r) => r.data),
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

export function statusVariant(
  status: ValuationStatus
): "success" | "info" | "warning" | "neutral" {
  if (status === "approved") return "success";
  if (status === "reviewed") return "info";
  if (status === "superseded") return "neutral";
  return "warning"; // draft
}

export function methodLabel(method: ValuationMethod): string {
  const labels: Record<ValuationMethod, string> = {
    dcf: "DCF",
    comparables: "Comparables",
    replacement_cost: "Replacement Cost",
    blended: "Blended",
  };
  return labels[method] ?? method;
}

export function formatEV(value: string, currency: string): string {
  const n = parseFloat(value);
  if (isNaN(n)) return `${currency} —`;
  if (Math.abs(n) >= 1_000_000)
    return `${currency} ${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${currency} ${(n / 1_000).toFixed(0)}K`;
  return `${currency} ${n.toFixed(0)}`;
}

export function sensitivityCellColor(
  value: number | null,
  base: number
): string {
  if (value === null) return "bg-gray-100 text-gray-400";
  const delta = (value - base) / base;
  if (delta >= 0.15) return "bg-green-100 text-green-800 font-medium";
  if (delta >= 0.05) return "bg-green-50 text-green-700";
  if (delta <= -0.15) return "bg-red-100 text-red-800 font-medium";
  if (delta <= -0.05) return "bg-red-50 text-red-700";
  return "bg-white text-gray-700";
}
