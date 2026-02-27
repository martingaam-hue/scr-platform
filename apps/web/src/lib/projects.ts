/**
 * Projects types and React Query hooks.
 *
 * Types mirror the FastAPI Pydantic schemas. Hooks wrap axios calls
 * with React Query for caching, optimistic updates, and pagination.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Enums ──────────────────────────────────────────────────────────────────

export type ProjectType =
  | "solar"
  | "wind"
  | "hydro"
  | "biomass"
  | "geothermal"
  | "storage"
  | "hydrogen"
  | "nuclear"
  | "grid"
  | "efficiency"
  | "carbon_capture"
  | "nature_based"
  | "other";

export type ProjectStatus =
  | "draft"
  | "active"
  | "fundraising"
  | "funded"
  | "construction"
  | "operational"
  | "decommissioned"
  | "on_hold"
  | "cancelled";

export type ProjectStage =
  | "concept"
  | "pre_feasibility"
  | "feasibility"
  | "development"
  | "permitting"
  | "financing"
  | "construction"
  | "commissioning"
  | "operational";

export type MilestoneStatus =
  | "not_started"
  | "in_progress"
  | "completed"
  | "delayed"
  | "blocked";

export type BudgetItemStatus =
  | "planned"
  | "committed"
  | "spent"
  | "over_budget";

// ── Types ──────────────────────────────────────────────────────────────────

export interface SignalScoreResponse {
  overall_score: number;
  technical_score: number;
  financial_score: number;
  esg_score: number;
  regulatory_score: number;
  team_score: number;
  gaps: Record<string, unknown> | null;
  strengths: Record<string, unknown> | null;
  model_used: string;
  version: number;
  calculated_at: string;
}

export interface ProjectResponse {
  id: string;
  name: string;
  slug: string;
  description: string;
  project_type: ProjectType;
  status: ProjectStatus;
  stage: ProjectStage;
  geography_country: string;
  geography_region: string;
  geography_coordinates: Record<string, unknown> | null;
  technology_details: Record<string, unknown> | null;
  capacity_mw: string | null;
  total_investment_required: string;
  currency: string;
  target_close_date: string | null;
  cover_image_url: string | null;
  is_published: boolean;
  published_at: string | null;
  latest_signal_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetailResponse extends ProjectResponse {
  milestone_count: number;
  budget_item_count: number;
  document_count: number;
  latest_signal: SignalScoreResponse | null;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectStatsResponse {
  total_projects: number;
  active_fundraising: number;
  total_funding_needed: string;
  avg_signal_score: number | null;
}

export interface MilestoneResponse {
  id: string;
  project_id: string;
  name: string;
  description: string;
  target_date: string;
  completed_date: string | null;
  status: MilestoneStatus;
  completion_pct: number;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetItemResponse {
  id: string;
  project_id: string;
  category: string;
  description: string;
  estimated_amount: string;
  actual_amount: string | null;
  currency: string;
  status: BudgetItemStatus;
  created_at: string;
  updated_at: string;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export interface ProjectListParams {
  status?: ProjectStatus;
  type?: ProjectType;
  stage?: ProjectStage;
  geography?: string;
  score_min?: number;
  score_max?: number;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const projectKeys = {
  all: ["projects"] as const,
  list: (params: ProjectListParams) =>
    [...projectKeys.all, "list", params] as const,
  detail: (id: string) => [...projectKeys.all, "detail", id] as const,
  stats: () => [...projectKeys.all, "stats"] as const,
  milestones: (projectId: string) =>
    [...projectKeys.all, "milestones", projectId] as const,
  budget: (projectId: string) =>
    [...projectKeys.all, "budget", projectId] as const,
};

// ── Project hooks ──────────────────────────────────────────────────────────

export function useProjects(params: ProjectListParams = {}) {
  return useQuery({
    queryKey: projectKeys.list(params),
    queryFn: () =>
      api
        .get<ProjectListResponse>("/projects", { params })
        .then((r) => r.data),
  });
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: projectKeys.detail(id ?? ""),
    queryFn: () =>
      api
        .get<ProjectDetailResponse>(`/projects/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function useProjectStats() {
  return useQuery({
    queryKey: projectKeys.stats(),
    queryFn: () =>
      api
        .get<ProjectStatsResponse>("/projects/stats")
        .then((r) => r.data),
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      project_type: ProjectType;
      description?: string;
      geography_country: string;
      geography_region?: string;
      geography_coordinates?: Record<string, unknown>;
      technology_details?: Record<string, unknown>;
      capacity_mw?: string;
      total_investment_required: string;
      currency?: string;
      target_close_date?: string;
      stage?: ProjectStage;
      status?: ProjectStatus;
    }) =>
      api.post<ProjectResponse>("/projects", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      ...body
    }: {
      projectId: string;
      name?: string;
      description?: string;
      project_type?: ProjectType;
      status?: ProjectStatus;
      stage?: ProjectStage;
      geography_country?: string;
      geography_region?: string;
      geography_coordinates?: Record<string, unknown>;
      technology_details?: Record<string, unknown>;
      capacity_mw?: string;
      total_investment_required?: string;
      currency?: string;
      target_close_date?: string;
    }) =>
      api
        .put<ProjectResponse>(`/projects/${projectId}`, body)
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.detail(vars.projectId),
      });
      qc.invalidateQueries({
        queryKey: [...projectKeys.all, "list"],
      });
      qc.invalidateQueries({ queryKey: projectKeys.stats() });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api.delete(`/projects/${projectId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function usePublishProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api
        .put<ProjectResponse>(`/projects/${projectId}/publish`)
        .then((r) => r.data),
    onSuccess: (_data, projectId) => {
      qc.invalidateQueries({
        queryKey: projectKeys.detail(projectId),
      });
      qc.invalidateQueries({
        queryKey: [...projectKeys.all, "list"],
      });
    },
  });
}

// ── Milestone hooks ────────────────────────────────────────────────────────

export function useMilestones(projectId: string | undefined) {
  return useQuery({
    queryKey: projectKeys.milestones(projectId ?? ""),
    queryFn: () =>
      api
        .get<MilestoneResponse[]>(`/projects/${projectId}/milestones`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateMilestone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      ...body
    }: {
      projectId: string;
      name: string;
      description?: string;
      target_date: string;
      order_index?: number;
    }) =>
      api
        .post<MilestoneResponse>(
          `/projects/${projectId}/milestones`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.milestones(vars.projectId),
      });
      qc.invalidateQueries({
        queryKey: projectKeys.detail(vars.projectId),
      });
    },
  });
}

export function useUpdateMilestone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      milestoneId,
      ...body
    }: {
      projectId: string;
      milestoneId: string;
      name?: string;
      description?: string;
      target_date?: string;
      completed_date?: string;
      status?: MilestoneStatus;
      completion_pct?: number;
      order_index?: number;
    }) =>
      api
        .put<MilestoneResponse>(
          `/projects/${projectId}/milestones/${milestoneId}`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.milestones(vars.projectId),
      });
    },
  });
}

export function useDeleteMilestone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      milestoneId,
    }: {
      projectId: string;
      milestoneId: string;
    }) =>
      api.delete(
        `/projects/${projectId}/milestones/${milestoneId}`
      ),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.milestones(vars.projectId),
      });
      qc.invalidateQueries({
        queryKey: projectKeys.detail(vars.projectId),
      });
    },
  });
}

// ── Budget hooks ───────────────────────────────────────────────────────────

export function useBudgetItems(projectId: string | undefined) {
  return useQuery({
    queryKey: projectKeys.budget(projectId ?? ""),
    queryFn: () =>
      api
        .get<BudgetItemResponse[]>(`/projects/${projectId}/budget`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateBudgetItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      ...body
    }: {
      projectId: string;
      category: string;
      description?: string;
      estimated_amount: string;
      currency?: string;
    }) =>
      api
        .post<BudgetItemResponse>(
          `/projects/${projectId}/budget`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.budget(vars.projectId),
      });
      qc.invalidateQueries({
        queryKey: projectKeys.detail(vars.projectId),
      });
    },
  });
}

export function useUpdateBudgetItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      budgetId,
      ...body
    }: {
      projectId: string;
      budgetId: string;
      category?: string;
      description?: string;
      estimated_amount?: string;
      actual_amount?: string;
      currency?: string;
      status?: BudgetItemStatus;
    }) =>
      api
        .put<BudgetItemResponse>(
          `/projects/${projectId}/budget/${budgetId}`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.budget(vars.projectId),
      });
    },
  });
}

export function useDeleteBudgetItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      budgetId,
    }: {
      projectId: string;
      budgetId: string;
    }) =>
      api.delete(`/projects/${projectId}/budget/${budgetId}`),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: projectKeys.budget(vars.projectId),
      });
      qc.invalidateQueries({
        queryKey: projectKeys.detail(vars.projectId),
      });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

const PROJECT_TYPE_ICONS: Record<ProjectType, string> = {
  solar: "Sun",
  wind: "Wind",
  hydro: "Droplets",
  biomass: "Leaf",
  geothermal: "Flame",
  storage: "Battery",
  hydrogen: "Atom",
  nuclear: "Radiation",
  grid: "Network",
  efficiency: "Gauge",
  carbon_capture: "CloudOff",
  nature_based: "TreePine",
  other: "Boxes",
};

export function projectTypeIcon(type: ProjectType): string {
  return PROJECT_TYPE_ICONS[type] ?? "Boxes";
}

const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  solar: "Solar",
  wind: "Wind",
  hydro: "Hydropower",
  biomass: "Biomass",
  geothermal: "Geothermal",
  storage: "Energy Storage",
  hydrogen: "Hydrogen",
  nuclear: "Nuclear",
  grid: "Grid Infrastructure",
  efficiency: "Energy Efficiency",
  carbon_capture: "Carbon Capture",
  nature_based: "Nature-Based",
  other: "Other",
};

export function projectTypeLabel(type: ProjectType): string {
  return PROJECT_TYPE_LABELS[type] ?? type;
}

export function projectStatusColor(
  status: ProjectStatus
): "neutral" | "success" | "warning" | "error" | "info" {
  switch (status) {
    case "operational":
    case "funded":
      return "success";
    case "fundraising":
    case "construction":
      return "warning";
    case "cancelled":
    case "decommissioned":
      return "error";
    case "active":
    case "draft":
      return "info";
    default:
      return "neutral";
  }
}

const STAGE_LABELS: Record<ProjectStage, string> = {
  concept: "Concept",
  pre_feasibility: "Pre-Feasibility",
  feasibility: "Feasibility",
  development: "Development",
  permitting: "Permitting",
  financing: "Financing",
  construction: "Construction",
  commissioning: "Commissioning",
  operational: "Operational",
};

export function stageLabel(stage: ProjectStage): string {
  return STAGE_LABELS[stage] ?? stage;
}

export function formatCurrency(
  amount: string | number,
  currency = "USD"
): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}
