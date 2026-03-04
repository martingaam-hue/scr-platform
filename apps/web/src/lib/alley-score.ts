/**
 * Alley Signal Score — types and React Query hooks.
 * All scores displayed as 0.0–10.0 (API stores 0–100, divides by 10).
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Portfolio Overview Types ───────────────────────────────────────────────────

export interface PortfolioStats {
  avg_score: number;              // 0.0–10.0
  total_projects: number;
  investment_ready_count: number;
}

export interface ProjectScoreListItem {
  project_id: string;
  project_name: string;
  sector: string | null;
  stage: string | null;
  score: number;                  // 0.0–10.0
  score_label: string;            // Excellent | Strong | Good | Needs Review
  score_label_color: string;      // green | yellow | amber | red
  status: string;                 // Ready | Needs Review
  calculated_at: string;
  trend: "up" | "down" | "stable" | "new";
}

export interface ImprovementFactor {
  dimension: string;
  avg_score: number;
}

export interface ImprovementAction {
  action: string;
  dimension: string;
  priority: string;
  estimated_impact: number;
}

export interface PortfolioScoreResponse {
  stats: PortfolioStats;
  projects: ProjectScoreListItem[];
  improvement_factors: ImprovementFactor[];
  improvement_actions: ImprovementAction[];
}

// ── Project Detail Types ───────────────────────────────────────────────────────

export interface DimensionDetail {
  id: string;
  label: string;
  score: number;                  // 0–100 (raw, used as bar %)
  description?: string;
}

export interface ReadinessIndicator {
  label: string;
  met: boolean;
}

export interface CriterionDetail {
  id: string;
  name: string;
  status: "met" | "partial" | "not_met";
  points_earned: number;
  points_max: number;
  evidence_note?: string;
}

export interface DimensionBreakdown {
  dimension_id: string;
  dimension_name: string;
  score: number;
  criteria: CriterionDetail[];
}

export interface GapAction {
  dimension: string;
  action: string;
  effort: string;
  timeline: string;
  estimated_impact: number;       // 0.0–10.0 scale
}

export interface ScoreHistoryPoint {
  date: string;                   // "YYYY-MM-DD"
  score: number;                  // 0.0–10.0
}

export interface ProjectScoreDetailResponse {
  project_id: string;
  project_name: string;
  score: number;                  // 0.0–10.0
  score_label: string;
  score_label_color: string;
  dimensions: DimensionDetail[];
  readiness_indicators: ReadinessIndicator[];
  criteria_breakdown: DimensionBreakdown[];
  gap_analysis: GapAction[];
  score_history: ScoreHistoryPoint[];
}

// ── Generate / Task Status ─────────────────────────────────────────────────────

export interface GenerateScoreResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress_message?: string;
  result?: Record<string, unknown>;
}

// ── Query key factory ──────────────────────────────────────────────────────────

export const alleyScoreKeys = {
  all: ["alley-score"] as const,
  portfolio: () => [...alleyScoreKeys.all, "portfolio"] as const,
  detail: (id: string) => [...alleyScoreKeys.all, "detail", id] as const,
  task: (id: string) => [...alleyScoreKeys.all, "task", id] as const,
  // Legacy keys kept for existing usage
  list: () => [...alleyScoreKeys.all, "list"] as const,
  gaps: (id: string) => [...alleyScoreKeys.all, "gaps", id] as const,
  history: (id: string) => [...alleyScoreKeys.all, "history", id] as const,
  benchmark: (id: string) => [...alleyScoreKeys.all, "benchmark", id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────────

export function usePortfolioOverview() {
  return useQuery({
    queryKey: alleyScoreKeys.portfolio(),
    queryFn: () =>
      api
        .get<PortfolioScoreResponse>("/alley/signal-score")
        .then((r) => r.data),
  });
}

/** @deprecated Use usePortfolioOverview() instead */
export const useAlleyScores = usePortfolioOverview;

export function useProjectScoreDetail(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyScoreKeys.detail(projectId ?? ""),
    queryFn: () =>
      api
        .get<ProjectScoreDetailResponse>(`/alley/signal-score/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useGenerateScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      api
        .post<GenerateScoreResponse>("/alley/signal-score/generate", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alleyScoreKeys.portfolio() });
    },
  });
}

export function useTaskStatus(taskId: string | undefined) {
  return useQuery({
    queryKey: alleyScoreKeys.task(taskId ?? ""),
    queryFn: () =>
      api
        .get<TaskStatusResponse>(`/alley/signal-score/tasks/${taskId}`)
        .then((r) => r.data),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });
}

// ── Display helpers ────────────────────────────────────────────────────────────

export function scoreLabelColor(color: string): string {
  switch (color) {
    case "green":  return "text-green-600";
    case "yellow": return "text-yellow-600";
    case "amber":  return "text-amber-600";
    default:       return "text-red-500";
  }
}

export function scoreBadgeClass(status: string): string {
  return status === "Ready"
    ? "bg-green-800 text-white border-transparent"
    : "border-orange-400 text-orange-600 bg-transparent";
}

export function dimensionBarColor(score: number): string {
  if (score >= 75) return "bg-green-500";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-400";
}

export function effortColor(effort: string): string {
  switch (effort.toLowerCase()) {
    case "low":    return "text-green-600 bg-green-50";
    case "medium": return "text-amber-700 bg-amber-50";
    default:       return "text-red-600 bg-red-50";
  }
}
