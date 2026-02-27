import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface InvestorPersona {
  id: string;
  org_id: string;
  persona_name: string;
  is_active: boolean;
  strategy_type: string;
  target_irr_min: number | null;
  target_irr_max: number | null;
  target_moic_min: number | null;
  preferred_asset_types: string[] | null;
  preferred_geographies: string[] | null;
  preferred_stages: string[] | null;
  ticket_size_min: number | null;
  ticket_size_max: number | null;
  esg_requirements: Record<string, unknown> | null;
  risk_tolerance: Record<string, unknown> | null;
  co_investment_preference: boolean;
  fund_structure_preference: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface PersonaMatch {
  project_id: string;
  project_name: string;
  project_type: string;
  geography_country: string;
  stage: string;
  investment_required: string;
  alignment_score: number;
  alignment_reasons: string[];
}

export const personaKeys = {
  all: ["investor-personas"] as const,
  list: () => [...personaKeys.all, "list"] as const,
  one: (id: string) => [...personaKeys.all, id] as const,
  matches: (id: string) => [...personaKeys.all, id, "matches"] as const,
};

export function useInvestorPersonas() {
  return useQuery({
    queryKey: personaKeys.list(),
    queryFn: () =>
      api.get<InvestorPersona[]>("/investor-personas").then((r) => r.data),
  });
}

export function useInvestorPersona(id?: string) {
  return useQuery({
    queryKey: personaKeys.one(id ?? ""),
    queryFn: () =>
      api
        .get<InvestorPersona>(`/investor-personas/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function usePersonaMatches(id?: string) {
  return useQuery({
    queryKey: personaKeys.matches(id ?? ""),
    queryFn: () =>
      api
        .get<PersonaMatch[]>(`/investor-personas/${id}/matches`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<InvestorPersona>) =>
      api
        .post<InvestorPersona>("/investor-personas", body)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: personaKeys.list() }),
  });
}

export function useGeneratePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (description: string) =>
      api
        .post<InvestorPersona>("/investor-personas/generate", { description })
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: personaKeys.list() }),
  });
}

export function useUpdatePersona(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<InvestorPersona>) =>
      api
        .put<InvestorPersona>(`/investor-personas/${id}`, body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: personaKeys.list() });
      qc.invalidateQueries({ queryKey: personaKeys.one(id) });
    },
  });
}

export const STRATEGY_LABELS: Record<string, string> = {
  conservative: "Conservative",
  moderate: "Moderate",
  growth: "Growth",
  aggressive: "Aggressive",
  impact_first: "Impact First",
};

export function strategyColor(strategy: string): string {
  switch (strategy) {
    case "conservative":
      return "text-blue-600";
    case "aggressive":
      return "text-red-600";
    case "impact_first":
      return "text-green-600";
    case "growth":
      return "text-purple-600";
    default:
      return "text-amber-600";
  }
}
