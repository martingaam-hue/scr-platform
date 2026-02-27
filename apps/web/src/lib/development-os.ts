/**
 * Development OS types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface Milestone {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  completed_date: string | null;
  status: string; // not_started, in_progress, completed, delayed, blocked
  created_at: string;
  updated_at: string;
}

export interface ConstructionPhase {
  phase_name: string;
  start_date: string | null;
  end_date: string | null;
  completion_pct: number;
  milestones: Milestone[];
  status: string; // not_started, in_progress, completed
}

export interface ProcurementItem {
  id: string;
  name: string;
  vendor: string | null;
  category: string;
  estimated_cost_usd: number | null;
  status: string; // pending, rfq_sent, negotiating, contracted, delivered
  delivery_date: string | null;
  notes: string | null;
}

export interface DevelopmentOSData {
  project_id: string;
  project_name: string;
  project_stage: string;
  overall_completion_pct: number;
  phases: ConstructionPhase[];
  procurement: ProcurementItem[];
  next_milestone: Milestone | null;
  days_to_next_milestone: number | null;
  last_updated: string;
}

export interface MilestoneCreate {
  title: string;
  description?: string;
  due_date?: string;
  status?: string;
}

export interface MilestoneUpdate {
  title?: string;
  description?: string;
  due_date?: string;
  completed_date?: string;
  status?: string;
}

// ── Query key factory ────────────────────────────────────────────────────────

export const devOsKeys = {
  all: ["development-os"] as const,
  overview: (projectId: string) =>
    [...devOsKeys.all, projectId, "overview"] as const,
  milestones: (projectId: string) =>
    [...devOsKeys.all, projectId, "milestones"] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useDevelopmentOS(projectId?: string) {
  return useQuery({
    queryKey: devOsKeys.overview(projectId ?? ""),
    queryFn: () =>
      api
        .get<DevelopmentOSData>(`/development-os/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useMilestones(projectId?: string) {
  return useQuery({
    queryKey: devOsKeys.milestones(projectId ?? ""),
    queryFn: () =>
      api
        .get<Milestone[]>(`/development-os/${projectId}/milestones`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateMilestone(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: MilestoneCreate) =>
      api
        .post<Milestone>(`/development-os/${projectId}/milestones`, body)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: devOsKeys.milestones(projectId),
      });
      queryClient.invalidateQueries({
        queryKey: devOsKeys.overview(projectId),
      });
    },
  });
}

export function useUpdateMilestone(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      milestoneId,
      body,
    }: {
      milestoneId: string;
      body: MilestoneUpdate;
    }) =>
      api
        .put<Milestone>(`/development-os/milestones/${milestoneId}`, body)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: devOsKeys.milestones(projectId),
      });
      queryClient.invalidateQueries({
        queryKey: devOsKeys.overview(projectId),
      });
    },
  });
}

export function useDeleteMilestone(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (milestoneId: string) =>
      api.delete(`/development-os/milestones/${milestoneId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: devOsKeys.milestones(projectId),
      });
      queryClient.invalidateQueries({
        queryKey: devOsKeys.overview(projectId),
      });
    },
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function milestoneStatusColor(status: string): string {
  switch (status) {
    case "completed":
      return "text-green-600";
    case "in_progress":
      return "text-blue-600";
    case "delayed":
      return "text-red-600";
    case "blocked":
      return "text-orange-600";
    default:
      return "text-neutral-500";
  }
}

export function milestoneStatusLabel(status: string): string {
  switch (status) {
    case "not_started":
      return "Not Started";
    case "in_progress":
      return "In Progress";
    case "completed":
      return "Completed";
    case "delayed":
      return "Delayed";
    case "blocked":
      return "Blocked";
    default:
      return status;
  }
}

export function procurementStatusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "rfq_sent":
      return "RFQ Sent";
    case "negotiating":
      return "Negotiating";
    case "contracted":
      return "Contracted";
    case "delivered":
      return "Delivered";
    default:
      return status;
  }
}
