"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface GamificationBadge {
  id: string;
  slug: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  points: number;
  rarity: string;
  earned_at: string | null;
  is_earned: boolean;
}

export interface Quest {
  id: string;
  title: string;
  description: string;
  action_type: string;
  target_dimension: string;
  estimated_score_impact: number;
  status: string;
  reward_badge_name: string | null;
}

export interface GamificationProgress {
  score: number | null;
  badge_count: number;
  total_points: number;
  active_quests: number;
  next_milestone: number | null;
  progress_to_next: number;
  level: string;
  rank: number | null;
}

export interface LeaderboardEntry {
  rank: number;
  project_name: string;
  org_name: string;
  score: number;
  badge_count: number;
  total_points: number;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useMyBadges() {
  return useQuery<GamificationBadge[]>({
    queryKey: ["badges", "my"],
    queryFn: () => api.get("/gamification/badges/my").then((r) => r.data),
  });
}

export function useProjectBadges(projectId: string) {
  return useQuery<GamificationBadge[]>({
    queryKey: ["badges", "project", projectId],
    queryFn: () =>
      api.get(`/gamification/badges/project/${projectId}`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useProjectQuests(projectId: string) {
  return useQuery<Quest[]>({
    queryKey: ["quests", projectId],
    queryFn: () =>
      api.get(`/gamification/quests/${projectId}`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useGamificationProgress(projectId?: string) {
  return useQuery<GamificationProgress>({
    queryKey: ["gamification-progress", projectId ?? "global"],
    queryFn: () => {
      const url = projectId
        ? `/gamification/progress/${projectId}`
        : "/gamification/progress";
      return api.get(url).then((r) => r.data);
    },
  });
}

export function useLeaderboard() {
  return useQuery<LeaderboardEntry[]>({
    queryKey: ["gamification-leaderboard"],
    queryFn: () => api.get("/gamification/leaderboard").then((r) => r.data),
  });
}

export function useCompleteQuest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (questId: string) =>
      api.post(`/gamification/quests/${questId}/complete`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quests"] });
      qc.invalidateQueries({ queryKey: ["gamification-progress"] });
      qc.invalidateQueries({ queryKey: ["badges"] });
    },
  });
}

export function useEvaluateBadges() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post(`/gamification/badges/evaluate/${projectId}`)
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      qc.invalidateQueries({ queryKey: ["badges", "project", projectId] });
      qc.invalidateQueries({ queryKey: ["gamification-progress", projectId] });
    },
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const RARITY_STYLE: Record<string, string> = {
  common: "border-gray-200 bg-gray-50",
  uncommon: "border-green-200 bg-green-50",
  rare: "border-blue-200 bg-blue-50",
  epic: "border-purple-200 bg-purple-50",
  legendary: "border-amber-200 bg-amber-50",
};

export const RARITY_TEXT: Record<string, string> = {
  common: "text-gray-500",
  uncommon: "text-green-600",
  rare: "text-blue-600",
  epic: "text-purple-600",
  legendary: "text-amber-600",
};
