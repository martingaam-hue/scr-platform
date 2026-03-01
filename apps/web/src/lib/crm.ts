"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CRMConnection {
  id: string;
  provider: string;
  connection_name: string;
  is_active: boolean;
  sync_direction: string;
  last_synced_at: string | null;
  error_count: number;
}

export interface SyncLog {
  id: string;
  direction: string;
  entity_type: string;
  action: string;
  status: string;
  error_message: string | null;
  created_at: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useCRMConnections() {
  return useQuery<CRMConnection[]>({
    queryKey: ["crm", "connections"],
    queryFn: () => api.get("/crm/connections").then((r) => r.data),
  });
}

export function useCRMOAuthURL(provider: string) {
  return useQuery<{ url: string }>({
    queryKey: ["crm", "oauth-url", provider],
    queryFn: () =>
      api.get(`/crm/connect/${provider}`).then((r) => r.data),
    enabled: !!provider,
  });
}

export function useDisconnectCRM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      api.delete(`/crm/connections/${connectionId}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm"] }),
  });
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      api
        .post(`/crm/connections/${connectionId}/sync`)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm"] }),
  });
}

export function useSyncLogs(connectionId: string | undefined) {
  return useQuery<SyncLog[]>({
    queryKey: ["crm", "logs", connectionId],
    queryFn: () =>
      api.get(`/crm/connections/${connectionId}/logs`).then((r) => r.data),
    enabled: !!connectionId,
  });
}
