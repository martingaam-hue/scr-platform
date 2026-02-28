"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Connector {
  id: string;
  name: string;
  display_name: string;
  category: string;
  description: string;
  pricing_tier: string;
  rate_limit_per_minute: number;
  auth_type: string;
}

export interface ConnectorConfig {
  connector_id: string;
  is_enabled: boolean;
  total_calls_this_month: number;
}

export interface UsageStats {
  connector_id: string;
  total_calls: number;
  success_calls: number;
  error_calls: number;
  avg_response_ms: number;
  calls_today: number;
}

export interface TestResult {
  ok: boolean;
  message: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useConnectors() {
  return useQuery<Connector[]>({
    queryKey: ["connectors"],
    queryFn: () => api.get("/connectors/").then((r) => r.data),
  });
}

export function useConnectorConfigs() {
  return useQuery<ConnectorConfig[]>({
    queryKey: ["connector-configs"],
    queryFn: () => api.get("/connectors/configs").then((r) => r.data),
  });
}

export function useConnectorUsage() {
  return useQuery<UsageStats[]>({
    queryKey: ["connector-usage"],
    queryFn: () => api.get("/connectors/usage").then((r) => r.data),
  });
}

export function useUpdateConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      connectorId,
      apiKey,
      isEnabled,
    }: {
      connectorId: string;
      apiKey?: string;
      isEnabled?: boolean;
    }) =>
      api
        .put(`/connectors/${connectorId}`, {
          api_key: apiKey,
          is_enabled: isEnabled,
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connector-configs"] });
    },
  });
}

export function useTestConnector() {
  return useMutation({
    mutationFn: (connectorId: string) =>
      api
        .post(`/connectors/${connectorId}/test`)
        .then((r) => r.data as TestResult),
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const CATEGORY_COLORS: Record<string, string> = {
  energy_market: "bg-yellow-100 text-yellow-700",
  corporate_registry: "bg-blue-100 text-blue-700",
  weather: "bg-sky-100 text-sky-700",
  fx_rates: "bg-green-100 text-green-700",
  financial: "bg-purple-100 text-purple-700",
};

export const TIER_BADGE: Record<string, string> = {
  free: "bg-gray-100 text-gray-600",
  standard: "bg-blue-100 text-blue-600",
  premium: "bg-amber-100 text-amber-700",
};
