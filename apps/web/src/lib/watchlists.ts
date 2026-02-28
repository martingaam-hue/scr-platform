"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Watchlist {
  id: string;
  name: string;
  watch_type: string;
  criteria: Record<string, unknown>;
  alert_channels: string[];
  alert_frequency: string;
  is_active: boolean;
  total_alerts_sent: number;
  unread_alerts: number;
}

export interface WatchlistAlert {
  id: string;
  watchlist_id: string;
  watchlist_name: string;
  alert_type: string;
  entity_type: string;
  entity_id: string;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface ParsedCriteria {
  criteria: Record<string, unknown>;
  watch_type?: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useWatchlists() {
  return useQuery<Watchlist[]>({
    queryKey: ["watchlists"],
    queryFn: () => api.get("/watchlists/").then((r) => r.data),
  });
}

export function useWatchlistAlerts() {
  return useQuery<WatchlistAlert[]>({
    queryKey: ["watchlist-alerts"],
    queryFn: () => api.get("/watchlists/alerts").then((r) => r.data),
  });
}

export function useCreateWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/watchlists/", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useDeleteWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/watchlists/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useToggleWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.put(`/watchlists/${id}/toggle`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });
}

export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) =>
      api.put(`/watchlists/alerts/${alertId}/read`).then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["watchlist-alerts"] }),
  });
}

export function useParseCriteria() {
  return useMutation({
    mutationFn: (query: string) =>
      api
        .post("/watchlists/parse-criteria", { query })
        .then((r) => r.data as ParsedCriteria),
  });
}
