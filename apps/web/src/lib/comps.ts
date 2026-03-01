"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Comp {
  id: string;
  deal_name: string;
  asset_type: string;
  geography: string | null;
  country_code: string | null;
  close_year: number | null;
  deal_size_eur: number | null;
  capacity_mw: number | null;
  ev_per_mw: number | null;
  equity_irr: number | null;
  stage_at_close: string | null;
  data_quality: string;
  org_id: string | null;
}

export interface CompsFilters {
  asset_type?: string;
  geography?: string;
  year_from?: string;
  year_to?: string;
  stage?: string;
}

export interface CompsListResponse {
  items: Comp[];
  total: number;
}

export interface ValuationResult {
  method: string;
  ev_eur: number;
  ev_per_mw: number;
  implied_irr: number | null;
  comps_used: number;
  confidence: string;
}

export interface SimilarCompResult {
  comp: {
    id: string;
    deal_name: string;
    asset_type: string;
    geography: string | null;
    ev_per_mw: number | null;
    ebitda_multiple: number | null;
    close_year: number | null;
    data_quality: string;
  };
  similarity_score: number;
  rationale: string;
}

export interface SimilarCompsResponse {
  items: SimilarCompResult[];
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useComps(filters: CompsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.asset_type) params.set("asset_type", filters.asset_type);
  if (filters.geography) params.set("geography", filters.geography);
  if (filters.year_from) params.set("year_from", filters.year_from);
  if (filters.year_to) params.set("year_to", filters.year_to);
  if (filters.stage) params.set("stage", filters.stage);

  return useQuery<CompsListResponse>({
    queryKey: ["comps", filters],
    queryFn: () => api.get(`/comps?${params}`).then((r) => r.data),
  });
}

export function useCreateComp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/comps", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["comps"] }),
  });
}

export function useUploadComps() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post("/comps/upload", form).then((r) => r.data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["comps"] }),
  });
}

export function useSimilarComps(projectId: string | null | undefined) {
  return useQuery<SimilarCompsResponse>({
    queryKey: ["comps", "similar", projectId],
    queryFn: () =>
      api.get(`/comps/similar/${projectId}?limit=10`).then((r) => r.data),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompsValuation() {
  return useMutation({
    mutationFn: ({ ids, capacityMw }: { ids: string[]; capacityMw?: number }) =>
      api
        .post("/comps/implied-valuation", {
          comp_ids: ids,
          project: { capacity_mw: capacityMw ?? 50 },
        })
        .then((r) => r.data as ValuationResult),
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const QUALITY_BADGE: Record<string, string> = {
  confirmed: "bg-green-100 text-green-700",
  estimated: "bg-yellow-100 text-yellow-700",
  rumored: "bg-gray-100 text-gray-600",
};

export const ASSET_TYPES = [
  "solar",
  "wind",
  "hydro",
  "bess",
  "biomass",
  "infrastructure",
  "private_equity",
  "other",
];

export const STAGES = ["development", "construction_ready", "operational"];
