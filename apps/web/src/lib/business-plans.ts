/**
 * Business Plans CRUD — React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type BusinessPlanStatus = "draft" | "review" | "finalized";

export interface BusinessPlanRecord {
  id: string;
  org_id: string;
  project_id: string;
  created_by: string | null;
  title: string;
  executive_summary: string;
  financial_projections: Record<string, unknown> | null;
  market_analysis: Record<string, unknown> | null;
  risk_analysis: Record<string, unknown> | null;
  use_of_funds: string | null;
  team_section: string | null;
  risk_section: string | null;
  status: BusinessPlanStatus;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CreateBusinessPlanPayload {
  project_id: string;
  title: string;
  executive_summary?: string;
  financial_projections?: Record<string, unknown>;
  market_analysis?: Record<string, unknown>;
  risk_analysis?: Record<string, unknown>;
  use_of_funds?: string;
  team_section?: string;
  risk_section?: string;
  status?: BusinessPlanStatus;
}

export interface UpdateBusinessPlanPayload {
  title?: string;
  executive_summary?: string;
  financial_projections?: Record<string, unknown>;
  market_analysis?: Record<string, unknown>;
  risk_analysis?: Record<string, unknown>;
  use_of_funds?: string;
  team_section?: string;
  risk_section?: string;
  status?: BusinessPlanStatus;
}

// ── Query Keys ────────────────────────────────────────────────────────────────

export const businessPlanKeys = {
  all: ["business-plans"] as const,
  list: (projectId?: string) =>
    ["business-plans", "list", projectId] as const,
  detail: (planId: string) => ["business-plans", planId] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useBusinessPlans(projectId?: string) {
  return useQuery<BusinessPlanRecord[]>({
    queryKey: businessPlanKeys.list(projectId),
    queryFn: async () => {
      const params = projectId ? { project_id: projectId } : {};
      const { data } = await api.get<BusinessPlanRecord[]>("/business-plans", {
        params,
      });
      return data;
    },
  });
}

export function useBusinessPlan(planId: string) {
  return useQuery<BusinessPlanRecord>({
    queryKey: businessPlanKeys.detail(planId),
    queryFn: async () => {
      const { data } = await api.get<BusinessPlanRecord>(
        `/business-plans/${planId}`
      );
      return data;
    },
    enabled: !!planId,
  });
}

export function useCreateBusinessPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateBusinessPlanPayload) => {
      const { data } = await api.post<BusinessPlanRecord>(
        "/business-plans",
        payload
      );
      return data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: businessPlanKeys.all }),
  });
}

export function useUpdateBusinessPlan(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateBusinessPlanPayload) => {
      const { data } = await api.patch<BusinessPlanRecord>(
        `/business-plans/${planId}`,
        payload
      );
      return data;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: businessPlanKeys.all }),
  });
}

export function useDeleteBusinessPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (planId: string) => {
      await api.delete(`/business-plans/${planId}`);
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: businessPlanKeys.all }),
  });
}
