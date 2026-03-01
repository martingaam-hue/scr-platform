/**
 * Citations — React Query hooks for B04 citation badge feature.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface Citation {
  id: string;
  claim_text: string;
  claim_index: number;
  source_type: string;
  document_id: string | null;
  document_name: string | null;
  page_or_section: string | null;
  confidence: number;
  verified: boolean | null;
}

export interface CitationStats {
  total_citations: number;
  verified_count: number;
  unverified_count: number;
  avg_confidence: number;
  by_source_type: Record<string, number>;
}

// ── Query Keys ─────────────────────────────────────────────────────────────

export const citationKeys = {
  all: ["citations"] as const,
  output: (aiTaskLogId: string) =>
    [...citationKeys.all, "output", aiTaskLogId] as const,
  stats: () => [...citationKeys.all, "stats"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useCitations(aiTaskLogId: string | undefined) {
  return useQuery({
    queryKey: citationKeys.output(aiTaskLogId ?? ""),
    queryFn: () =>
      api
        .get<Citation[]>(`/citations/output/${aiTaskLogId}`)
        .then((r) => r.data),
    enabled: !!aiTaskLogId,
  });
}

export function useVerifyCitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      citationId,
      isCorrect,
    }: {
      citationId: string;
      isCorrect: boolean;
    }) =>
      api
        .post(`/citations/${citationId}/verify?is_correct=${isCorrect}`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: citationKeys.all });
    },
  });
}

export function useCitationStats() {
  return useQuery({
    queryKey: citationKeys.stats(),
    queryFn: () =>
      api.get<CitationStats>("/citations/stats").then((r) => r.data),
  });
}
