"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PageView {
  page: number;
  time_seconds: number;
}

export interface DocumentEngagement {
  id: string;
  document_id: string;
  viewer_org_id: string;
  pages_viewed: PageView[];
  total_time_seconds: number;
  completion_pct: number;
  downloaded: boolean;
  opened_at: string;
  closed_at: string | null;
}

export interface DealEngagementSummary {
  investor_org_id: string;
  total_time_seconds: number;
  unique_documents_viewed: number;
  avg_completion_pct: number;
  engagement_score: number;
  last_active_at: string;
}

export interface DocumentAnalytics {
  document_id: string;
  total_views: number;
  unique_viewers: number;
  avg_time_seconds: number;
  avg_completion_pct: number;
  download_count: number;
  page_heatmap: Record<string, number>;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useDocumentAnalytics(documentId: string | undefined) {
  return useQuery<DocumentAnalytics>({
    queryKey: ["engagement", "document", documentId],
    queryFn: () =>
      api.get(`/engagement/document/${documentId}`).then((r) => r.data),
    enabled: !!documentId,
  });
}

export function useDealRoomEngagement(dealRoomId: string | undefined) {
  return useQuery<DealEngagementSummary[]>({
    queryKey: ["engagement", "deal-room", dealRoomId],
    queryFn: () =>
      api.get(`/engagement/deal-room/${dealRoomId}`).then((r) => r.data),
    enabled: !!dealRoomId,
  });
}

export function useTrackOpen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { document_id: string; deal_room_id?: string }) =>
      api
        .post("/engagement/track/open", body)
        .then((r) => r.data as DocumentEngagement),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engagement"] }),
  });
}

export function useTrackPage() {
  return useMutation({
    mutationFn: (body: {
      engagement_id: string;
      page_number: number;
      time_seconds: number;
    }) => api.post("/engagement/track/page", body).then((r) => r.data),
  });
}

export function useTrackClose() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { engagement_id: string }) =>
      api.post("/engagement/track/close", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engagement"] }),
  });
}

export function useTrackDownload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { engagement_id: string }) =>
      api.post("/engagement/track/download", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["engagement"] }),
  });
}
