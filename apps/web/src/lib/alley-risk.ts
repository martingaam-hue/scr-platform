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
  source: "auto" | "logged";
}

export interface ProjectRiskSummary {
  project_id: string;
  project_name: string;
  total_risks: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  mitigated_count: number;
  mitigation_progress_pct: number;
  overall_risk_score: number;
  auto_identified_count: number;
  logged_count: number;
}

export interface RiskListResponse {
  items: ProjectRiskSummary[];
  total: number;
  portfolio_risk_score: number;
  total_auto_identified: number;
  total_logged: number;
}

export interface ProjectRiskDetailResponse {
  project_id: string;
  project_name: string;
  risk_items: RiskItemSummary[];
  total_risks: number;
  addressed_risks: number;
  mitigation_progress_pct: number;
  overall_risk_score: number;
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

export interface DomainRiskItem {
  domain: string;
  risk_score: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total: number;
}

export interface DomainRiskResponse {
  domains: DomainRiskItem[];
  portfolio_risk_score: number;
}

export interface RunCheckResponse {
  task_id: string;
  message: string;
}

// ── Query key factory ──────────────────────────────────────────────────────

export const alleyRiskKeys = {
  all: ["alley-risk"] as const,
  list: () => [...alleyRiskKeys.all, "list"] as const,
  detail: (id: string) => [...alleyRiskKeys.all, "detail", id] as const,
  progress: (id: string) => [...alleyRiskKeys.all, "progress", id] as const,
  domains: () => [...alleyRiskKeys.all, "domains"] as const,
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

export function useRiskDomains() {
  return useQuery({
    queryKey: alleyRiskKeys.domains(),
    queryFn: () =>
      api.get<DomainRiskResponse>("/alley/risk/domains").then((r) => r.data),
  });
}

export function useRunRiskCheck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post<RunCheckResponse>(`/alley/risk/${projectId}/check`)
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      qc.invalidateQueries({ queryKey: alleyRiskKeys.detail(projectId) });
      qc.invalidateQueries({ queryKey: alleyRiskKeys.list() });
      qc.invalidateQueries({ queryKey: alleyRiskKeys.domains() });
    },
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
        .post(`/alley/risk/${projectId}/items/${riskId}/evidence`, body)
        .then((r) => r.data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: alleyRiskKeys.detail(projectId) });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

/** 4-tier severity → Badge variant */
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

/** 4-tier severity color classes for custom styling */
export function severityClasses(severity: string): {
  dot: string;
  bg: string;
  text: string;
  border: string;
} {
  switch (severity.toLowerCase()) {
    case "critical":
      return {
        dot: "bg-black",
        bg: "bg-black/10",
        text: "text-black",
        border: "border-black/20",
      };
    case "high":
      return {
        dot: "bg-red-500",
        bg: "bg-red-50",
        text: "text-red-700",
        border: "border-red-200",
      };
    case "medium":
      return {
        dot: "bg-amber-400",
        bg: "bg-amber-50",
        text: "text-amber-700",
        border: "border-amber-200",
      };
    default:
      return {
        dot: "bg-green-500",
        bg: "bg-green-50",
        text: "text-green-700",
        border: "border-green-200",
      };
  }
}

/** Risk management score 0–100 → color (higher = better managed = greener) */
export function riskScoreColor(score: number): string {
  if (score >= 80) return "#22c55e";  // Excellent / Strong
  if (score >= 70) return "#3b82f6";  // Good
  if (score >= 60) return "#f59e0b";  // Fair — some areas need attention
  if (score >= 50) return "#eab308";  // Concerning — multiple unaddressed risks
  return "#ef4444";                    // Critical — immediate action required
}

// ── Mitigation Strategy types ──────────────────────────────────────────────

export interface MitigationAction {
  action: string;
  timeline: string;
  owner: string;
  expected_impact: string;
}

export interface MitigationStrategy {
  risk_id: string;
  risk_title: string;
  recommended_actions: MitigationAction[];
  overall_timeline: string;
  expected_impact: string;
  generated_at: string;
}

export interface PortfolioMitigationPlan {
  portfolio_summary: string;
  top_priorities: string[];
  cross_project_recommendations: string[];
  risk_reduction_timeline: string;
  generated_at: string;
}

export function useGenerateMitigation() {
  return useMutation({
    mutationFn: ({
      projectId,
      riskId,
    }: {
      projectId: string;
      riskId: string;
    }) =>
      api
        .post<MitigationStrategy>(
          `/alley/risk/${projectId}/items/${riskId}/mitigation-strategy`
        )
        .then((r) => r.data),
  });
}

export function useGeneratePortfolioMitigation() {
  return useMutation({
    mutationFn: (projectId?: string) =>
      api
        .post<PortfolioMitigationPlan>("/alley/risk/mitigation-strategy", {
          project_id: projectId ?? null,
        })
        .then((r) => r.data),
  });
}

export const MITIGATION_STATUS_LABELS: Record<string, string> = {
  unaddressed: "Unaddressed",
  acknowledged: "Acknowledged",
  in_progress: "In Progress",
  mitigated: "Mitigated",
  accepted: "Accepted",
};

export const DOMAIN_LABELS: Record<string, string> = {
  technical: "Technical",
  financial: "Financial",
  regulatory: "Regulatory",
  esg: "ESG",
  market: "Market",
};
