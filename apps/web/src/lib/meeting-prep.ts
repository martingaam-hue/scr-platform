"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BriefingContent {
  executive_summary?: string;
  key_metrics?: Record<string, unknown>;
  risk_flags?: Array<{
    flag: string;
    severity: string;
    mitigation?: string;
  }>;
  dd_progress?: {
    total?: number;
    completed?: number;
    pct?: number;
    outstanding_items?: string[];
  };
  talking_points?: string[];
  questions_to_ask?: string[];
  changes_since_last?: string[];
}

export interface Briefing {
  id: string;
  project_id: string;
  meeting_type: string;
  meeting_date: string | null;
  briefing_content: BriefingContent | null;
  custom_overrides: Record<string, unknown> | null;
  created_at: string;
}

export interface BriefingsResponse {
  items: Briefing[];
  total: number;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useBriefings(projectId: string) {
  return useQuery<BriefingsResponse>({
    queryKey: ["meeting-briefings", projectId],
    queryFn: () =>
      api
        .get(`/meeting-prep/briefings?project_id=${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useBriefing(briefingId: string | null) {
  return useQuery<Briefing>({
    queryKey: ["meeting-briefing", briefingId],
    queryFn: () =>
      api.get(`/meeting-prep/briefings/${briefingId}`).then((r) => r.data),
    enabled: !!briefingId,
  });
}

export function useGenerateBriefing(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      meeting_type: string;
      meeting_date: string | null;
      previous_meeting_date: string | null;
    }) =>
      api
        .post<Briefing>("/meeting-prep/briefings", {
          project_id: projectId,
          ...body,
        })
        .then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["meeting-briefings", projectId] }),
  });
}

export function useDeleteBriefing(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (briefingId: string) =>
      api.delete(`/meeting-prep/briefings/${briefingId}`).then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["meeting-briefings", projectId] }),
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const MEETING_TYPES = [
  { value: "screening", label: "Screening" },
  { value: "dd_review", label: "DD Review" },
  { value: "follow_up", label: "Follow-Up" },
  { value: "ic_presentation", label: "IC Presentation" },
] as const;

export const RISK_SEVERITY_COLOR: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-green-100 text-green-700 border-green-200",
};
