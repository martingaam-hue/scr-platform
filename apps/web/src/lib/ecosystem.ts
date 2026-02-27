/**
 * Ecosystem types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface StakeholderNode {
  id: string;
  name: string;
  type: string; // investor, ally, advisor, regulator, partner, supplier, community
  sub_type: string | null;
  relationship_strength: number; // 1–5
  engagement_status: string;     // active, passive, at_risk, churned
  tags: string[];
  metadata: Record<string, unknown> | null;
}

export interface StakeholderEdge {
  source: string;
  target: string;
  relationship_type: string; // investment, partnership, advisory, regulatory, supply_chain
  weight: number;            // 1–10
  description: string | null;
}

export interface EcosystemMap {
  project_id: string | null;
  org_id: string;
  nodes: StakeholderNode[];
  edges: StakeholderEdge[];
  summary: Record<string, unknown>; // {total_stakeholders, by_type, avg_strength}
  last_updated: string;
}

export interface StakeholderCreate {
  name: string;
  type: string;
  sub_type?: string;
  relationship_strength?: number;
  engagement_status?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface RelationshipCreate {
  source_id: string;
  target_id: string;
  relationship_type: string;
  weight?: number;
  description?: string;
}

// ── Query key factory ────────────────────────────────────────────────────────

export const ecosystemKeys = {
  all: ["ecosystem"] as const,
  org: () => [...ecosystemKeys.all, "org"] as const,
  project: (id: string) => [...ecosystemKeys.all, id] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

/** Get the organisation-level ecosystem map. */
export function useEcosystem(projectId?: string) {
  return useQuery({
    queryKey: projectId
      ? ecosystemKeys.project(projectId)
      : ecosystemKeys.org(),
    queryFn: () =>
      api
        .get<EcosystemMap>(
          projectId ? `/ecosystem/${projectId}` : "/ecosystem",
        )
        .then((r) => r.data),
  });
}

export function useAddStakeholder(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: StakeholderCreate) =>
      api
        .post<EcosystemMap>(`/ecosystem/${projectId}/stakeholders`, body)
        .then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData(ecosystemKeys.project(projectId), data);
    },
  });
}

export function useAddRelationship(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RelationshipCreate) =>
      api
        .post<EcosystemMap>(`/ecosystem/${projectId}/relationships`, body)
        .then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData(ecosystemKeys.project(projectId), data);
    },
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function stakeholderTypeColor(type: string): string {
  switch (type) {
    case "investor":
      return "bg-blue-100 text-blue-800";
    case "ally":
      return "bg-green-100 text-green-800";
    case "advisor":
      return "bg-purple-100 text-purple-800";
    case "regulator":
      return "bg-orange-100 text-orange-800";
    case "partner":
      return "bg-teal-100 text-teal-800";
    case "supplier":
      return "bg-yellow-100 text-yellow-800";
    case "community":
      return "bg-pink-100 text-pink-800";
    default:
      return "bg-neutral-100 text-neutral-800";
  }
}

export function engagementStatusColor(status: string): string {
  switch (status) {
    case "active":
      return "text-green-600";
    case "passive":
      return "text-neutral-500";
    case "at_risk":
      return "text-amber-600";
    case "churned":
      return "text-red-600";
    default:
      return "text-neutral-500";
  }
}

export const STAKEHOLDER_TYPES = [
  "investor",
  "ally",
  "advisor",
  "regulator",
  "partner",
  "supplier",
  "community",
];

export const RELATIONSHIP_TYPES = [
  "investment",
  "partnership",
  "advisory",
  "regulatory",
  "supply_chain",
];
