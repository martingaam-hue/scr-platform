/**
 * Reports types and React Query hooks.
 *
 * Types mirror the FastAPI Pydantic schemas. Hooks wrap axios calls
 * with React Query for caching, mutations, and polling.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Enums ──────────────────────────────────────────────────────────────────

export type ReportCategory =
  | "performance"
  | "esg"
  | "compliance"
  | "portfolio"
  | "project"
  | "custom";

export type ReportStatus = "queued" | "generating" | "ready" | "error";

export type ReportFrequency =
  | "daily"
  | "weekly"
  | "biweekly"
  | "monthly"
  | "quarterly"
  | "annually";

export type OutputFormat = "pdf" | "xlsx" | "pptx";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ReportTemplateResponse {
  id: string;
  org_id: string | null;
  name: string;
  category: ReportCategory;
  description: string;
  template_config: Record<string, unknown>;
  sections: Record<string, unknown> | null;
  is_system: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ReportTemplateListResponse {
  items: ReportTemplateResponse[];
  total: number;
}

export interface GeneratedReportResponse {
  id: string;
  org_id: string;
  template_id: string | null;
  title: string;
  status: ReportStatus;
  parameters: Record<string, unknown> | null;
  result_data: Record<string, unknown> | null;
  s3_key: string | null;
  error_message: string | null;
  generated_by: string;
  completed_at: string | null;
  download_url: string | null;
  template_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedReportListResponse {
  items: GeneratedReportResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GenerateReportAcceptedResponse {
  report_id: string;
  status: ReportStatus;
  message: string;
}

export interface ScheduledReportResponse {
  id: string;
  org_id: string;
  template_id: string;
  name: string;
  frequency: ReportFrequency;
  parameters: Record<string, unknown> | null;
  recipients: Record<string, unknown> | null;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  template_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduledReportListResponse {
  items: ScheduledReportResponse[];
  total: number;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const reportKeys = {
  all: ["reports"] as const,
  templates: (category?: ReportCategory) =>
    [...reportKeys.all, "templates", category] as const,
  template: (id: string) =>
    [...reportKeys.all, "template", id] as const,
  list: (params?: { status?: ReportStatus; page?: number; page_size?: number }) =>
    [...reportKeys.all, "list", params] as const,
  detail: (id: string) => [...reportKeys.all, "detail", id] as const,
  schedules: () => [...reportKeys.all, "schedules"] as const,
};

// ── Template hooks ─────────────────────────────────────────────────────────

export function useReportTemplates(category?: ReportCategory) {
  return useQuery({
    queryKey: reportKeys.templates(category),
    queryFn: () =>
      api
        .get<ReportTemplateListResponse>("/reports/templates", {
          params: category ? { category } : undefined,
        })
        .then((r) => r.data),
  });
}

export function useReportTemplate(id: string | undefined) {
  return useQuery({
    queryKey: reportKeys.template(id ?? ""),
    queryFn: () =>
      api
        .get<ReportTemplateResponse>(`/reports/templates/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

// ── Report hooks ───────────────────────────────────────────────────────────

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      template_id: string;
      parameters: Record<string, unknown>;
      output_format: OutputFormat;
      title?: string;
    }) =>
      api
        .post<GenerateReportAcceptedResponse>("/reports/generate", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.all });
    },
  });
}

export function useReports(params?: {
  status?: ReportStatus;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: reportKeys.list(params),
    queryFn: () =>
      api
        .get<GeneratedReportListResponse>("/reports", { params })
        .then((r) => r.data),
  });
}

export function useReport(id: string | undefined) {
  return useQuery({
    queryKey: reportKeys.detail(id ?? ""),
    queryFn: () =>
      api
        .get<GeneratedReportResponse>(`/reports/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function useDeleteReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reportId: string) =>
      api.delete(`/reports/${reportId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.all });
    },
  });
}

// ── Schedule hooks ─────────────────────────────────────────────────────────

export function useSchedules() {
  return useQuery({
    queryKey: reportKeys.schedules(),
    queryFn: () =>
      api
        .get<ScheduledReportListResponse>("/reports/schedules")
        .then((r) => r.data),
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      template_id: string;
      name: string;
      frequency: ReportFrequency;
      parameters: Record<string, unknown>;
      recipients: string[];
      output_format: OutputFormat;
    }) =>
      api
        .post<ScheduledReportResponse>("/reports/schedules", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.schedules() });
    },
  });
}

export function useUpdateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      scheduleId,
      ...body
    }: {
      scheduleId: string;
      name?: string;
      frequency?: ReportFrequency;
      parameters?: Record<string, unknown>;
      recipients?: string[];
      output_format?: OutputFormat;
      is_active?: boolean;
    }) =>
      api
        .put<ScheduledReportResponse>(`/reports/schedules/${scheduleId}`, body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.schedules() });
    },
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scheduleId: string) =>
      api.delete(`/reports/schedules/${scheduleId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.schedules() });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<ReportStatus, "neutral" | "warning" | "success" | "error"> = {
  queued: "neutral",
  generating: "warning",
  ready: "success",
  error: "error",
};

export function reportStatusColor(status: ReportStatus) {
  return STATUS_COLORS[status] ?? "neutral";
}

const CATEGORY_LABELS: Record<ReportCategory, string> = {
  performance: "Performance",
  esg: "ESG",
  compliance: "Compliance",
  portfolio: "Portfolio",
  project: "Project",
  custom: "Custom",
};

export function reportCategoryLabel(category: ReportCategory) {
  return CATEGORY_LABELS[category] ?? category;
}

const FREQUENCY_LABELS: Record<ReportFrequency, string> = {
  daily: "Daily",
  weekly: "Weekly",
  biweekly: "Bi-weekly",
  monthly: "Monthly",
  quarterly: "Quarterly",
  annually: "Annually",
};

export function frequencyLabel(frequency: ReportFrequency) {
  return FREQUENCY_LABELS[frequency] ?? frequency;
}

const FORMAT_LABELS: Record<OutputFormat, string> = {
  pdf: "PDF",
  xlsx: "Excel",
  pptx: "PowerPoint",
};

export function formatLabel(format: OutputFormat) {
  return FORMAT_LABELS[format] ?? format.toUpperCase();
}
