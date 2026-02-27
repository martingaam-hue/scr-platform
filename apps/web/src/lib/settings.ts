/**
 * Settings module — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export type OrgType = "investor" | "ally" | "admin";
export type SubscriptionTier = "foundation" | "professional" | "enterprise";
export type SubscriptionStatus = "active" | "trial" | "suspended" | "cancelled";
export type UserRole = "admin" | "manager" | "analyst" | "viewer";
export type DigestFrequency = "never" | "daily" | "weekly";

export interface OrgResponse {
  id: string;
  name: string;
  slug: string;
  type: OrgType;
  logo_url: string | null;
  settings: Record<string, unknown>;
  subscription_tier: SubscriptionTier;
  subscription_status: SubscriptionStatus;
  created_at: string;
}

export interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  avatar_url: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TeamListResponse {
  items: TeamMember[];
  total: number;
}

export interface InviteUserRequest {
  email: string;
  full_name: string;
  role: UserRole;
}

export interface ApiKeyItem {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyListResponse {
  items: ApiKeyItem[];
}

export interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  key: string;
  created_at: string;
}

export interface NotificationPreferences {
  email_match_alerts: boolean;
  email_project_updates: boolean;
  email_report_ready: boolean;
  email_weekly_digest: boolean;
  in_app_mentions: boolean;
  in_app_match_alerts: boolean;
  in_app_status_changes: boolean;
  digest_frequency: DigestFrequency;
}

export interface PreferencesResponse {
  notification: NotificationPreferences;
  raw: Record<string, unknown>;
}

// ── Query Keys ─────────────────────────────────────────────────────────────

export const settingsKeys = {
  all: ["settings"] as const,
  org: () => [...settingsKeys.all, "org"] as const,
  team: () => [...settingsKeys.all, "team"] as const,
  apiKeys: () => [...settingsKeys.all, "api-keys"] as const,
  preferences: () => [...settingsKeys.all, "preferences"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useOrg() {
  return useQuery({
    queryKey: settingsKeys.org(),
    queryFn: () => api.get<OrgResponse>("/settings/org").then((r) => r.data),
  });
}

export function useUpdateOrg() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Pick<OrgResponse, "name" | "logo_url"> & { settings: Record<string, unknown> }>) =>
      api.put<OrgResponse>("/settings/org", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.org() });
    },
  });
}

export function useTeam() {
  return useQuery({
    queryKey: settingsKeys.team(),
    queryFn: () =>
      api.get<TeamListResponse>("/settings/team").then((r) => r.data),
  });
}

export function useInviteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InviteUserRequest) =>
      api.post<TeamMember>("/settings/team/invite", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.team() });
    },
  });
}

export function useUpdateUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) =>
      api
        .put<TeamMember>(`/settings/team/${userId}/role`, { role })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.team() });
    },
  });
}

export function useToggleUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      is_active,
    }: {
      userId: string;
      is_active: boolean;
    }) =>
      api
        .put<TeamMember>(`/settings/team/${userId}/status`, { is_active })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.team() });
    },
  });
}

export function useApiKeys() {
  return useQuery({
    queryKey: settingsKeys.apiKeys(),
    queryFn: () =>
      api.get<ApiKeyListResponse>("/settings/api-keys").then((r) => r.data),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api
        .post<ApiKeyCreatedResponse>("/settings/api-keys", { name })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.apiKeys() });
    },
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      api.delete(`/settings/api-keys/${keyId}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.apiKeys() });
    },
  });
}

export function usePreferences() {
  return useQuery({
    queryKey: settingsKeys.preferences(),
    queryFn: () =>
      api.get<PreferencesResponse>("/settings/preferences").then((r) => r.data),
  });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: NotificationPreferences) =>
      api
        .put<PreferencesResponse>("/settings/preferences", data)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.preferences() });
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "admin",   label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "analyst", label: "Analyst" },
  { value: "viewer",  label: "Viewer" },
];

export const TIER_LABELS: Record<SubscriptionTier, string> = {
  foundation:   "Foundation",
  professional: "Professional",
  enterprise:   "Enterprise",
};

export const STATUS_LABELS: Record<SubscriptionStatus, string> = {
  active:    "Active",
  trial:     "Trial",
  suspended: "Suspended",
  cancelled: "Cancelled",
};

export function tierVariant(
  tier: SubscriptionTier
): "neutral" | "info" | "gold" {
  if (tier === "enterprise") return "gold";
  if (tier === "professional") return "info";
  return "neutral";
}

export function statusVariant(
  status: SubscriptionStatus
): "success" | "warning" | "error" | "neutral" {
  if (status === "active") return "success";
  if (status === "trial") return "warning";
  if (status === "suspended" || status === "cancelled") return "error";
  return "neutral";
}

export function roleVariant(
  role: UserRole
): "error" | "warning" | "info" | "neutral" {
  if (role === "admin") return "error";
  if (role === "manager") return "warning";
  if (role === "analyst") return "info";
  return "neutral";
}
