/**
 * Investor Matching types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface AlignmentBreakdown {
  overall: number;
  sector: number;
  geography: number;
  ticket_size: number;
  stage: number;
  risk_return: number;
  esg: number;
  breakdown: Record<string, unknown>;
}

export const ALIGNMENT_DIMENSIONS = [
  { key: "sector",      label: "Sector",       max: 25 },
  { key: "geography",   label: "Geography",    max: 20 },
  { key: "ticket_size", label: "Ticket Size",  max: 20 },
  { key: "stage",       label: "Stage",        max: 15 },
  { key: "risk_return", label: "Risk/Return",  max: 10 },
  { key: "esg",         label: "ESG",          max: 10 },
] as const;

export type DimensionKey = (typeof ALIGNMENT_DIMENSIONS)[number]["key"];

export interface RecommendedProject {
  match_id: string | null;
  project_id: string;
  project_name: string;
  project_type: string;
  geography_country: string;
  stage: string;
  total_investment_required: string;
  currency: string;
  cover_image_url: string | null;
  signal_score: number | null;
  alignment: AlignmentBreakdown;
  status: string;
  mandate_id: string | null;
  mandate_name: string | null;
  updated_at: string | null;
}

export interface InvestorRecommendations {
  items: RecommendedProject[];
  total: number;
}

export interface MatchingInvestor {
  match_id: string | null;
  investor_org_id: string;
  investor_name: string;
  logo_url: string | null;
  mandate_id: string | null;
  mandate_name: string | null;
  ticket_size_min: string;
  ticket_size_max: string;
  sectors: string[];
  geographies: string[];
  risk_tolerance: string;
  alignment: AlignmentBreakdown;
  status: string;
  initiated_by: string | null;
  updated_at: string | null;
}

export interface AllyRecommendations {
  project_id: string;
  project_name: string;
  items: MatchingInvestor[];
  total: number;
}

export interface MatchMessage {
  id: string;
  match_id: string;
  sender_id: string;
  content: string;
  is_system: boolean;
  created_at: string;
}

export interface MessagesResponse {
  items: MatchMessage[];
  total: number;
}

export interface MatchStatusResponse {
  match_id: string;
  status: string;
  updated_at: string;
}

export interface Mandate {
  id: string;
  org_id: string;
  name: string;
  sectors: string[] | null;
  geographies: string[] | null;
  stages: string[] | null;
  ticket_size_min: string;
  ticket_size_max: string;
  target_irr_min: string | null;
  risk_tolerance: string;
  esg_requirements: Record<string, unknown> | null;
  exclusions: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MandateCreate {
  name: string;
  sectors?: string[];
  geographies?: string[];
  stages?: string[];
  ticket_size_min: number;
  ticket_size_max: number;
  target_irr_min?: number;
  risk_tolerance?: string;
  esg_requirements?: Record<string, unknown>;
  exclusions?: Record<string, unknown>;
  is_active?: boolean;
}

export interface MandateUpdate extends Partial<MandateCreate> {}

export interface RecommendParams {
  sector?: string;
  geography?: string;
  min_alignment?: number;
  sort_by?: "alignment" | "signal_score" | "recency";
}

// ── Query Keys ─────────────────────────────────────────────────────────────

export const matchingKeys = {
  all: ["matching"] as const,
  investorRecs: (params?: RecommendParams) =>
    [...matchingKeys.all, "investor-recs", params ?? {}] as const,
  allyRecs: (projectId: string) =>
    [...matchingKeys.all, "ally-recs", projectId] as const,
  messages: (matchId: string) =>
    [...matchingKeys.all, "messages", matchId] as const,
  mandates: () => [...matchingKeys.all, "mandates"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useInvestorRecommendations(params?: RecommendParams) {
  const qs = new URLSearchParams();
  if (params?.sector) qs.set("sector", params.sector);
  if (params?.geography) qs.set("geography", params.geography);
  if (params?.min_alignment != null)
    qs.set("min_alignment", String(params.min_alignment));
  if (params?.sort_by) qs.set("sort_by", params.sort_by);

  return useQuery({
    queryKey: matchingKeys.investorRecs(params),
    queryFn: () =>
      api
        .get<InvestorRecommendations>(
          `/matching/investor/recommendations${qs.toString() ? `?${qs}` : ""}`
        )
        .then((r) => r.data),
  });
}

export function useAllyRecommendations(projectId: string | undefined) {
  return useQuery({
    queryKey: matchingKeys.allyRecs(projectId ?? ""),
    queryFn: () =>
      api
        .get<AllyRecommendations>(
          `/matching/ally/recommendations/${projectId}`
        )
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useMatchMessages(matchId: string | undefined) {
  return useQuery({
    queryKey: matchingKeys.messages(matchId ?? ""),
    queryFn: () =>
      api
        .get<MessagesResponse>(`/matching/${matchId}/messages`)
        .then((r) => r.data),
    enabled: !!matchId,
    refetchInterval: 10_000, // poll every 10s for new messages
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ matchId, content }: { matchId: string; content: string }) =>
      api
        .post<MatchMessage>(`/matching/${matchId}/messages`, { content })
        .then((r) => r.data),
    onSuccess: (_data, { matchId }) => {
      qc.invalidateQueries({ queryKey: matchingKeys.messages(matchId) });
    },
  });
}

export function useExpressInterest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: string) =>
      api
        .post<MatchStatusResponse>(`/matching/${matchId}/interest`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matchingKeys.all });
    },
  });
}

export function useRequestIntro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: string) =>
      api
        .post<MatchStatusResponse>(`/matching/${matchId}/request-intro`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matchingKeys.all });
    },
  });
}

export function useUpdateMatchStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      matchId,
      status,
      notes,
    }: {
      matchId: string;
      status: string;
      notes?: string;
    }) =>
      api
        .put<MatchStatusResponse>(`/matching/${matchId}/status`, {
          status,
          notes,
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matchingKeys.all });
    },
  });
}

export function useMandates() {
  return useQuery({
    queryKey: matchingKeys.mandates(),
    queryFn: () =>
      api.get<Mandate[]>("/matching/mandates").then((r) => r.data),
  });
}

export function useCreateMandate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MandateCreate) =>
      api.post<Mandate>("/matching/mandates", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matchingKeys.mandates() });
    },
  });
}

export function useUpdateMandate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: MandateUpdate & { id: string }) =>
      api.put<Mandate>(`/matching/mandates/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matchingKeys.mandates() });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function alignmentColor(score: number): string {
  if (score >= 70) return "text-green-600";
  if (score >= 45) return "text-amber-600";
  return "text-red-500";
}

export function alignmentBarColor(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 45) return "bg-amber-400";
  return "bg-red-400";
}

export function statusLabel(s: string): string {
  const map: Record<string, string> = {
    new: "New",
    suggested: "Suggested",
    viewed: "Viewed",
    interested: "Interested",
    intro_requested: "Intro Requested",
    engaged: "Engaged",
    passed: "Passed",
    declined: "Declined",
  };
  return map[s] ?? s;
}

export function statusVariant(
  s: string
): "success" | "warning" | "error" | "neutral" | "info" {
  switch (s) {
    case "engaged":        return "success";
    case "interested":
    case "intro_requested":return "info";
    case "passed":
    case "declined":       return "error";
    case "viewed":         return "warning";
    default:               return "neutral";
  }
}

export const PIPELINE_STAGES = [
  { value: "suggested",       label: "Suggested" },
  { value: "viewed",          label: "Viewed" },
  { value: "interested",      label: "Interested" },
  { value: "intro_requested", label: "Intro Requested" },
  { value: "engaged",         label: "Engaged" },
  { value: "passed",          label: "Passed" },
] as const;

export const PROJECT_TYPE_LABELS: Record<string, string> = {
  solar: "Solar",
  wind: "Wind",
  hydro: "Hydro",
  biomass: "Biomass",
  geothermal: "Geothermal",
  energy_efficiency: "Energy Efficiency",
  green_building: "Green Building",
  sustainable_agriculture: "Sustainable Agri.",
  other: "Other",
};
