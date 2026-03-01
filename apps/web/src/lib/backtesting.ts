/**
 * Score Backtesting types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface DealOutcome {
  id: string;
  org_id: string;
  project_id: string | null;
  deal_flow_stage_id: string | null;
  outcome_type: string;
  actual_irr: string | null;
  actual_moic: string | null;
  actual_revenue_eur: string | null;
  signal_score_at_evaluation: string | null;
  signal_score_at_decision: string | null;
  signal_dimensions_at_decision: Record<string, number> | null;
  decision_date: string | null;
  outcome_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BacktestRun {
  id: string;
  org_id: string;
  run_by: string | null;
  methodology: string;
  date_from: string | null;
  date_to: string | null;
  min_score_threshold: string | null;
  accuracy: string | null;
  precision: string | null;
  recall: string | null;
  auc_roc: string | null;
  f1_score: string | null;
  sample_size: number | null;
  results: BacktestResults | null;
  created_at: string;
}

export interface CalibrationBucket {
  score_band: string;
  count: number;
  funded_count: number;
  funded_rate: number | null;
}

export interface CohortQuartile {
  quartile: string;
  count: number;
  funded_count: number;
  funded_rate: number | null;
  avg_irr: number | null;
}

export interface BacktestResults {
  methodology: string;
  threshold: number;
  metrics: {
    accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
    auc_roc: number | null;
    sample_size: number;
    tp: number;
    fp: number;
    tn: number;
    fn: number;
    calibration: CalibrationBucket[];
  };
  cohort_analysis: {
    quartiles: CohortQuartile[];
    total_scored: number;
  };
}

export interface BacktestSummary {
  total_outcomes: number;
  funded_count: number;
  pass_count: number;
  closed_lost_count: number;
  in_progress_count: number;
  funded_rate: number | null;
  avg_score_of_funded: number | null;
  latest_run: BacktestRun | null;
}

export interface RecordOutcomeRequest {
  project_id?: string;
  outcome_type: string;
  actual_irr?: number;
  actual_moic?: number;
  actual_revenue_eur?: number;
  signal_score_at_evaluation?: number;
  signal_score_at_decision?: number;
  signal_dimensions_at_decision?: Record<string, number>;
  decision_date?: string;
  outcome_date?: string;
  notes?: string;
}

export interface BacktestRunRequest {
  methodology?: string;
  date_from?: string;
  date_to?: string;
  min_score_threshold?: number;
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const backtestingKeys = {
  all: ["backtesting"] as const,
  outcomes: () => [...backtestingKeys.all, "outcomes"] as const,
  runs: () => [...backtestingKeys.all, "runs"] as const,
  run: (id: string) => [...backtestingKeys.all, "runs", id] as const,
  summary: () => [...backtestingKeys.all, "summary"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useDealOutcomes() {
  return useQuery<DealOutcome[]>({
    queryKey: backtestingKeys.outcomes(),
    queryFn: async () => {
      const { data } = await api.get<DealOutcome[]>("/backtesting/outcomes");
      return data;
    },
  });
}

export function useBacktestRuns() {
  return useQuery<BacktestRun[]>({
    queryKey: backtestingKeys.runs(),
    queryFn: async () => {
      const { data } = await api.get<BacktestRun[]>("/backtesting/runs");
      return data;
    },
  });
}

export function useBacktestRun(id: string) {
  return useQuery<BacktestRun>({
    queryKey: backtestingKeys.run(id),
    queryFn: async () => {
      const { data } = await api.get<BacktestRun>(`/backtesting/runs/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useBacktestSummary() {
  return useQuery<BacktestSummary>({
    queryKey: backtestingKeys.summary(),
    queryFn: async () => {
      const { data } = await api.get<BacktestSummary>("/backtesting/summary");
      return data;
    },
  });
}

export function useRecordOutcome() {
  const qc = useQueryClient();
  return useMutation<DealOutcome, Error, RecordOutcomeRequest>({
    mutationFn: async (body) => {
      const { data } = await api.post<DealOutcome>("/backtesting/outcomes", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: backtestingKeys.outcomes() });
      qc.invalidateQueries({ queryKey: backtestingKeys.summary() });
    },
  });
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation<BacktestRun, Error, BacktestRunRequest>({
    mutationFn: async (body) => {
      const { data } = await api.post<BacktestRun>("/backtesting/runs", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: backtestingKeys.runs() });
      qc.invalidateQueries({ queryKey: backtestingKeys.summary() });
    },
  });
}
