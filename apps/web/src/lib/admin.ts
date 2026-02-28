/**
 * Admin module — React Query hooks for platform administration.
 * Only accessible to users in ADMIN-type organisations.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface OrgSummary {
  id: string;
  name: string;
  slug: string;
  type: "investor" | "ally" | "admin";
  subscription_tier: "foundation" | "professional" | "enterprise";
  subscription_status: "active" | "trial" | "suspended" | "cancelled";
  user_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrgDetail extends OrgSummary {
  logo_url: string | null;
  settings: Record<string, unknown>;
}

export interface UserSummary {
  id: string;
  org_id: string;
  org_name: string;
  org_type: "investor" | "ally" | "admin";
  email: string;
  full_name: string;
  role: "admin" | "manager" | "analyst" | "viewer";
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface OrgBreakdown {
  total: number;
  ally: number;
  investor: number;
  admin: number;
  trial: number;
  active: number;
  suspended: number;
  cancelled: number;
}

export interface UserBreakdown {
  total: number;
  active: number;
  inactive: number;
  admins: number;
  managers: number;
  analysts: number;
  viewers: number;
}

export interface PlatformAnalytics {
  orgs: OrgBreakdown;
  users: UserBreakdown;
  total_projects: number;
  total_portfolios: number;
  total_ai_conversations: number;
  total_documents: number;
  generated_at: string;
}

export interface AICostEntry {
  label: string;
  task_count: number;
  total_tokens: number;
  avg_processing_ms: number | null;
  failed_count: number;
}

export interface AICostReport {
  period_days: number;
  total_tasks: number;
  total_tokens: number;
  total_failed: number;
  by_agent: AICostEntry[];
  by_model: AICostEntry[];
  by_org: AICostEntry[];
}

export interface AuditLogEntry {
  id: string;
  org_id: string;
  org_name: string | null;
  user_id: string | null;
  user_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  ip_address: string | null;
  timestamp: string;
}

export interface AuditLogPage {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface ServiceHealth {
  name: string;
  status: "ok" | "degraded" | "down";
  latency_ms: number | null;
  detail: string | null;
}

export interface SystemHealthResponse {
  overall: "ok" | "degraded" | "down";
  services: ServiceHealth[];
  checked_at: string;
}

export interface PagedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const adminKeys = {
  all: ["admin"] as const,
  organizations: (params?: Record<string, unknown>) =>
    [...adminKeys.all, "organizations", params] as const,
  organization: (id: string) => [...adminKeys.all, "organization", id] as const,
  users: (params?: Record<string, unknown>) =>
    [...adminKeys.all, "users", params] as const,
  analytics: () => [...adminKeys.all, "analytics"] as const,
  aiCosts: (days: number) => [...adminKeys.all, "ai-costs", days] as const,
  auditLogs: (params?: Record<string, unknown>) =>
    [...adminKeys.all, "audit-logs", params] as const,
  systemHealth: () => [...adminKeys.all, "system-health"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useAdminOrganizations(params?: {
  search?: string;
  type?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: adminKeys.organizations(params),
    queryFn: () =>
      api
        .get<PagedResult<OrgSummary>>("/admin/organizations", { params })
        .then((r) => r.data),
    retry: false,
  });
}

export function useAdminOrganization(id: string) {
  return useQuery({
    queryKey: adminKeys.organization(id),
    queryFn: () =>
      api.get<OrgDetail>(`/admin/organizations/${id}`).then((r) => r.data),
    enabled: !!id,
    retry: false,
  });
}

export function useUpdateOrgStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      orgId,
      status,
    }: {
      orgId: string;
      status: OrgSummary["subscription_status"];
    }) => api.put(`/admin/organizations/${orgId}/status`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
    },
  });
}

export function useUpdateOrgTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      orgId,
      tier,
    }: {
      orgId: string;
      tier: OrgSummary["subscription_tier"];
    }) => api.put(`/admin/organizations/${orgId}/tier`, { tier }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
    },
  });
}

export function useAdminUsers(params?: {
  search?: string;
  org_id?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: adminKeys.users(params),
    queryFn: () =>
      api
        .get<PagedResult<UserSummary>>("/admin/users", { params })
        .then((r) => r.data),
    retry: false,
  });
}

export function useUpdateUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, is_active }: { userId: string; is_active: boolean }) =>
      api.put(`/admin/users/${userId}/status`, { is_active }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.users() });
    },
  });
}

export function usePlatformAnalytics() {
  return useQuery({
    queryKey: adminKeys.analytics(),
    queryFn: () =>
      api.get<PlatformAnalytics>("/admin/analytics").then((r) => r.data),
    retry: false,
    staleTime: 60 * 1000,
  });
}

export function useAICostReport(days = 30) {
  return useQuery({
    queryKey: adminKeys.aiCosts(days),
    queryFn: () =>
      api
        .get<AICostReport>("/admin/ai-costs", { params: { days } })
        .then((r) => r.data),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAuditLogs(params?: {
  search?: string;
  org_id?: string;
  action?: string;
  entity_type?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: adminKeys.auditLogs(params),
    queryFn: () =>
      api
        .get<AuditLogPage>("/admin/audit-logs", { params })
        .then((r) => r.data),
    retry: false,
  });
}

export function useSystemHealth() {
  return useQuery({
    queryKey: adminKeys.systemHealth(),
    queryFn: () =>
      api
        .get<SystemHealthResponse>("/admin/system-health")
        .then((r) => r.data),
    retry: false,
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function tierLabel(tier: OrgSummary["subscription_tier"]): string {
  const labels: Record<OrgSummary["subscription_tier"], string> = {
    foundation: "Foundation",
    professional: "Professional",
    enterprise: "Enterprise",
  };
  return labels[tier];
}

export function tierColor(
  tier: OrgSummary["subscription_tier"]
): "default" | "info" | "success" {
  if (tier === "enterprise") return "success";
  if (tier === "professional") return "info";
  return "default";
}

export function statusColor(
  status: OrgSummary["subscription_status"]
): "success" | "warning" | "error" | "default" {
  if (status === "active") return "success";
  if (status === "trial") return "warning";
  if (status === "suspended") return "error";
  return "default";
}

export function healthColor(
  status: ServiceHealth["status"]
): "success" | "warning" | "error" {
  if (status === "ok") return "success";
  if (status === "degraded") return "warning";
  return "error";
}

export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
