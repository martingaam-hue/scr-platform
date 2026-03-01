"use client";

/**
 * E04 Launch Preparation — types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface FeatureFlag {
  name: string;
  description: string | null;
  enabled_globally: boolean;
  rollout_pct: number;
  org_override: boolean | null;
}

export interface WaitlistEntry {
  id: string;
  email: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export interface UsageEventRequest {
  event_type: string;
  entity_type?: string | null;
  entity_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface UsageSummary {
  org_id: string;
  days: number;
  since: string;
  totals: Record<string, number>;
  total_events: number;
}

export interface TokenUsage {
  org_id: string;
  tier: string;
  tokens_used: number;
  tokens_limit: number;
  tokens_remaining: number;
  usage_pct: number;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  db_ok: boolean;
  redis_ok: boolean;
  checks: Record<string, boolean>;
}

// ── Query key factory ─────────────────────────────────────────────────────────

export const launchKeys = {
  all: ["launch"] as const,
  flags: () => [...launchKeys.all, "flags"] as const,
  health: () => [...launchKeys.all, "health"] as const,
  waitlist: (status?: string) => [...launchKeys.all, "waitlist", status ?? "all"] as const,
  usageSummary: (days: number) => [...launchKeys.all, "usage-summary", days] as const,
  tokenUsage: () => [...launchKeys.all, "token-usage"] as const,
};

// ── Feature flags ─────────────────────────────────────────────────────────────

export function useFeatureFlags() {
  return useQuery({
    queryKey: launchKeys.flags(),
    queryFn: async (): Promise<FeatureFlag[]> => {
      const { data } = await api.get("/launch/flags");
      return data;
    },
    staleTime: 60_000,
  });
}

export function useSetFlagOverride() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      flagName,
      enabled,
    }: {
      flagName: string;
      enabled: boolean;
    }): Promise<FeatureFlag> => {
      const { data } = await api.put(`/launch/flags/${flagName}/override`, {
        enabled,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: launchKeys.flags() });
    },
  });
}

// ── Health status ─────────────────────────────────────────────────────────────

export function useHealthStatus() {
  return useQuery({
    queryKey: launchKeys.health(),
    queryFn: async (): Promise<HealthStatus> => {
      const { data } = await api.get("/launch/health");
      return data;
    },
    refetchInterval: 30_000, // Auto-refresh every 30 s
    staleTime: 25_000,
  });
}

// ── Waitlist ──────────────────────────────────────────────────────────────────

export function useWaitlist(statusFilter?: string) {
  return useQuery({
    queryKey: launchKeys.waitlist(statusFilter),
    queryFn: async (): Promise<WaitlistEntry[]> => {
      const params = statusFilter ? { status: statusFilter } : {};
      const { data } = await api.get("/launch/waitlist", { params });
      return data;
    },
    staleTime: 30_000,
  });
}

export function useApproveWaitlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (entryId: string): Promise<WaitlistEntry> => {
      const { data } = await api.post(`/launch/waitlist/${entryId}/approve`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: launchKeys.waitlist() });
    },
  });
}

export function useJoinWaitlist() {
  return useMutation({
    mutationFn: async (body: {
      email: string;
      name?: string;
      company?: string;
      use_case?: string;
    }): Promise<WaitlistEntry> => {
      const { data } = await api.post("/launch/waitlist", body);
      return data;
    },
  });
}

// ── Usage events ──────────────────────────────────────────────────────────────

export function useRecordUsage() {
  return useMutation({
    mutationFn: async (body: UsageEventRequest): Promise<void> => {
      await api.post("/launch/usage", body);
    },
  });
}

export function useUsageSummary(days = 30) {
  return useQuery({
    queryKey: launchKeys.usageSummary(days),
    queryFn: async (): Promise<UsageSummary> => {
      const { data } = await api.get("/launch/usage/summary", {
        params: { days },
      });
      return data;
    },
    staleTime: 60_000,
  });
}

export function useTokenUsage() {
  return useQuery({
    queryKey: launchKeys.tokenUsage(),
    queryFn: async (): Promise<TokenUsage> => {
      const { data } = await api.get("/launch/usage/tokens");
      return data;
    },
    refetchInterval: 60_000, // Auto-refresh every 60 s
    staleTime: 55_000,
  });
}
