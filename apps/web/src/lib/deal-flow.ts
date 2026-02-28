/**
 * Deal Flow Analytics — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface TransitionCreate {
  project_id: string;
  to_stage: string;
  from_stage?: string | null;
  reason?: string | null;
  investor_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface TransitionResponse {
  id: string;
  org_id: string;
  project_id: string;
  investor_id: string | null;
  from_stage: string | null;
  to_stage: string;
  reason: string | null;
  transitioned_by: string | null;
  created_at: string;
}

export interface StageCount {
  stage: string;
  count: number;
  deal_value: number | null;
}

export interface ConversionStep {
  from_stage: string;
  to_stage: string;
  from_count: number;
  to_count: number;
  conversion_rate: number;
}

export interface AvgTimeInStage {
  stage: string;
  avg_days: number | null;
}

export interface FunnelResponse {
  period_days: number;
  stage_counts: StageCount[];
  conversions: ConversionStep[];
  avg_time_in_stage: AvgTimeInStage[];
  drop_off_reasons: Record<string, number>;
  total_entered: number;
  total_closed: number;
  overall_conversion_rate: number;
  generated_at: string;
}

export interface PipelineValueResponse {
  by_stage: Record<string, number>;
  total: number;
}

export interface VelocityResponse {
  avg_days_to_close: number | null;
  by_stage: AvgTimeInStage[];
  trend: Array<{ month: string; avg_days: number }>;
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const dealFlowKeys = {
  all: ["deal-flow"] as const,
  funnel: (periodDays: number) =>
    [...dealFlowKeys.all, "funnel", periodDays] as const,
  pipelineValue: () => [...dealFlowKeys.all, "pipeline-value"] as const,
  velocity: () => [...dealFlowKeys.all, "velocity"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useFunnelData(periodDays: number = 90) {
  return useQuery({
    queryKey: dealFlowKeys.funnel(periodDays),
    queryFn: () =>
      api
        .get<FunnelResponse>(`/deal-flow/funnel?period_days=${periodDays}`)
        .then((r) => r.data),
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

export function usePipelineValue() {
  return useQuery({
    queryKey: dealFlowKeys.pipelineValue(),
    queryFn: () =>
      api
        .get<PipelineValueResponse>("/deal-flow/pipeline-value")
        .then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useVelocity() {
  return useQuery({
    queryKey: dealFlowKeys.velocity(),
    queryFn: () =>
      api
        .get<VelocityResponse>("/deal-flow/velocity")
        .then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useRecordTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TransitionCreate) =>
      api
        .post<TransitionResponse>("/deal-flow/transition", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dealFlowKeys.all });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export const STAGE_LABELS: Record<string, string> = {
  discovery: "Discovery",
  screening: "Screening",
  preliminary_dd: "Prelim. DD",
  full_dd: "Full DD",
  negotiation: "Negotiation",
  term_sheet: "Term Sheet",
  closing: "Closing",
  closed: "Closed",
  passed: "Passed",
};

export function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] ?? stage;
}

export function formatCurrency(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}
