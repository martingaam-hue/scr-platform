/**
 * Deal Intelligence types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface DealCard {
  project_id: string;
  match_id: string;
  project_name: string;
  project_type: string;
  geography_country: string;
  stage: string;
  total_investment_required: string;
  currency: string;
  signal_score: number | null;
  alignment_score: number;
  status: string;
  cover_image_url: string | null;
  updated_at: string;
}

export interface DealPipeline {
  discovered: DealCard[];
  screening: DealCard[];
  due_diligence: DealCard[];
  negotiation: DealCard[];
  passed: DealCard[];
}

export interface DiscoveryDeal {
  project_id: string;
  project_name: string;
  project_type: string;
  geography_country: string;
  stage: string;
  total_investment_required: string;
  currency: string;
  signal_score: number | null;
  alignment_score: number;
  alignment_reasons: string[];
  cover_image_url: string | null;
  is_in_pipeline: boolean;
}

export interface DiscoveryResponse {
  items: DiscoveryDeal[];
  total: number;
  mandate_name: string | null;
}

export interface ScreeningReport {
  task_log_id: string;
  project_id: string;
  fit_score: number;
  executive_summary: string;
  strengths: string[];
  risks: string[];
  key_metrics: Array<{ label: string; value: string }>;
  mandate_alignment: Array<{ criterion: string; met: boolean; notes: string }>;
  recommendation: "proceed" | "pass" | "need_more_info";
  questions_to_ask: string[];
  model_used: string;
  status: string;
  created_at: string;
}

export interface ScreenAcceptedResponse {
  task_log_id: string;
  status: string;
  message: string;
}

export interface CompareRow {
  dimension: string;
  values: Array<string | number | null>;
  best_index: number | null;
  worst_index: number | null;
}

export interface CompareResponse {
  project_ids: string[];
  project_names: string[];
  rows: CompareRow[];
}

export interface MemoAcceptedResponse {
  memo_id: string;
  status: string;
  message: string;
}

export interface MemoResponse {
  memo_id: string;
  project_id: string;
  title: string;
  status: string;
  content: string | null;
  download_url: string | null;
  model_used: string | null;
  created_at: string;
}

export interface DealStatusUpdateRequest {
  status: string;
  notes?: string;
}

export interface DiscoverParams {
  sector?: string;
  geography?: string;
  score_min?: number;
  score_max?: number;
}

// ── Query Keys ─────────────────────────────────────────────────────────────

export const dealKeys = {
  all: ["deals"] as const,
  pipeline: () => [...dealKeys.all, "pipeline"] as const,
  discover: (params?: DiscoverParams) =>
    [...dealKeys.all, "discover", params ?? {}] as const,
  screening: (projectId: string) =>
    [...dealKeys.all, "screening", projectId] as const,
  memo: (projectId: string, memoId: string) =>
    [...dealKeys.all, "memo", projectId, memoId] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useDealPipeline() {
  return useQuery({
    queryKey: dealKeys.pipeline(),
    queryFn: () =>
      api.get<DealPipeline>("/deals/pipeline").then((r) => r.data),
  });
}

export function useDiscoverDeals(params?: DiscoverParams) {
  const searchParams = new URLSearchParams();
  if (params?.sector) searchParams.set("sector", params.sector);
  if (params?.geography) searchParams.set("geography", params.geography);
  if (params?.score_min != null)
    searchParams.set("score_min", String(params.score_min));
  if (params?.score_max != null)
    searchParams.set("score_max", String(params.score_max));

  const qs = searchParams.toString();
  return useQuery({
    queryKey: dealKeys.discover(params),
    queryFn: () =>
      api
        .get<DiscoveryResponse>(`/deals/discover${qs ? `?${qs}` : ""}`)
        .then((r) => r.data),
  });
}

export function useScreeningReport(projectId: string | undefined) {
  return useQuery({
    queryKey: dealKeys.screening(projectId ?? ""),
    queryFn: () =>
      api
        .get<ScreeningReport>(`/deals/${projectId}/screening`)
        .then((r) => r.data),
    enabled: !!projectId,
    retry: false,
  });
}

export function useTriggerScreening() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post<ScreenAcceptedResponse>(`/deals/${projectId}/screen`)
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      qc.invalidateQueries({ queryKey: dealKeys.screening(projectId) });
    },
  });
}

export function useCompareProjects() {
  return useMutation({
    mutationFn: (projectIds: string[]) =>
      api
        .post<CompareResponse>("/deals/compare", { project_ids: projectIds })
        .then((r) => r.data),
  });
}

export function useTriggerMemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .post<MemoAcceptedResponse>(`/deals/${projectId}/memo`)
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      // Invalidate so polling picks it up
      qc.invalidateQueries({ queryKey: dealKeys.all });
    },
  });
}

export function useMemo(
  projectId: string | undefined,
  memoId: string | undefined
) {
  return useQuery({
    queryKey: dealKeys.memo(projectId ?? "", memoId ?? ""),
    queryFn: () =>
      api
        .get<MemoResponse>(`/deals/${projectId}/memo/${memoId}`)
        .then((r) => r.data),
    enabled: !!projectId && !!memoId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "ready" || data.status === "error")) {
        return false;
      }
      return 5000;
    },
  });
}

export function useUpdateDealStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      status,
      notes,
    }: {
      projectId: string;
      status: string;
      notes?: string;
    }) =>
      api
        .put(`/deals/${projectId}/status`, { status, notes })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dealKeys.pipeline() });
      qc.invalidateQueries({ queryKey: dealKeys.discover() });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

const PIPELINE_LABELS: Record<string, string> = {
  suggested: "Discovered",
  viewed: "Screening",
  interested: "Due Diligence",
  intro_requested: "Negotiation",
  engaged: "Negotiation",
  passed: "Passed",
  declined: "Passed",
};

export function pipelineStageLabel(status: string): string {
  return PIPELINE_LABELS[status] ?? status;
}

export function recommendationColor(
  rec: string
): "success" | "error" | "warning" {
  switch (rec) {
    case "proceed":
      return "success";
    case "pass":
      return "error";
    default:
      return "warning";
  }
}

export function alignmentColor(score: number): string {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-amber-600";
  return "text-red-600";
}

export function alignmentBgColor(score: number): string {
  if (score >= 70) return "bg-green-50 border-green-200";
  if (score >= 40) return "bg-amber-50 border-amber-200";
  return "bg-red-50 border-red-200";
}

const PIPELINE_STATUS_OPTIONS = [
  { label: "Discovered", value: "suggested" },
  { label: "Screening", value: "viewed" },
  { label: "Due Diligence", value: "interested" },
  { label: "Negotiation", value: "intro_requested" },
  { label: "Passed", value: "passed" },
];

export { PIPELINE_STATUS_OPTIONS };
