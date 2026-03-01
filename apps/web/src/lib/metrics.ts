/**
 * Metrics, benchmarks, and signal-score explainability hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface MetricSnapshot {
  id: string;
  entity_type: string;
  entity_id: string;
  metric_name: string;
  value: number;
  previous_value: number | null;
  delta: number | null;
  delta_pct: number | null;
  recorded_at: string;
  trigger_event: string | null;
  metadata: Record<string, unknown> | null;
}

export interface MetricTrendResponse {
  data: MetricSnapshot[];
}

export interface MetricRankResponse {
  value: number;
  percentile_rank: number;
  sample_size: number;
}

export interface BenchmarkEntry {
  id: string;
  asset_class: string;
  geography: string;
  stage: string;
  metric_name: string;
  median: number;
  p25: number;
  p75: number;
  sample_count: number;
  computed_at: string | null;
}

export interface BenchmarkListResponse {
  items: BenchmarkEntry[];
  total: number;
}

export interface BenchmarkMetricComparison {
  metric_name: string;
  project_value: number | null;
  median: number;
  p25: number;
  p75: number;
  quartile: 1 | 2 | 3 | 4;
  percentile_rank: number;
  vs_median: number;
  sample_count: number;
}

export interface BenchmarkComparisonResponse {
  project_id: string;
  comparisons: BenchmarkMetricComparison[];
}

export interface ComputeBenchmarksResponse {
  computed: number;
  message: string;
}

export interface ImportBenchmarksResponse {
  imported: number;
  skipped: number;
  message: string;
}

export interface PacingMonth {
  month: string;
  drawn: number;
  distributed: number;
  nav: number;
  cumulative_drawn: number;
  cumulative_distributed: number;
}

export interface CashflowPacingResponse {
  portfolio_id: string;
  scenario: string;
  months: PacingMonth[];
}

export interface QuartileChartPoint {
  metric_name: string;
  project_value: number | null;
  p25: number;
  median: number;
  p75: number;
}

export interface QuartileChartResponse {
  project_id: string;
  data: QuartileChartPoint[];
}

export interface ScoreHistoryTrendPoint {
  recorded_at: string;
  overall_score: number;
  project_viability: number | null;
  financial_planning: number | null;
  team_strength: number | null;
  risk_assessment: number | null;
  esg: number | null;
}

export interface ScoreHistoryTrendResponse {
  items: ScoreHistoryTrendPoint[];
}

export interface ScoreChangeEvent {
  id: string;
  recorded_at: string;
  overall_delta: number;
  dimension_changes: Array<{
    dimension: string;
    from_score: number;
    to_score: number;
    delta: number;
  }>;
  trigger_event: string | null;
  explanation: string | null;
}

export interface ScoreChangesResponse {
  items: ScoreChangeEvent[];
}

export interface ScoreVolatilityResponse {
  project_id: string;
  period_months: number;
  volatility: "low" | "medium" | "high" | "insufficient_data";
  std_dev: number | null;
  sample_count: number;
}

export interface DimensionHistoryPoint {
  recorded_at: string;
  dimension: string;
  score: number;
}

export interface DimensionHistoryResponse {
  items: DimensionHistoryPoint[];
}

// ── Query Keys ─────────────────────────────────────────────────────────────

const STALE = 5 * 60 * 1000;

export const metricsKeys = {
  all: ["metrics"] as const,
  trend: (entityType: string, entityId: string, metricName: string, from?: string, to?: string) =>
    [...metricsKeys.all, "trend", entityType, entityId, metricName, from ?? "", to ?? ""] as const,
  changes: (entityType: string, entityId: string, metricName: string) =>
    [...metricsKeys.all, "changes", entityType, entityId, metricName] as const,
  rank: (entityType: string, entityId: string, metricName: string) =>
    [...metricsKeys.all, "rank", entityType, entityId, metricName] as const,
  benchmarkComparison: (projectId: string, metricNames?: string[]) =>
    [...metricsKeys.all, "benchmark", "compare", projectId, metricNames ?? []] as const,
  benchmarkList: () => [...metricsKeys.all, "benchmark", "list"] as const,
  pacing: (portfolioId: string, scenario?: string) =>
    [...metricsKeys.all, "benchmark", "pacing", portfolioId, scenario ?? "base"] as const,
  quartileChart: (projectId: string) =>
    [...metricsKeys.all, "benchmark", "quartile-chart", projectId] as const,
  scoreHistoryTrend: (projectId: string) =>
    [...metricsKeys.all, "score", "history-trend", projectId] as const,
  scoreChanges: (projectId: string, fromDate?: string, toDate?: string) =>
    [...metricsKeys.all, "score", "changes", projectId, fromDate ?? "", toDate ?? ""] as const,
  scoreVolatility: (projectId: string, periodMonths?: number) =>
    [...metricsKeys.all, "score", "volatility", projectId, periodMonths ?? 12] as const,
  dimensionHistory: (projectId: string) =>
    [...metricsKeys.all, "score", "dimension-history", projectId] as const,
};

// ── Snapshot hooks ─────────────────────────────────────────────────────────

export function useMetricTrend(
  entityType: string,
  entityId: string,
  metricName: string,
  fromDate?: string,
  toDate?: string
) {
  const qs = new URLSearchParams();
  if (fromDate) qs.set("from_date", fromDate);
  if (toDate) qs.set("to_date", toDate);
  const qsStr = qs.toString();

  return useQuery({
    queryKey: metricsKeys.trend(entityType, entityId, metricName, fromDate, toDate),
    queryFn: () =>
      api
        .get<MetricTrendResponse>(
          `/metrics/trend/${entityType}/${entityId}/${metricName}${qsStr ? `?${qsStr}` : ""}`
        )
        .then((r) => r.data),
    enabled: !!entityId,
    staleTime: STALE,
  });
}

export function useMetricChanges(
  entityType: string,
  entityId: string,
  metricName: string
) {
  return useQuery({
    queryKey: metricsKeys.changes(entityType, entityId, metricName),
    queryFn: () =>
      api
        .get<MetricTrendResponse>(
          `/metrics/changes/${entityType}/${entityId}/${metricName}`
        )
        .then((r) => r.data),
    enabled: !!entityId,
    staleTime: STALE,
  });
}

export function useMetricRank(
  entityType: string,
  entityId: string,
  metricName: string
) {
  return useQuery({
    queryKey: metricsKeys.rank(entityType, entityId, metricName),
    queryFn: () =>
      api
        .get<MetricRankResponse>(
          `/metrics/rank/${entityType}/${entityId}/${metricName}`
        )
        .then((r) => r.data),
    enabled: !!entityId,
    staleTime: STALE,
  });
}

// ── Benchmark hooks ────────────────────────────────────────────────────────

export function useBenchmarkComparison(
  projectId: string,
  metricNames?: string[]
) {
  const qs = metricNames?.length
    ? `?metric_names=${metricNames.join(",")}`
    : "";
  return useQuery({
    queryKey: metricsKeys.benchmarkComparison(projectId, metricNames),
    queryFn: () =>
      api
        .get<BenchmarkComparisonResponse>(
          `/metrics/benchmark/compare/${projectId}${qs}`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: STALE,
  });
}

export function useBenchmarkList() {
  return useQuery({
    queryKey: metricsKeys.benchmarkList(),
    queryFn: () =>
      api
        .get<BenchmarkListResponse>("/metrics/benchmark/list")
        .then((r) => r.data),
    staleTime: STALE,
  });
}

export function useComputeBenchmarks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api
        .post<ComputeBenchmarksResponse>("/metrics/benchmark/compute")
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: metricsKeys.benchmarkList() });
    },
  });
}

export function useImportBenchmarks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api
        .post<ImportBenchmarksResponse>("/metrics/benchmark/import", form, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        .then((r) => r.data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: metricsKeys.benchmarkList() });
    },
  });
}

export function useCashflowPacing(
  portfolioId: string,
  scenario?: "base" | "optimistic" | "pessimistic"
) {
  const s = scenario ?? "base";
  return useQuery({
    queryKey: metricsKeys.pacing(portfolioId, s),
    queryFn: () =>
      api
        .get<CashflowPacingResponse>(
          `/metrics/benchmark/pacing/${portfolioId}?scenario=${s}`
        )
        .then((r) => r.data),
    enabled: !!portfolioId,
    staleTime: STALE,
  });
}

export function useQuartileChartData(projectId: string) {
  return useQuery({
    queryKey: metricsKeys.quartileChart(projectId),
    queryFn: () =>
      api
        .get<QuartileChartResponse>(
          `/metrics/benchmark/quartile-chart/${projectId}`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: STALE,
  });
}

// ── Signal score explainability ────────────────────────────────────────────

export function useScoreHistoryTrend(projectId: string) {
  return useQuery({
    queryKey: metricsKeys.scoreHistoryTrend(projectId),
    queryFn: () =>
      api
        .get<ScoreHistoryTrendResponse>(
          `/signal-scores/${projectId}/history-trend`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: STALE,
  });
}

export function useScoreChanges(
  projectId: string,
  fromDate?: string,
  toDate?: string
) {
  const qs = new URLSearchParams();
  if (fromDate) qs.set("from_date", fromDate);
  if (toDate) qs.set("to_date", toDate);
  const qsStr = qs.toString();

  return useQuery({
    queryKey: metricsKeys.scoreChanges(projectId, fromDate, toDate),
    queryFn: () =>
      api
        .get<ScoreChangesResponse>(
          `/signal-scores/${projectId}/changes${qsStr ? `?${qsStr}` : ""}`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: STALE,
  });
}

export function useScoreVolatility(projectId: string, periodMonths?: number) {
  const qs = periodMonths != null ? `?period_months=${periodMonths}` : "";
  return useQuery({
    queryKey: metricsKeys.scoreVolatility(projectId, periodMonths),
    queryFn: () =>
      api
        .get<ScoreVolatilityResponse>(
          `/signal-scores/${projectId}/volatility${qs}`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: STALE,
  });
}

export function useDimensionHistory(projectId: string) {
  return useQuery({
    queryKey: metricsKeys.dimensionHistory(projectId),
    queryFn: () =>
      api
        .get<DimensionHistoryResponse>(
          `/signal-scores/${projectId}/dimension-history`
        )
        .then((r) => r.data),
    enabled: !!projectId,
    staleTime: STALE,
  });
}
