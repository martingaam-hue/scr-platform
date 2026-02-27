/**
 * Value Quantifier types and React Query hooks.
 * All financial KPIs are deterministic — no AI calls.
 */

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface ValueKPI {
  label: string;
  value: string;
  raw_value: number | null;
  unit: string;
  description: string;
  quality: "good" | "warning" | "bad" | "neutral";
}

export interface ValueQuantifierResult {
  project_id: string;
  project_name: string;
  irr: number | null;
  npv: number | null;
  payback_years: number | null;
  dscr: number | null;
  lcoe: number | null;
  carbon_savings_tons: number | null;
  jobs_created: number | null;
  total_investment: number | null;
  kpis: ValueKPI[];
  assumptions: Record<string, number | string>;
}

export interface ValueQuantifierRequest {
  project_id: string;
  capex_usd?: number;
  opex_annual_usd?: number;
  revenue_annual_usd?: number;
  project_lifetime_years?: number;
  discount_rate?: number;
  debt_ratio?: number;
  interest_rate?: number;
  loan_term_years?: number;
  capacity_factor?: number;
  electricity_price_kwh?: number;
  jobs_created?: number;
}

// ── Query key factory ────────────────────────────────────────────────────────

export const valueKeys = {
  all: ["value-quantifier"] as const,
  project: (id: string) => [...valueKeys.all, id] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

/** Fetch value quantification for a project using default assumptions. */
export function useValueQuantifier(projectId?: string) {
  return useQuery({
    queryKey: valueKeys.project(projectId ?? ""),
    queryFn: () =>
      api
        .get<ValueQuantifierResult>(`/value-quantifier/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

/** Calculate value with custom overrides (POST). */
export function useCalculateValue() {
  return useMutation({
    mutationFn: (req: ValueQuantifierRequest) =>
      api
        .post<ValueQuantifierResult>("/value-quantifier/calculate", req)
        .then((r) => r.data),
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function kpiQualityColor(quality: string): string {
  switch (quality) {
    case "good":
      return "text-green-600";
    case "warning":
      return "text-amber-600";
    case "bad":
      return "text-red-600";
    default:
      return "text-neutral-600";
  }
}

export function kpiQualityBg(quality: string): string {
  switch (quality) {
    case "good":
      return "bg-green-50 border-green-200";
    case "warning":
      return "bg-amber-50 border-amber-200";
    case "bad":
      return "bg-red-50 border-red-200";
    default:
      return "bg-neutral-50 border-neutral-200";
  }
}

export function formatCurrency(value: number | null): string {
  if (value === null) return "N/A";
  if (Math.abs(value) >= 1_000_000_000)
    return `$${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000)
    return `$${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}
