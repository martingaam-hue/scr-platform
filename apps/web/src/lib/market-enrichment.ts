"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MarketDataSource {
  id: string;
  org_id: string;
  name: string;
  slug: string;
  description: string | null;
  source_type: "official_api" | "rss_feed" | "document" | "manual";
  tier: 1 | 2 | 3 | 4;
  base_url: string | null;
  legal_basis: "public_data" | "licensed" | "fair_use" | "manual_entry";
  rate_limit_per_hour: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FetchLog {
  id: string;
  org_id: string;
  source_id: string;
  status: "pending" | "running" | "success" | "failed" | "rate_limited";
  records_fetched: number;
  records_new: number;
  records_updated: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface MarketDataProcessed {
  id: string;
  org_id: string;
  raw_id: string | null;
  data_type: "price" | "policy" | "project_pipeline" | "macro_indicator" | "news";
  category: string;
  region: string | null;
  technology: string | null;
  effective_date: string | null;
  value_numeric: number | null;
  value_text: string | null;
  value_json: Record<string, unknown> | null;
  unit: string | null;
  confidence: number;
  source_url: string | null;
  review_status: "pending_review" | "auto_accepted" | "approved" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface ReviewQueueItem {
  id: string;
  org_id: string;
  processed_id: string;
  assigned_to: string | null;
  priority: number;
  reason: string;
  resolved_at: string | null;
  created_at: string;
  processed: MarketDataProcessed | null;
}

export interface MarketEnrichmentDashboard {
  sources_count: number;
  active_sources_count: number;
  records_today: number;
  pending_review_count: number;
  recent_fetches: FetchLog[];
}

export interface SourceFilters {
  tier?: number;
  is_active?: boolean;
}

export interface DataFilters {
  data_type?: string;
  category?: string;
  region?: string;
  technology?: string;
  effective_date_from?: string;
  effective_date_to?: string;
  review_status?: string;
  skip?: number;
  limit?: number;
}

// ── Query key factory ─────────────────────────────────────────────────────────

export const marketEnrichmentKeys = {
  all: ["market-enrichment"] as const,
  dashboard: () => [...marketEnrichmentKeys.all, "dashboard"] as const,
  sources: (filters?: SourceFilters) =>
    [...marketEnrichmentKeys.all, "sources", filters] as const,
  sourceLogs: (sourceId: string) =>
    [...marketEnrichmentKeys.all, "sources", sourceId, "logs"] as const,
  data: (filters?: DataFilters) => [...marketEnrichmentKeys.all, "data", filters] as const,
  dataRecord: (id: string) => [...marketEnrichmentKeys.all, "data", id] as const,
  reviewQueue: () => [...marketEnrichmentKeys.all, "review-queue"] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useMarketEnrichmentDashboard() {
  return useQuery<MarketEnrichmentDashboard>({
    queryKey: marketEnrichmentKeys.dashboard(),
    queryFn: () => api.get("/market-enrichment/dashboard").then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useMarketDataSources(filters: SourceFilters = {}) {
  const params = new URLSearchParams();
  if (filters.tier != null) params.set("tier", String(filters.tier));
  if (filters.is_active != null) params.set("is_active", String(filters.is_active));

  return useQuery<MarketDataSource[]>({
    queryKey: marketEnrichmentKeys.sources(filters),
    queryFn: () =>
      api.get(`/market-enrichment/sources?${params}`).then((r) => r.data),
    staleTime: 120_000,
  });
}

export function useSourceFetchLogs(sourceId: string | null) {
  return useQuery<FetchLog[]>({
    queryKey: marketEnrichmentKeys.sourceLogs(sourceId ?? ""),
    queryFn: () =>
      api.get(`/market-enrichment/sources/${sourceId}/logs`).then((r) => r.data),
    enabled: !!sourceId,
  });
}

export function useMarketData(filters: DataFilters = {}) {
  const params = new URLSearchParams();
  if (filters.data_type) params.set("data_type", filters.data_type);
  if (filters.category) params.set("category", filters.category);
  if (filters.region) params.set("region", filters.region);
  if (filters.technology) params.set("technology", filters.technology);
  if (filters.effective_date_from) params.set("effective_date_from", filters.effective_date_from);
  if (filters.effective_date_to) params.set("effective_date_to", filters.effective_date_to);
  if (filters.review_status) params.set("review_status", filters.review_status);
  if (filters.skip != null) params.set("skip", String(filters.skip));
  if (filters.limit != null) params.set("limit", String(filters.limit));

  return useQuery<MarketDataProcessed[]>({
    queryKey: marketEnrichmentKeys.data(filters),
    queryFn: () =>
      api.get(`/market-enrichment/data?${params}`).then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useReviewQueue() {
  return useQuery<ReviewQueueItem[]>({
    queryKey: marketEnrichmentKeys.reviewQueue(),
    queryFn: () => api.get("/market-enrichment/review-queue").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function useCreateSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/market-enrichment/sources", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: marketEnrichmentKeys.sources() }),
  });
}

export function useTriggerFetch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) =>
      api.post(`/market-enrichment/sources/${sourceId}/fetch`).then((r) => r.data),
    onSuccess: (_data, sourceId) => {
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.sourceLogs(sourceId) });
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.dashboard() });
    },
  });
}

export function useCreateManualEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/market-enrichment/data/manual", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.data() });
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.dashboard() });
    },
  });
}

export function useReviewEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      processedId,
      action,
      notes,
    }: {
      processedId: string;
      action: "approve" | "reject";
      notes?: string;
    }) =>
      api
        .post(`/market-enrichment/data/${processedId}/review`, { action, notes })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.reviewQueue() });
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.data() });
      qc.invalidateQueries({ queryKey: marketEnrichmentKeys.dashboard() });
    },
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const DATA_TYPES = [
  { value: "price", label: "Price" },
  { value: "policy", label: "Policy" },
  { value: "project_pipeline", label: "Project Pipeline" },
  { value: "macro_indicator", label: "Macro Indicator" },
  { value: "news", label: "News" },
];

export const TIER_LABELS: Record<number, string> = {
  1: "Official API",
  2: "RSS Feed",
  3: "Document",
  4: "Manual",
};

export const LEGAL_BASIS_LABELS: Record<string, string> = {
  public_data: "Public Data",
  licensed: "Licensed",
  fair_use: "Fair Use",
  manual_entry: "Manual Entry",
};

export const REVIEW_STATUS_BADGE: Record<string, string> = {
  pending_review: "bg-yellow-100 text-yellow-700",
  auto_accepted: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
};

export const FETCH_STATUS_BADGE: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  rate_limited: "bg-orange-100 text-orange-700",
};
