/**
 * Alley Signal Score — types and React Query hooks.
 * All scores on 0–100 scale (API stores and returns 0–100).
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Portfolio Overview Types ───────────────────────────────────────────────────

export interface PortfolioStats {
  avg_score: number;              // 0–100
  total_projects: number;
  investment_ready_count: number;
}

export interface ProjectScoreListItem {
  project_id: string;
  project_name: string;
  sector: string | null;
  stage: string | null;
  score: number;                  // 0–100
  score_label: string;            // Excellent | Strong | Good | Fair | Needs Review
  score_label_color: string;      // green | teal | amber | red
  status: string;                 // Investment Ready | Needs Review | In Progress
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
  estimated_impact: number;       // 0–100 scale
}

export interface ScoreHistoryPoint {
  date: string;                   // "YYYY-MM-DD"
  score: number;                  // 0–100
}

export interface ProjectScoreDetailResponse {
  project_id: string;
  project_name: string;
  score: number;                  // 0–100
  score_label: string;
  score_label_color: string;
  calculated_at?: string;
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

// ── Display helpers (0–100 scale) ─────────────────────────────────────────────

/** Returns a human-readable label for a 0–100 score */
export function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 80) return "Strong";
  if (score >= 70) return "Good";
  if (score >= 60) return "Fair";
  return "Needs Review";
}

/** Returns Tailwind text color class for a 0–100 score */
export function scoreLabelColor(score: number): string {
  if (score >= 90) return "text-green-700";
  if (score >= 80) return "text-green-600";
  if (score >= 70) return "text-teal-600";
  if (score >= 60) return "text-orange-500";
  return "text-red-500";
}

/** Returns Tailwind badge classes for a 0–100 score */
export function scoreBadgeClass(score: number): string {
  if (score >= 90) return "bg-green-900 text-white border-transparent";
  if (score >= 80) return "bg-green-700 text-white border-transparent";
  if (score >= 70) return "bg-teal-700 text-white border-transparent";
  if (score >= 60) return "bg-orange-500 text-white border-transparent";
  return "bg-red-600 text-white border-transparent";
}

/** Returns investment readiness status label for a 0–100 score */
export function readinessStatus(score: number): string {
  if (score >= 80) return "Investment Ready";
  if (score >= 60) return "Needs Review";
  return "In Progress";
}

/** Returns Tailwind bar color for a 0–100 score */
export function dimensionBarColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 70) return "bg-teal-500";
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
