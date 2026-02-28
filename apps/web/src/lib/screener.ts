"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ParsedFilters {
  project_types?: string[];
  geographies?: string[];
  stages?: string[];
  min_signal_score?: number;
  max_signal_score?: number;
  min_ticket_size?: number;
  max_ticket_size?: number;
  sector_keywords?: string[];
  sort_by?: string;
}

export interface ScreenerResult {
  id: string;
  name: string;
  project_type: string | null;
  geography_country: string | null;
  stage: string | null;
  total_investment_required: number | null;
  currency: string | null;
  signal_score: number | null;
  status: string | null;
}

export interface ScreenerResponse {
  query: string;
  parsed_filters: ParsedFilters;
  results: ScreenerResult[];
  total_results: number;
  suggestions: string[];
}

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  filters: ParsedFilters;
  notify_new_matches: boolean;
  last_used: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useSavedSearches() {
  return useQuery<SavedSearch[]>({
    queryKey: ["screener-saved"],
    queryFn: () =>
      api.get("/screener/saved").then((r) => {
        const data = r.data;
        return Array.isArray(data) ? data : (data.searches ?? []);
      }),
  });
}

export function useScreenerSearch() {
  return useMutation({
    mutationFn: ({
      query,
      existingFilters,
    }: {
      query: string;
      existingFilters?: ParsedFilters;
    }) =>
      api
        .post<ScreenerResponse>("/screener/search", {
          query,
          existing_filters:
            existingFilters && Object.keys(existingFilters).length
              ? existingFilters
              : undefined,
        })
        .then((r) => r.data),
  });
}

export function useSaveSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      query: string;
      filters: ParsedFilters;
      notify_new_matches: boolean;
    }) => api.post("/screener/save", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["screener-saved"] }),
  });
}

export function useDeleteSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/screener/saved/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["screener-saved"] }),
  });
}
