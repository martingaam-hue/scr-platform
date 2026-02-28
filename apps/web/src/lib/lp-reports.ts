/**
 * LP Reporting — React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface LPReportNarrative {
  executive_summary: string;
  portfolio_commentary: string;
  market_outlook: string;
  esg_highlights: string;
}

export interface InvestmentDataItem {
  project_id: string;
  name: string;
  vintage?: number | null;
  committed?: number | null;
  invested?: number | null;
  nav?: number | null;
  realized?: number | null;
  moic?: number | null;
  stage?: string | null;
  notes?: string | null;
}

export interface LPReport {
  id: string;
  org_id: string;
  portfolio_id: string | null;
  report_period: string;
  period_start: string;
  period_end: string;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  gross_irr: number | null;
  net_irr: number | null;
  tvpi: number | null;
  dpi: number | null;
  rvpi: number | null;
  moic: number | null;
  total_committed: number | null;
  total_invested: number | null;
  total_returned: number | null;
  total_nav: number | null;
  narrative: LPReportNarrative | null;
  investments_data: InvestmentDataItem[];
  pdf_s3_key: string | null;
  generated_at: string | null;
  download_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface LPReportListResponse {
  items: LPReport[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateLPReportRequest {
  portfolio_id?: string | null;
  report_period: string;
  period_start: string;
  period_end: string;
  cash_flows?: Array<{ date: string; amount: number }>;
  investments_data?: Partial<InvestmentDataItem>[];
  total_committed?: number | null;
  total_invested?: number | null;
  total_returned?: number | null;
  total_nav?: number | null;
}

export interface UpdateLPReportRequest {
  narrative?: Partial<LPReportNarrative> | null;
  investments_data?: Partial<InvestmentDataItem>[] | null;
  report_period?: string | null;
  period_start?: string | null;
  period_end?: string | null;
}

// ── Query key factories ─────────────────────────────────────────────────────

export const lpReportKeys = {
  all: ["lp-reports"] as const,
  list: (params?: { portfolio_id?: string; status?: string }) =>
    [...lpReportKeys.all, "list", params] as const,
  detail: (id: string) => [...lpReportKeys.all, "detail", id] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useLPReports(params?: { portfolio_id?: string; status?: string }) {
  return useQuery({
    queryKey: lpReportKeys.list(params),
    queryFn: async () => {
      const { data } = await api.get<LPReportListResponse>("/lp-reports", { params });
      return data;
    },
  });
}

export function useLPReport(id: string) {
  return useQuery({
    queryKey: lpReportKeys.detail(id),
    queryFn: async () => {
      const { data } = await api.get<LPReport>(`/lp-reports/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateLPReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateLPReportRequest) => {
      const { data } = await api.post<LPReport>("/lp-reports", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: lpReportKeys.all }),
  });
}

export function useUpdateLPReport(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: UpdateLPReportRequest) => {
      const { data } = await api.put<LPReport>(`/lp-reports/${id}`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: lpReportKeys.detail(id) });
      qc.invalidateQueries({ queryKey: lpReportKeys.all });
    },
  });
}

export function useApproveLPReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/lp-reports/${id}/approve`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: lpReportKeys.all }),
  });
}

export function useGenerateLPReportPDF() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<{ id: string; pdf_s3_key: string; download_url: string; generated_at: string }>(
        `/lp-reports/${id}/generate-pdf`
      );
      return data;
    },
    onSuccess: (_d, id) => qc.invalidateQueries({ queryKey: lpReportKeys.detail(id) }),
  });
}

// ── Formatting helpers ──────────────────────────────────────────────────────

export function formatMultiple(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(2)}x`;
}

export function formatIRR(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function lpReportStatusColor(status: string): string {
  switch (status) {
    case "approved": return "success";
    case "draft": return "neutral";
    case "generated": return "info";
    default: return "neutral";
  }
}
