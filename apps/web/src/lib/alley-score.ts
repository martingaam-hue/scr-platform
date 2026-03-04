/**
 * Alley Signal Score — types and React Query hooks.
 * Covers GET /alley/signal-score and related endpoints.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface AlleyProjectScoreSummary {
  project_id: string;
  project_name: string;
  overall_score: number;
  project_viability_score: number;
  financial_planning_score: number;
  team_strength_score: number;
  risk_assessment_score: number;
  esg_score: number;
  market_opportunity_score: number;
  version: number;
  calculated_at: string;
  trend: "up" | "down" | "stable" | "new";
  score_change: number;
}

export interface AlleyScoreListResponse {
  items: AlleyProjectScoreSummary[];
  total: number;
}

export interface GapActionItem {
  dimension: string;
  criterion: string;
  current_score: number;
  max_score: number;
  action: string;
  estimated_impact: number;
  priority: string;
  effort: string;
  document_types: string[];
}

export interface GapAnalysisResponse {
  project_id: string;
  overall_score: number;
  target_score: number;
  gap_items: GapActionItem[];
  generated_at: string;
}

export interface SimulateResponse {
  current_score: number;
  projected_score: number;
  score_change: number;
  dimension_changes: Record<string, number>;
}

export interface ScoreHistoryPoint {
  version: number;
  overall_score: number;
  calculated_at: string;
  project_viability_score: number;
  financial_planning_score: number;
  team_strength_score: number;
  risk_assessment_score: number;
  esg_score: number;
  market_opportunity_score: number;
}

export interface ScoreHistoryResponse {
  project_id: string;
  history: ScoreHistoryPoint[];
}

export interface BenchmarkResponse {
  project_id: string;
  your_score: number;
  platform_median: number;
  top_quartile: number;
  percentile: number;
  peer_asset_type: string;
  peer_count: number;
}

// ── Query key factory ──────────────────────────────────────────────────────

export const alleyScoreKeys = {
  all: ["alley-score"] as const,
  list: () => [...alleyScoreKeys.all, "list"] as const,
  gaps: (id: string) => [...alleyScoreKeys.all, "gaps", id] as const,
  history: (id: string) => [...alleyScoreKeys.all, "history", id] as const,
  benchmark: (id: string) => [...alleyScoreKeys.all, "benchmark", id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useAlleyScores() {
  return useQuery({
    queryKey: alleyScoreKeys.list(),
    queryFn: () =>
      api
        .get<AlleyScoreListResponse>("/alley/signal-score")
        .then((r) => r.data),
  });
}

export function useAlleyScoreGaps(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyScoreKeys.gaps(projectId ?? ""),
    queryFn: () =>
      api
        .get<GapAnalysisResponse>(`/alley/signal-score/${projectId}/gaps`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useAlleyScoreHistory(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyScoreKeys.history(projectId ?? ""),
    queryFn: () =>
      api
        .get<ScoreHistoryResponse>(`/alley/signal-score/${projectId}/history`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useAlleyBenchmark(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyScoreKeys.benchmark(projectId ?? ""),
    queryFn: () =>
      api
        .get<BenchmarkResponse>(`/alley/signal-score/${projectId}/benchmark`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useSimulateScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: Record<string, unknown>;
    }) =>
      api
        .post<SimulateResponse>(`/alley/signal-score/${id}/simulate`, body)
        .then((r) => r.data),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: alleyScoreKeys.gaps(id) });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function scoreColor(score: number): string {
  if (score >= 75) return "text-green-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

export function scoreBg(score: number): string {
  if (score >= 75) return "bg-green-50 border-green-200";
  if (score >= 50) return "bg-amber-50 border-amber-200";
  return "bg-red-50 border-red-200";
}

export function priorityVariant(
  priority: string
): "error" | "warning" | "neutral" {
  switch (priority.toLowerCase()) {
    case "high":
      return "error";
    case "medium":
      return "warning";
    default:
      return "neutral";
  }
}
