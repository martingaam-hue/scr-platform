/**
 * Impact Measurement module — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export type ContributionLevel = "primary" | "secondary" | "co-benefit";
export type CarbonVerificationStatus =
  | "estimated"
  | "submitted"
  | "verified"
  | "issued"
  | "retired";

export interface SDGGoal {
  number: number;
  label: string;
  color: string;
  contribution_level: ContributionLevel;
  description: string;
}

export interface SDGSummary {
  project_id: string;
  project_name: string;
  goals: SDGGoal[];
}

export interface ImpactKPI {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  category: "energy" | "environment" | "social" | "economic";
}

export interface ProjectImpactResponse {
  project_id: string;
  project_name: string;
  project_type: string;
  geography_country: string;
  kpis: ImpactKPI[];
  sdg_goals: SDGGoal[];
  additionality_score: number;
  additionality_breakdown: Record<string, { score: number; max: number; rationale: string }>;
}

export interface PortfolioImpactResponse {
  total_projects: number;
  total_capacity_mw: number;
  total_co2_reduction_tco2e: number;
  total_jobs_created: number;
  total_households_served: number;
  total_carbon_credit_tons: number;
  sdg_coverage: number[];
  projects: ProjectImpactResponse[];
}

export interface CarbonCreditResponse {
  id: string;
  project_id: string;
  org_id: string;
  registry: string;
  methodology: string;
  vintage_year: number;
  quantity_tons: string;
  price_per_ton: string | null;
  currency: string;
  serial_number: string | null;
  verification_status: CarbonVerificationStatus;
  verification_body: string | null;
  issuance_date: string | null;
  retirement_date: string | null;
  created_at: string;
}

export interface CarbonCreditListResponse {
  items: CarbonCreditResponse[];
  total: number;
  total_estimated: number;
  total_verified: number;
  total_issued: number;
  total_retired: number;
}

export interface CarbonCreditCreateRequest {
  project_id: string;
  registry: string;
  methodology: string;
  vintage_year: number;
  quantity_tons: number;
  price_per_ton?: number;
  currency?: string;
  serial_number?: string;
  verification_status?: CarbonVerificationStatus;
  verification_body?: string;
  issuance_date?: string;
  retirement_date?: string;
}

export interface AdditionalityResponse {
  project_id: string;
  score: number;
  rating: "high" | "medium" | "low";
  breakdown: Record<string, { score: number; max: number; rationale: string }>;
  recommendations: string[];
}

// ── SDG metadata ───────────────────────────────────────────────────────────

export const SDG_METADATA: Record<number, { label: string; color: string }> = {
  1:  { label: "No Poverty",               color: "#e5243b" },
  2:  { label: "Zero Hunger",              color: "#dda63a" },
  3:  { label: "Good Health",              color: "#4c9f38" },
  4:  { label: "Quality Education",        color: "#c5192d" },
  5:  { label: "Gender Equality",          color: "#ff3a21" },
  6:  { label: "Clean Water",              color: "#26bde2" },
  7:  { label: "Affordable Energy",        color: "#fcc30b" },
  8:  { label: "Decent Work",              color: "#a21942" },
  9:  { label: "Industry & Innovation",    color: "#fd6925" },
  10: { label: "Reduced Inequalities",     color: "#dd1367" },
  11: { label: "Sustainable Cities",       color: "#fd9d24" },
  12: { label: "Responsible Consumption",  color: "#bf8b2e" },
  13: { label: "Climate Action",           color: "#3f7e44" },
  14: { label: "Life Below Water",         color: "#0a97d9" },
  15: { label: "Life on Land",             color: "#56c02b" },
  16: { label: "Peace & Justice",          color: "#00689d" },
  17: { label: "Partnerships",             color: "#19486a" },
};

export const CARBON_STATUS_LABELS: Record<CarbonVerificationStatus, string> = {
  estimated: "Estimated",
  submitted: "Submitted",
  verified:  "Verified",
  issued:    "Issued",
  retired:   "Retired",
};

// ── Query Keys ─────────────────────────────────────────────────────────────

export const impactKeys = {
  all: ["impact"] as const,
  portfolio: () => [...impactKeys.all, "portfolio"] as const,
  carbonCredits: (projectId?: string) =>
    [...impactKeys.all, "carbon-credits", projectId ?? "all"] as const,
  project: (projectId: string) =>
    [...impactKeys.all, "project", projectId] as const,
  sdg: (projectId: string) =>
    [...impactKeys.all, "sdg", projectId] as const,
  additionality: (projectId: string) =>
    [...impactKeys.all, "additionality", projectId] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function usePortfolioImpact() {
  return useQuery({
    queryKey: impactKeys.portfolio(),
    queryFn: () =>
      api.get<PortfolioImpactResponse>("/impact/portfolio").then((r) => r.data),
  });
}

export function useCarbonCredits(projectId?: string) {
  const params = projectId ? `?project_id=${projectId}` : "";
  return useQuery({
    queryKey: impactKeys.carbonCredits(projectId),
    queryFn: () =>
      api
        .get<CarbonCreditListResponse>(`/impact/carbon-credits${params}`)
        .then((r) => r.data),
  });
}

export function useCreateCarbonCredit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CarbonCreditCreateRequest) =>
      api
        .post<CarbonCreditResponse>("/impact/carbon-credits", data)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: impactKeys.carbonCredits() });
      qc.invalidateQueries({ queryKey: impactKeys.portfolio() });
    },
  });
}

export function useUpdateCarbonCredit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      creditId,
      ...data
    }: Partial<CarbonCreditCreateRequest> & { creditId: string }) =>
      api
        .put<CarbonCreditResponse>(`/impact/carbon-credits/${creditId}`, data)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: impactKeys.carbonCredits() });
    },
  });
}

export function useProjectImpact(projectId: string | undefined) {
  return useQuery({
    queryKey: impactKeys.project(projectId ?? ""),
    queryFn: () =>
      api
        .get<ProjectImpactResponse>(`/impact/projects/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useUpdateKPIs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      kpis,
    }: {
      projectId: string;
      kpis: Record<string, number | null>;
    }) =>
      api
        .put<ProjectImpactResponse>(`/impact/projects/${projectId}/kpis`, { kpis })
        .then((r) => r.data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: impactKeys.project(projectId) });
      qc.invalidateQueries({ queryKey: impactKeys.portfolio() });
    },
  });
}

export function useSDGMapping(projectId: string | undefined) {
  return useQuery({
    queryKey: impactKeys.sdg(projectId ?? ""),
    queryFn: () =>
      api.get<SDGSummary>(`/impact/projects/${projectId}/sdg`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useUpdateSDGMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      goals,
    }: {
      projectId: string;
      goals: Array<{ number: number; contribution_level: ContributionLevel; description: string }>;
    }) =>
      api
        .put<SDGSummary>(`/impact/projects/${projectId}/sdg`, { goals })
        .then((r) => r.data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: impactKeys.sdg(projectId) });
    },
  });
}

export function useAdditionality(projectId: string | undefined) {
  return useQuery({
    queryKey: impactKeys.additionality(projectId ?? ""),
    queryFn: () =>
      api
        .get<AdditionalityResponse>(`/impact/projects/${projectId}/additionality`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function additionalityColor(rating: string): string {
  if (rating === "high") return "text-green-600";
  if (rating === "medium") return "text-amber-600";
  return "text-red-500";
}

export function additionalityBadge(rating: string): "success" | "warning" | "error" {
  if (rating === "high") return "success";
  if (rating === "medium") return "warning";
  return "error";
}

export function carbonStatusVariant(
  status: CarbonVerificationStatus
): "success" | "warning" | "info" | "neutral" | "error" {
  if (status === "issued" || status === "verified") return "success";
  if (status === "submitted") return "info";
  if (status === "retired") return "neutral";
  return "warning";
}

export function formatNumber(n: number, decimals = 0): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(decimals);
}
