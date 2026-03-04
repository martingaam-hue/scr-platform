/**
 * Alley Risk — types and React Query hooks.
 * Covers GET /alley/risk and related endpoints.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface RiskItemSummary {
  id: string;
  title: string;
  description: string;
  severity: string;
  dimension: string;
  mitigation_status: string;
  guidance?: string;
  evidence_document_ids: string[];
  notes?: string;
}

export interface ProjectRiskSummary {
  project_id: string;
  project_name: string;
  total_risks: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  mitigation_progress_pct: number;
}

export interface RiskListResponse {
  items: ProjectRiskSummary[];
  total: number;
}

export interface ProjectRiskDetailResponse {
  project_id: string;
  project_name: string;
  risk_items: RiskItemSummary[];
  total_risks: number;
  addressed_risks: number;
  mitigation_progress_pct: number;
}

export interface MitigationProgressResponse {
  project_id: string;
  total_risks: number;
  addressed: number;
  in_progress: number;
  mitigated: number;
  accepted: number;
  unaddressed: number;
  progress_pct: number;
}

// ── Query key factory ──────────────────────────────────────────────────────

export const alleyRiskKeys = {
  all: ["alley-risk"] as const,
  list: () => [...alleyRiskKeys.all, "list"] as const,
  detail: (id: string) => [...alleyRiskKeys.all, "detail", id] as const,
  progress: (id: string) => [...alleyRiskKeys.all, "progress", id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useAlleyRisks() {
  return useQuery({
    queryKey: alleyRiskKeys.list(),
    queryFn: () =>
      api.get<RiskListResponse>("/alley/risk").then((r) => r.data),
  });
}

export function useAlleyRiskDetail(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyRiskKeys.detail(projectId ?? ""),
    queryFn: () =>
      api
        .get<ProjectRiskDetailResponse>(`/alley/risk/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useAlleyRiskProgress(projectId: string | undefined) {
  return useQuery({
    queryKey: alleyRiskKeys.progress(projectId ?? ""),
    queryFn: () =>
      api
        .get<MitigationProgressResponse>(`/alley/risk/${projectId}/progress`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useUpdateMitigation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      riskId,
      status,
      notes,
    }: {
      projectId: string;
      riskId: string;
      status: string;
      notes?: string;
    }) =>
      api
        .patch(`/alley/risk/${projectId}/items/${riskId}`, { status, notes })
        .then((r) => r.data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: alleyRiskKeys.detail(projectId) });
      qc.invalidateQueries({ queryKey: alleyRiskKeys.progress(projectId) });
      qc.invalidateQueries({ queryKey: alleyRiskKeys.list() });
    },
  });
}

export function useAddEvidence() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      riskId,
      body,
    }: {
      projectId: string;
      riskId: string;
      body: Record<string, unknown>;
    }) =>
      api
        .post(
          `/alley/risk/${projectId}/items/${riskId}/evidence`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: alleyRiskKeys.detail(projectId) });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function severityVariant(
  severity: string
): "error" | "warning" | "neutral" | "success" {
  switch (severity.toLowerCase()) {
    case "critical":
    case "high":
      return "error";
    case "medium":
      return "warning";
    case "low":
      return "neutral";
    default:
      return "neutral";
  }
}

export const MITIGATION_STATUS_LABELS: Record<string, string> = {
  unaddressed: "Unaddressed",
  acknowledged: "Acknowledged",
  in_progress: "In Progress",
  mitigated: "Mitigated",
  accepted: "Accepted",
};
