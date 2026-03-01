/**
 * Digest — React Query hooks for AI activity digest preview + preferences.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export type DigestFrequency = "daily" | "weekly" | "monthly";

export interface DigestPreferences {
  is_subscribed: boolean;
  frequency: DigestFrequency;
}

export interface DigestSummary {
  new_projects?: number;
  new_documents?: number;
  new_matches?: number;
  new_alerts?: number;
  signal_score_updates?: number;
  [key: string]: number | undefined;
}

export interface DigestPreviewResponse {
  days: number;
  summary: DigestSummary;
}

export interface DigestTriggerResponse {
  status: string;
  days: number;
  narrative: string;
  data: DigestSummary;
}

export interface DigestHistoryEntry {
  id: string;
  sent_at: string;
  recipients: number;
  status: string;
}

export interface DigestHistoryResponse {
  history: DigestHistoryEntry[];
  message?: string;
}

// ── Query key factory ───────────────────────────────────────────────────────

export const digestKeys = {
  preview: (days: number) => ["digest", "preview", days] as const,
  preferences: ["digest", "preferences"] as const,
  history: ["digest", "history"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useDigestPreview(days: number = 7) {
  return useQuery({
    queryKey: digestKeys.preview(days),
    queryFn: async () => {
      const { data } = await api.get<DigestPreviewResponse>("/digest/preview", {
        params: { days },
      });
      return data;
    },
  });
}

export function useDigestPreferences() {
  return useQuery({
    queryKey: digestKeys.preferences,
    queryFn: async () => {
      const { data } = await api.get<DigestPreferences>("/digest/preferences");
      return data;
    },
  });
}

export function useUpdateDigestPreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DigestPreferences) => {
      const { data } = await api.put<DigestPreferences>("/digest/preferences", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: digestKeys.preferences }),
  });
}

export function useDigestHistory() {
  return useQuery({
    queryKey: digestKeys.history,
    queryFn: async () => {
      const { data } = await api.get<DigestHistoryResponse>("/digest/history");
      return data;
    },
  });
}

export function useTriggerDigest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (days: number = 7) => {
      const { data } = await api.post<DigestTriggerResponse>("/digest/trigger", null, {
        params: { days },
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: digestKeys.history }),
  });
}
