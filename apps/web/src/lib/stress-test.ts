/**
 * Portfolio Stress Test — React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ScenarioResponse {
  key: string;
  name: string;
  description: string;
  params: Record<string, unknown>;
}

export interface ProjectSensitivity {
  project_id: string;
  project_name: string;
  base_value: number;
  stressed_value: number;
  change_pct: number;
}

export interface StressTestResult {
  id: string;
  portfolio_id: string;
  scenario_key: string;
  scenario_name: string;
  parameters: Record<string, unknown>;
  simulations_count: number;
  base_nav: number;
  mean_nav: number;
  median_nav: number;
  p5_nav: number;
  p95_nav: number;
  var_95: number;
  max_loss_pct: number;
  probability_of_loss: number;
  histogram: number[];
  histogram_edges: number[];
  project_sensitivities: ProjectSensitivity[];
  created_at: string;
}

export interface StressTestListResponse {
  items: StressTestResult[];
  total: number;
}

export interface RunStressTestRequest {
  portfolio_id: string;
  scenario_key?: string;
  custom_params?: Record<string, number> | null;
  custom_name?: string | null;
  simulations?: number;
}

// ── Query key factories ─────────────────────────────────────────────────────

export const stressTestKeys = {
  scenarios: ["stress-test", "scenarios"] as const,
  list: (portfolioId: string) => ["stress-test", "list", portfolioId] as const,
  detail: (id: string) => ["stress-test", "detail", id] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useStressTestScenarios() {
  return useQuery({
    queryKey: stressTestKeys.scenarios,
    queryFn: async () => {
      const { data } = await api.get<ScenarioResponse[]>("/stress-test/scenarios");
      return data;
    },
  });
}

export function useStressTests(portfolioId: string) {
  return useQuery({
    queryKey: stressTestKeys.list(portfolioId),
    queryFn: async () => {
      const { data } = await api.get<StressTestListResponse>(
        `/stress-test/portfolio/${portfolioId}`
      );
      return data;
    },
    enabled: !!portfolioId,
  });
}

export function useStressTest(id: string) {
  return useQuery({
    queryKey: stressTestKeys.detail(id),
    queryFn: async () => {
      const { data } = await api.get<StressTestResult>(`/stress-test/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useRunStressTest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RunStressTestRequest) => {
      const { data } = await api.post<StressTestResult>("/stress-test/run", body);
      return data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: stressTestKeys.list(data.portfolio_id) });
    },
  });
}

// ── Formatting helpers ──────────────────────────────────────────────────────

export function formatNavChange(base: number, stressed: number): string {
  if (base <= 0) return "—";
  const pct = ((stressed - base) / base) * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

export function formatCurrency(v: number): string {
  if (v >= 1_000_000) return `€${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `€${(v / 1_000).toFixed(0)}K`;
  return `€${v.toFixed(0)}`;
}
