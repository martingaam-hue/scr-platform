"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Covenant {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  metric_name: string;
  threshold_value: number;
  comparison: string;
  threshold_max: number | null;
  warning_threshold_pct: number;
  status: string;
  last_checked_at: string | null;
  waived_reason: string | null;
}

export interface KPIActual {
  id: string;
  project_id: string;
  kpi_name: string;
  value: number;
  unit: string | null;
  period: string;
  period_type: string;
  source: string;
  recorded_at: string;
}

export interface KPITarget {
  id: string;
  project_id: string;
  kpi_name: string;
  target_value: number;
  period: string;
  tolerance_pct: number;
}

export interface KPIVariance {
  kpi_name: string;
  period: string;
  actual: number | null;
  target: number | null;
  variance_pct: number | null;
  status: string;
}

export interface PortfolioDashboard {
  project_summaries: Array<{
    project_id: string;
    project_name: string;
    compliant: number;
    warning: number;
    breach: number;
    traffic_light: string;
  }>;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useCovenants(projectId: string | undefined) {
  return useQuery<Covenant[]>({
    queryKey: ["monitoring", "covenants", projectId],
    queryFn: () =>
      api
        .get(`/monitoring/projects/${projectId}/covenants`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateCovenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      body,
    }: {
      projectId: string;
      body: Record<string, unknown>;
    }) =>
      api
        .post(`/monitoring/projects/${projectId}/covenants`, body)
        .then((r) => r.data as Covenant),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitoring"] }),
  });
}

export function useKPIActuals(
  projectId: string | undefined,
  period?: string
) {
  return useQuery<KPIActual[]>({
    queryKey: ["monitoring", "kpi-actuals", projectId, period],
    queryFn: () =>
      api
        .get(`/monitoring/projects/${projectId}/kpi-actuals`, {
          params: period ? { period } : undefined,
        })
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useAddKPIActual() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      body,
    }: {
      projectId: string;
      body: Record<string, unknown>;
    }) =>
      api
        .post(`/monitoring/projects/${projectId}/kpi-actuals`, body)
        .then((r) => r.data as KPIActual),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitoring"] }),
  });
}

export function useKPITargets(projectId: string | undefined) {
  return useQuery<KPITarget[]>({
    queryKey: ["monitoring", "kpi-targets", projectId],
    queryFn: () =>
      api
        .get(`/monitoring/projects/${projectId}/kpi-targets`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useKPIVariance(projectId: string | undefined) {
  return useQuery<KPIVariance[]>({
    queryKey: ["monitoring", "kpi-variance", projectId],
    queryFn: () =>
      api
        .get(`/monitoring/projects/${projectId}/kpi-variance`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function usePortfolioDashboard() {
  return useQuery<PortfolioDashboard>({
    queryKey: ["monitoring", "portfolio-dashboard"],
    queryFn: () =>
      api.get("/monitoring/portfolio-dashboard").then((r) => r.data),
  });
}

export function useCheckCovenants(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api
        .post(`/monitoring/projects/${projectId}/check-covenants`)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitoring"] }),
  });
}
