/**
 * Investor Readiness Certification — types, React Query hooks, and helpers.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface CertificationResponse {
  id: string;
  project_id: string;
  status: string; // "not_certified" | "certified" | "expired" | "suspended"
  tier: string | null; // "bronze" | "silver" | "gold" | "platinum"
  certification_score: number | null;
  dimension_scores: Record<string, number> | null;
  certified_at: string | null;
  last_verified_at: string | null;
  certification_count: number;
  consecutive_months_certified: number;
  created_at: string;
}

export interface CertificationBadge {
  certified: boolean;
  tier: string | null;
  score: number | null;
  certified_since: string | null;
  consecutive_months: number;
}

export interface CertificationGap {
  type: string;
  dimension?: string;
  current: number | string;
  needed: number | string;
}

export interface CertificationRequirements {
  eligible: boolean;
  current_score: number | null;
  gaps: CertificationGap[];
}

// ── Query Keys ───────────────────────────────────────────────────────────────

export const certKeys = {
  all: ["certification"] as const,
  status: (projectId: string) => [...certKeys.all, "status", projectId] as const,
  badge: (projectId: string) => [...certKeys.all, "badge", projectId] as const,
  requirements: (projectId: string) =>
    [...certKeys.all, "requirements", projectId] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useCertification(projectId: string) {
  return useQuery({
    queryKey: certKeys.status(projectId),
    queryFn: () =>
      api
        .get<CertificationResponse>(`/certification/${projectId}`)
        .then((r) => r.data)
        .catch((err) => {
          // 404 means no cert record yet — return null
          if (err?.response?.status === 404) return null;
          throw err;
        }),
    enabled: !!projectId,
  });
}

export function useCertificationBadge(projectId: string) {
  return useQuery({
    queryKey: certKeys.badge(projectId),
    queryFn: () =>
      api
        .get<CertificationBadge>(`/certification/${projectId}/badge`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCertificationRequirements(projectId: string) {
  return useQuery({
    queryKey: certKeys.requirements(projectId),
    queryFn: () =>
      api
        .get<CertificationRequirements>(`/certification/${projectId}/requirements`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useEvaluateCertification(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api
        .post<CertificationResponse>(`/certification/${projectId}/evaluate`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: certKeys.all });
    },
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export const TIER_LABELS: Record<string, string> = {
  bronze: "Bronze",
  silver: "Silver",
  gold: "Gold",
  platinum: "Platinum",
};

export const TIER_COLORS: Record<string, string> = {
  bronze: "#cd7f32",
  silver: "#c0c0c0",
  gold: "#ffd700",
  platinum: "#e5e4e2",
};

export const STATUS_LABELS: Record<string, string> = {
  not_certified: "Not Certified",
  certified: "Certified",
  expired: "Expired",
  suspended: "Suspended",
};

export function tierVariant(
  tier: string | null
): "neutral" | "info" | "success" | "warning" | "gold" {
  if (!tier) return "neutral";
  const map: Record<string, "neutral" | "info" | "success" | "warning" | "gold"> = {
    bronze: "warning",
    silver: "neutral",
    gold: "gold",
    platinum: "success",
  };
  return map[tier] ?? "neutral";
}
