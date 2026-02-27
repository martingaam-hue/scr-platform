/**
 * Signal Score types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { projectKeys } from "@/lib/projects";

// ── Types ──────────────────────────────────────────────────────────────────

export interface CriterionScore {
  id: string;
  name: string;
  max_points: number;
  score: number;
  has_document: boolean;
  ai_assessment: {
    score: number;
    reasoning: string;
    strengths: string[];
    weaknesses: string[];
    recommendation: string;
  } | null;
}

export interface DimensionScore {
  id: string;
  name: string;
  weight: number;
  score: number;
  completeness_score: number;
  quality_score: number;
  criteria: CriterionScore[];
}

export interface SignalScoreDetail {
  id: string;
  project_id: string;
  overall_score: number;
  dimensions: DimensionScore[];
  model_used: string;
  version: number;
  calculated_at: string;
}

export interface GapItem {
  dimension_id: string;
  dimension_name: string;
  criterion_id: string;
  criterion_name: string;
  current_score: number;
  max_points: number;
  priority: "high" | "medium" | "low";
  recommendation: string;
  relevant_doc_types: string[];
}

export interface GapsResponse {
  items: GapItem[];
  total: number;
}

export interface ScoreHistoryItem {
  version: number;
  overall_score: number;
  technical_score: number;
  financial_score: number;
  esg_score: number;
  regulatory_score: number;
  team_score: number;
  calculated_at: string;
}

export interface ScoreHistoryResponse {
  items: ScoreHistoryItem[];
}

export interface CalculateAcceptedResponse {
  task_log_id: string;
  status: string;
  message: string;
}

export interface TaskStatusResponse {
  id: string;
  status: string;
  error_message: string | null;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const signalScoreKeys = {
  all: ["signal-score"] as const,
  latest: (projectId: string) =>
    [...signalScoreKeys.all, "latest", projectId] as const,
  history: (projectId: string) =>
    [...signalScoreKeys.all, "history", projectId] as const,
  details: (projectId: string) =>
    [...signalScoreKeys.all, "details", projectId] as const,
  gaps: (projectId: string) =>
    [...signalScoreKeys.all, "gaps", projectId] as const,
  task: (taskId: string) =>
    [...signalScoreKeys.all, "task", taskId] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useSignalScore(projectId: string | undefined) {
  return useQuery({
    queryKey: signalScoreKeys.latest(projectId ?? ""),
    queryFn: () =>
      api
        .get<SignalScoreDetail>(`/signal-score/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
    retry: false,
  });
}

export function useSignalScoreDetails(projectId: string | undefined) {
  return useQuery({
    queryKey: signalScoreKeys.details(projectId ?? ""),
    queryFn: () =>
      api
        .get<SignalScoreDetail>(`/signal-score/${projectId}/details`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useSignalScoreHistory(projectId: string | undefined) {
  return useQuery({
    queryKey: signalScoreKeys.history(projectId ?? ""),
    queryFn: () =>
      api
        .get<ScoreHistoryResponse>(`/signal-score/${projectId}/history`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useSignalScoreGaps(projectId: string | undefined) {
  return useQuery({
    queryKey: signalScoreKeys.gaps(projectId ?? ""),
    queryFn: () =>
      api
        .get<GapsResponse>(`/signal-score/${projectId}/gaps`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCalculateScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post<CalculateAcceptedResponse>(
          `/signal-score/calculate/${projectId}`
        )
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      qc.invalidateQueries({ queryKey: signalScoreKeys.all });
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
    },
  });
}

export function useRecalculateScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post<CalculateAcceptedResponse>(
          `/signal-score/${projectId}/recalculate`
        )
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      qc.invalidateQueries({ queryKey: signalScoreKeys.all });
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
    },
  });
}

export function useTaskStatus(taskId: string | undefined) {
  return useQuery({
    queryKey: signalScoreKeys.task(taskId ?? ""),
    queryFn: () =>
      api
        .get<TaskStatusResponse>(`/signal-score/task/${taskId}`)
        .then((r) => r.data),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "completed" || data.status === "failed")) {
        return false;
      }
      return 3000;
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export function scoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-50";
  if (score >= 60) return "bg-amber-50";
  return "bg-red-50";
}

export function priorityColor(
  priority: string
): "error" | "warning" | "neutral" {
  switch (priority) {
    case "high":
      return "error";
    case "medium":
      return "warning";
    default:
      return "neutral";
  }
}

const DIMENSION_LABELS: Record<string, string> = {
  technical: "Technical",
  financial: "Financial",
  esg: "ESG",
  regulatory: "Regulatory",
  team: "Team",
};

export function dimensionLabel(id: string): string {
  return DIMENSION_LABELS[id] ?? id;
}
