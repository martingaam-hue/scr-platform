import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// Types mirroring backend schemas
export interface AdvisorProfile {
  id: string;
  user_id: string;
  org_id: string;
  expertise_areas: Record<string, unknown> | null;
  industry_experience: Record<string, unknown> | null;
  board_positions_held: number;
  availability_status: string;
  compensation_preference: string;
  bio: string;
  linkedin_url: string | null;
  verified: boolean;
  match_count: number;
  avg_rating: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdvisorSearchResult {
  id: string;
  user_id: string;
  expertise_areas: Record<string, unknown> | null;
  availability_status: string;
  compensation_preference: string;
  bio: string;
  verified: boolean;
  board_positions_held: number;
  avg_rating: number | null;
  match_score: number;
}

export interface AdvisorApplication {
  id: string;
  project_id: string;
  advisor_profile_id: string;
  ally_org_id: string;
  status: string;
  message: string | null;
  role_offered: string;
  equity_offered: number | null;
  compensation_terms: Record<string, unknown> | null;
  signal_score_impact: number | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  project_id: string;
  role_offered: string;
  message?: string;
  equity_offered?: number;
}

// Query key factory
export const advisorKeys = {
  all: ["board-advisors"] as const,
  search: (params: object) => [...advisorKeys.all, "search", params] as const,
  profile: () => [...advisorKeys.all, "my-profile"] as const,
  applications: (projectId?: string) =>
    [...advisorKeys.all, "applications", projectId ?? "all"] as const,
};

// Hooks

export function useAdvisorSearch(expertise?: string, availability?: string) {
  return useQuery({
    queryKey: advisorKeys.search({ expertise, availability }),
    queryFn: () =>
      api
        .get<AdvisorSearchResult[]>("/board-advisors/search", {
          params: { expertise, availability },
        })
        .then((r) => r.data),
  });
}

export function useMyAdvisorProfile() {
  return useQuery({
    queryKey: advisorKeys.profile(),
    queryFn: () =>
      api.get<AdvisorProfile>("/board-advisors/my-profile").then((r) => r.data),
  });
}

export function useCreateAdvisorProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<AdvisorProfile>) =>
      api
        .post<AdvisorProfile>("/board-advisors/my-profile", body)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: advisorKeys.profile() }),
  });
}

export function useUpdateAdvisorProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<AdvisorProfile>) =>
      api
        .put<AdvisorProfile>("/board-advisors/my-profile", body)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: advisorKeys.profile() }),
  });
}

export function useAdvisorApplications(projectId?: string) {
  return useQuery({
    queryKey: advisorKeys.applications(projectId),
    queryFn: () =>
      api
        .get<AdvisorApplication[]>("/board-advisors/applications", {
          params: projectId ? { project_id: projectId } : undefined,
        })
        .then((r) => r.data),
  });
}

export function useApplyAsAdvisor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ApplicationCreate) =>
      api
        .post<AdvisorApplication>("/board-advisors/apply", body)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: advisorKeys.all }),
  });
}

export function useUpdateApplicationStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      applicationId,
      status,
      notes,
    }: {
      applicationId: string;
      status: string;
      notes?: string;
    }) =>
      api
        .put<AdvisorApplication>(
          `/board-advisors/applications/${applicationId}/status`,
          { status, notes }
        )
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: advisorKeys.all }),
  });
}

// Helpers

export const AVAILABILITY_LABELS: Record<string, string> = {
  available: "Available",
  limited: "Limited",
  unavailable: "Not Available",
  // legacy values
  busy: "Busy",
  not_available: "Not Available",
};

export const APPLICATION_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  active: "Active",
  completed: "Completed",
};

export function applicationStatusBadge(
  status: string
): "neutral" | "warning" | "success" | "error" {
  switch (status) {
    case "accepted":
    case "active":
    case "completed":
      return "success";
    case "rejected":
      return "error";
    default:
      return "neutral";
  }
}
