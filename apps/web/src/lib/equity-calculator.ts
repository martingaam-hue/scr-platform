/**
 * Equity Calculator types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface CapTableEntry {
  name: string;
  shares: number;
  percentage: number;
  investment: number | null;
}

export interface WaterfallScenario {
  multiple: number;
  exit_value: number;
  investor_proceeds: number;
  founder_proceeds: number;
  investor_moic: number;
  investor_irr_estimate: number | null;
}

export interface EquityScenario {
  id: string;
  org_id: string;
  project_id: string | null;
  scenario_name: string;
  description: string | null;
  pre_money_valuation: number;
  investment_amount: number;
  security_type: string;
  equity_percentage: number;
  post_money_valuation: number;
  shares_outstanding_before: number;
  new_shares_issued: number;
  price_per_share: number;
  liquidation_preference: number | null;
  participation_cap: number | null;
  anti_dilution_type: string | null;
  cap_table: CapTableEntry[];
  waterfall: WaterfallScenario[];
  dilution_impact: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateScenarioRequest {
  scenario_name: string;
  project_id?: string;
  description?: string;
  pre_money_valuation: number;
  investment_amount: number;
  security_type?: string;
  shares_outstanding_before?: number;
  liquidation_preference?: number;
  participation_cap?: number;
  anti_dilution_type?: string;
  vesting_cliff_months?: number;
  vesting_total_months?: number;
}

export interface CompareRequest {
  scenario_ids: string[];
}

export interface CompareResponse {
  scenarios: Array<Record<string, unknown>>;
  dimensions: string[];
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const equityKeys = {
  all: ["equity-calculator"] as const,
  scenarios: (projectId?: string) =>
    [...equityKeys.all, "scenarios", projectId ?? "all"] as const,
  one: (id: string) => [...equityKeys.all, id] as const,
  compare: (ids: string[]) =>
    [...equityKeys.all, "compare", ...ids.sort()] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useEquityScenarios(projectId?: string) {
  return useQuery({
    queryKey: equityKeys.scenarios(projectId),
    queryFn: () => {
      const params = projectId ? `?project_id=${projectId}` : "";
      return api
        .get<EquityScenario[]>(`/equity-calculator/scenarios${params}`)
        .then((r) => r.data);
    },
  });
}

export function useEquityScenario(id?: string) {
  return useQuery({
    queryKey: equityKeys.one(id ?? ""),
    queryFn: () =>
      api
        .get<EquityScenario>(`/equity-calculator/scenarios/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateScenarioRequest) =>
      api
        .post<EquityScenario>("/equity-calculator/scenarios", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: equityKeys.all });
    },
  });
}

export function useCompareScenarios() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CompareRequest) =>
      api
        .post<CompareResponse>("/equity-calculator/compare", body)
        .then((r) => r.data),
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function securityTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    common_equity: "Common Equity",
    preferred_equity: "Preferred Equity",
    convertible_note: "Convertible Note",
    safe: "SAFE",
    revenue_share: "Revenue Share",
  };
  return labels[type] ?? type;
}

export function antiDilutionLabel(type: string | null): string {
  if (!type) return "None";
  const labels: Record<string, string> = {
    none: "None",
    broad_based: "Broad-Based Weighted Average",
    narrow_based: "Narrow-Based Weighted Average",
    full_ratchet: "Full Ratchet",
  };
  return labels[type] ?? type;
}

export function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

export function moicColor(moic: number): string {
  if (moic >= 5) return "text-green-600";
  if (moic >= 2) return "text-blue-600";
  if (moic >= 1) return "text-amber-600";
  return "text-red-600";
}
