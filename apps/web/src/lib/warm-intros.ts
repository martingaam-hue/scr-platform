"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Connection {
  id: string;
  connection_type: string;
  connected_org_name: string;
  connected_person_name: string | null;
  connected_person_email: string | null;
  relationship_strength: string;
  last_interaction_date: string | null;
  notes: string | null;
  created_at: string;
}

export interface IntroPath {
  type: string;
  connector_org: string;
  connector_person: string | null;
  connection_type: string;
  warmth: number;
}

export interface ConnectionsResponse {
  connections: Connection[];
  total: number;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useConnections() {
  return useQuery<ConnectionsResponse>({
    queryKey: ["warm-intros-connections"],
    queryFn: () => api.get("/warm-intros/connections").then((r) => r.data),
  });
}

export function useAddConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/warm-intros/connections", body).then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["warm-intros-connections"] }),
  });
}

export function useDeleteConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/warm-intros/connections/${id}`).then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["warm-intros-connections"] }),
  });
}

export function useIntroPath() {
  return useMutation({
    mutationFn: (investorId: string) =>
      api
        .get(`/warm-intros/paths/${investorId}`)
        .then((r) => r.data as { paths: IntroPath[] }),
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const STRENGTH_BADGE: Record<string, string> = {
  strong: "bg-green-100 text-green-700",
  moderate: "bg-yellow-100 text-yellow-700",
  weak: "bg-gray-100 text-gray-600",
};

export function warmthColor(score: number): string {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-yellow-600";
  return "text-gray-500";
}

export function warmthBg(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-gray-400";
}

export const CONNECTION_TYPES = [
  "advisor",
  "co_investor",
  "service_provider",
  "board_member",
  "lp_relationship",
];
