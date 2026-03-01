"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ProjectionRow {
  year: number;
  base_net: number;
  optimistic_net: number;
  pessimistic_net: number;
  base_cumulative: number;
  optimistic_cumulative: number;
  pessimistic_cumulative: number;
  actual_invested: number | null;
  actual_distributed: number | null;
}

export interface PacingData {
  portfolio_id: string;
  assumption_id: string;
  total_commitment: number;
  currency: string;
  trough_year: number;
  trough_value: number;
  projections: ProjectionRow[];
}

export interface CashflowAssumption {
  id: string;
  portfolio_id: string;
  total_commitment: number;
  currency: string;
  deployment_years: number;
  annual_management_fee_pct: number;
  preferred_return_pct: number;
  carry_pct: number;
  created_at: string;
}

export interface CreateAssumptionPayload {
  portfolio_id: string;
  total_commitment: number;
  currency?: string;
  deployment_years?: number;
  annual_management_fee_pct?: number;
  preferred_return_pct?: number;
  carry_pct?: number;
}

export interface UpdateActualsPayload {
  year: number;
  actual_invested: number;
  actual_distributed: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

export function formatMillions(value: number, currency = "EUR"): string {
  const symbol = currency === "USD" ? "$" : currency === "GBP" ? "£" : "€";
  const millions = value / 1_000_000;
  return `${symbol}${millions.toFixed(1)}m`;
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

export function usePacingData(portfolioId: string) {
  return useQuery<PacingData>({
    queryKey: ["pacing", portfolioId],
    queryFn: async () => {
      const { data } = await api.get(`/pacing/portfolios/${portfolioId}`);
      return data;
    },
    enabled: !!portfolioId,
  });
}

export function useListAssumptions(portfolioId: string) {
  return useQuery<CashflowAssumption[]>({
    queryKey: ["pacing-assumptions", portfolioId],
    queryFn: async () => {
      const { data } = await api.get(
        `/pacing/portfolios/${portfolioId}/assumptions`
      );
      return data;
    },
    enabled: !!portfolioId,
  });
}

export function useCreateAssumption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateAssumptionPayload) => {
      const { data } = await api.post(
        `/pacing/portfolios/${payload.portfolio_id}/assumptions`,
        payload
      );
      return data as CashflowAssumption;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["pacing", vars.portfolio_id] });
      qc.invalidateQueries({
        queryKey: ["pacing-assumptions", vars.portfolio_id],
      });
    },
  });
}

export function useUpdateActuals(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateActualsPayload) => {
      const { data } = await api.put(
        `/pacing/portfolios/${portfolioId}/actuals`,
        payload
      );
      return data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["pacing", portfolioId] }),
  });
}
