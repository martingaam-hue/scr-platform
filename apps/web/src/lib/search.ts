"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SearchProjectHit {
  type: "project";
  id: string;
  org_id: string;
  name: string;
  project_type: string | null;
  status: string | null;
  stage: string | null;
  geography_country: string | null;
  total_investment_required: number | null;
  score: number;
}

export interface SearchListingHit {
  type: "listing";
  id: string;
  org_id: string;
  project_id: string | null;
  headline: string;
  listing_type: string | null;
  sector: string | null;
  score: number;
}

export interface SearchDocumentHit {
  type: "document";
  id: string;
  org_id: string;
  project_id: string | null;
  filename: string;
  document_type: string | null;
  snippet: string | null;
  score: number;
}

export interface SearchResults {
  query: string;
  total: number;
  projects: SearchProjectHit[];
  listings: SearchListingHit[];
  documents: SearchDocumentHit[];
}

// ── Query key factory ─────────────────────────────────────────────────────────

export const searchKeys = {
  all: ["search"] as const,
  results: (query: string) => [...searchKeys.all, "results", query] as const,
};

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSearch(query: string, enabled: boolean = true) {
  return useQuery({
    queryKey: searchKeys.results(query),
    queryFn: async (): Promise<SearchResults> => {
      const { data } = await api.get("/search", { params: { q: query, limit: 10 } });
      return data;
    },
    enabled: enabled && query.trim().length >= 2,
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });
}
