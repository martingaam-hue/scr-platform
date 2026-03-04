/**
 * Score Journey — types and React Query hooks.
 * Covers score performance over time under /alley/score-performance.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ScoreJourneyPoint {
  version: number;
  overall_score: number;
  calculated_at: string;
  score_change: number;
  event_label?: string;
}

export interface DimensionTrendPoint {
  version: number;
  calculated_at: string;
  project_viability: number;
  financial_planning: number;
  team_strength: number;
  risk_assessment: number;
  esg: number;
  market_opportunity: number;
}

export interface ScoreInsightItem {
  dimension: string;
  insight: string;
  recommendation: string;
  estimated_impact: number;
}

export interface ProjectScorePerformanceSummary {
  project_id: string;
  project_name: string;
  current_score: number;
  start_score: number;
  total_improvement: number;
  versions: number;
  trend: string;
}

export interface ScorePerformanceListResponse {
  items: ProjectScorePerformanceSummary[];
  total: number;
}

export interface ScoreJourneyResponse {
  project_id: string;
  journey: ScoreJourneyPoint[];
  total_improvement: number;
}

export interface DimensionTrendsResponse {
  project_id: string;
  trends: DimensionTrendPoint[];
}

export interface ScoreInsightsResponse {
  project_id: string;
  insights: ScoreInsightItem[];
  generated_at: string;
}

// ── Query key factory ──────────────────────────────────────────────────────

export const scoreJourneyKeys = {
  all: ["score-journey"] as const,
  list: () => [...scoreJourneyKeys.all, "list"] as const,
  journey: (id: string) => [...scoreJourneyKeys.all, "journey", id] as const,
  dimensions: (id: string) =>
    [...scoreJourneyKeys.all, "dimensions", id] as const,
  insights: (id: string) => [...scoreJourneyKeys.all, "insights", id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useScorePerformanceList() {
  return useQuery({
    queryKey: scoreJourneyKeys.list(),
    queryFn: () =>
      api
        .get<ScorePerformanceListResponse>("/alley/score-performance")
        .then((r) => r.data),
  });
}

export function useScoreJourney(projectId: string | undefined) {
  return useQuery({
    queryKey: scoreJourneyKeys.journey(projectId ?? ""),
    queryFn: () =>
      api
        .get<ScoreJourneyResponse>(`/alley/score-performance/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useDimensionTrends(projectId: string | undefined) {
  return useQuery({
    queryKey: scoreJourneyKeys.dimensions(projectId ?? ""),
    queryFn: () =>
      api
        .get<DimensionTrendsResponse>(
          `/alley/score-performance/${projectId}/dimensions`
        )
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useScoreInsights(projectId: string | undefined) {
  return useQuery({
    queryKey: scoreJourneyKeys.insights(projectId ?? ""),
    queryFn: () =>
      api
        .get<ScoreInsightsResponse>(
          `/alley/score-performance/${projectId}/insights`
        )
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function trendVariant(
  trend: string
): "success" | "error" | "warning" | "neutral" {
  switch (trend.toLowerCase()) {
    case "up":
    case "improving":
      return "success";
    case "down":
    case "declining":
      return "error";
    case "stable":
      return "neutral";
    default:
      return "neutral";
  }
}

export function trendIcon(trend: string): string {
  switch (trend.toLowerCase()) {
    case "up":
    case "improving":
      return "↑";
    case "down":
    case "declining":
      return "↓";
    default:
      return "→";
  }
}

export function impactColor(impact: number): string {
  if (impact >= 10) return "text-green-600 font-semibold";
  if (impact >= 5) return "text-amber-600";
  return "text-neutral-500";
}
