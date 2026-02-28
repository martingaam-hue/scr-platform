"use client";

import React, { useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bot,
  Building2,
  CheckCircle2,
  Clock,
  FileText,
  FolderKanban,
  LayoutDashboard,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  TrendingUp,
  Users,
  XCircle,
  Zap,
} from "lucide-react";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState } from "@scr/ui";
import { useSCRUser } from "@/lib/auth";
import {
  useAdminOrganizations,
  useAdminUsers,
  useAICostReport,
  useAIQualityReport,
  useAICorrections,
  useAuditLogs,
  usePlatformAnalytics,
  useSystemHealth,
  useUpdateOrgStatus,
  useUpdateOrgTier,
  useUpdateUserStatus,
  formatTokens,
  healthColor,
  statusColor,
  tierColor,
  tierLabel,
  type OrgSummary,
  type UserSummary,
  type AICostEntry,
  type QualityMetric,
} from "@/lib/admin";

// ── Tab types ──────────────────────────────────────────────────────────────

type Tab =
  | "dashboard"
  | "organizations"
  | "users"
  | "ai-costs"
  | "ai-quality"
  | "audit-logs"
  | "system-health";

// ── Status badge ───────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: OrgSummary["subscription_status"] }) {
  const color = statusColor(status);
  const labels: Record<string, string> = {
    active: "Active",
    trial: "Trial",
    suspended: "Suspended",
    cancelled: "Cancelled",
  };
  return <Badge variant={color}>{labels[status] ?? status}</Badge>;
}

// ── Health dot ─────────────────────────────────────────────────────────────

function HealthDot({ status }: { status: "ok" | "degraded" | "down" }) {
  const color =
    status === "ok"
      ? "bg-green-500"
      : status === "degraded"
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
  );
}

// ── Stat card ──────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  sub?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-950/30">
          <Icon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            {value}
          </p>
          <p className="text-sm text-neutral-500">{label}</p>
          {sub && <p className="text-xs text-neutral-400">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Dashboard tab ──────────────────────────────────────────────────────────

function DashboardTab() {
  const { data: analytics, isLoading, refetch } = usePlatformAnalytics();
  const { data: health } = useSystemHealth();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-neutral-200 dark:bg-neutral-800" />
        ))}
      </div>
    );
  }

  if (!analytics) return <EmptyState title="No analytics data" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          Platform Overview
        </h2>
        <Button variant="ghost" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Org stats */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-neutral-500 uppercase tracking-wide">
          Organizations
        </h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Total Orgs" value={analytics.orgs.total} icon={Building2} />
          <StatCard label="Ally Orgs" value={analytics.orgs.ally} icon={FolderKanban} />
          <StatCard label="Investor Orgs" value={analytics.orgs.investor} icon={TrendingUp} />
          <StatCard
            label="Active Subs"
            value={analytics.orgs.active}
            sub={`${analytics.orgs.trial} on trial`}
            icon={Activity}
          />
        </div>
      </div>

      {/* User stats */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-neutral-500 uppercase tracking-wide">
          Users
        </h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Total Users" value={analytics.users.total} icon={Users} />
          <StatCard
            label="Active Users"
            value={analytics.users.active}
            sub={`${analytics.users.inactive} inactive`}
            icon={CheckCircle2}
          />
          <StatCard label="Admins" value={analytics.users.admins} icon={Shield} />
          <StatCard label="Analysts" value={analytics.users.analysts} icon={BarChart3} />
        </div>
      </div>

      {/* Content stats */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-neutral-500 uppercase tracking-wide">
          Content
        </h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Projects" value={analytics.total_projects} icon={FolderKanban} />
          <StatCard label="Portfolios" value={analytics.total_portfolios} icon={BarChart3} />
          <StatCard label="AI Conversations" value={analytics.total_ai_conversations} icon={Bot} />
          <StatCard label="Documents" value={analytics.total_documents} icon={FileText} />
        </div>
      </div>

      {/* System health mini */}
      {health && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {health.services.map((svc) => (
                <div key={svc.name} className="flex items-center gap-2">
                  <HealthDot status={svc.status} />
                  <span className="text-sm font-medium capitalize text-neutral-700 dark:text-neutral-300">
                    {svc.name}
                  </span>
                  {svc.latency_ms !== null && (
                    <span className="text-xs text-neutral-400">
                      {svc.latency_ms.toFixed(0)}ms
                    </span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Organizations tab ──────────────────────────────────────────────────────

function OrganizationsTab() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const { data, isLoading, refetch } = useAdminOrganizations({
    search: search || undefined,
    limit,
    offset,
  });
  const updateStatus = useUpdateOrgStatus();
  const updateTier = useUpdateOrgTier();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            className="w-full rounded-lg border border-neutral-200 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="Search organisations..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        <Button variant="ghost" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <EmptyState title="No organisations found" />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-900">
                <tr>
                  {["Name", "Type", "Tier", "Status", "Users", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800 bg-white dark:bg-neutral-950">
                {data.items.map((org: OrgSummary) => (
                  <tr key={org.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-neutral-900 dark:text-neutral-100">
                          {org.name}
                        </p>
                        <p className="text-xs text-neutral-400">{org.slug}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="default" className="capitalize">
                        {org.type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        className="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900"
                        value={org.subscription_tier}
                        onChange={(e) =>
                          updateTier.mutate({
                            orgId: org.id,
                            tier: e.target.value as OrgSummary["subscription_tier"],
                          })
                        }
                      >
                        <option value="foundation">Foundation</option>
                        <option value="professional">Professional</option>
                        <option value="enterprise">Enterprise</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        className="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900"
                        value={org.subscription_status}
                        onChange={(e) =>
                          updateStatus.mutate({
                            orgId: org.id,
                            status: e.target.value as OrgSummary["subscription_status"],
                          })
                        }
                      >
                        <option value="active">Active</option>
                        <option value="trial">Trial</option>
                        <option value="suspended">Suspended</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-neutral-600 dark:text-neutral-400">
                      {org.user_count}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={org.subscription_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-neutral-500">
            <span>
              {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + limit >= data.total}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Users tab ──────────────────────────────────────────────────────────────

function UsersTab() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const { data, isLoading } = useAdminUsers({
    search: search || undefined,
    limit,
    offset,
  });
  const updateStatus = useUpdateUserStatus();

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
        <input
          className="w-full rounded-lg border border-neutral-200 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
          placeholder="Search users..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <EmptyState title="No users found" />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-900">
                <tr>
                  {["User", "Organisation", "Role", "Status", "Last Login", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800 bg-white dark:bg-neutral-950">
                {data.items.map((user: UserSummary) => (
                  <tr key={user.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-neutral-900 dark:text-neutral-100">
                          {user.full_name}
                        </p>
                        <p className="text-xs text-neutral-400">{user.email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-neutral-600 dark:text-neutral-400">
                      <div>
                        <p>{user.org_name}</p>
                        <p className="text-xs capitalize text-neutral-400">{user.org_type}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="default" className="capitalize">
                        {user.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        {user.is_active ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs">{user.is_active ? "Active" : "Inactive"}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-400">
                      {user.last_login_at
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : "Never"}
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          updateStatus.mutate({
                            userId: user.id,
                            is_active: !user.is_active,
                          })
                        }
                      >
                        {user.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-neutral-500">
            <span>
              {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + limit >= data.total}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── AI Costs tab ───────────────────────────────────────────────────────────

function AICostsTab() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useAICostReport(days);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <select
          className="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      ) : !data ? (
        <EmptyState title="No AI cost data" />
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Tasks" value={data.total_tasks.toLocaleString()} icon={Zap} />
            <StatCard
              label="Total Tokens"
              value={formatTokens(data.total_tokens)}
              sub={`${data.total_failed} failed`}
              icon={Bot}
            />
            <StatCard
              label="Failed Tasks"
              value={data.total_failed}
              sub={`${data.period_days}-day window`}
              icon={AlertCircle}
            />
          </div>

          {/* By agent */}
          <CostBreakdownTable title="By Agent Type" entries={data.by_agent} />

          {/* By model */}
          <CostBreakdownTable title="By Model" entries={data.by_model} />
        </>
      )}
    </div>
  );
}

function CostBreakdownTable({
  title,
  entries,
}: {
  title: string;
  entries: AICostEntry[];
}) {
  if (!entries.length) return null;
  const maxTokens = Math.max(...entries.map((e) => e.total_tokens));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.label}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-neutral-700 dark:text-neutral-300 capitalize">
                  {entry.label.replace(/_/g, " ")}
                </span>
                <div className="flex items-center gap-4 text-xs text-neutral-500">
                  <span>{entry.task_count.toLocaleString()} tasks</span>
                  <span>{formatTokens(entry.total_tokens)} tokens</span>
                  {entry.avg_processing_ms !== null && (
                    <span>{entry.avg_processing_ms.toFixed(0)}ms avg</span>
                  )}
                  {entry.failed_count > 0 && (
                    <span className="text-red-500">{entry.failed_count} failed</span>
                  )}
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className="h-full rounded-full bg-primary-500"
                  style={{
                    width: `${maxTokens > 0 ? (entry.total_tokens / maxTokens) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Audit Logs tab ─────────────────────────────────────────────────────────

function AuditLogsTab() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 30;

  const { data, isLoading } = useAuditLogs({
    search: search || undefined,
    limit,
    offset,
  });

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
        <input
          className="w-full rounded-lg border border-neutral-200 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
          placeholder="Search action or entity type..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <EmptyState title="No audit log entries" />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-900">
                <tr>
                  {["Timestamp", "Action", "Entity", "User", "Organisation", "IP"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800 bg-white dark:bg-neutral-950">
                {data.items.map((log) => (
                  <tr key={log.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3 text-xs text-neutral-500 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs font-mono text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
                        {log.action}
                      </code>
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400">
                      {log.entity_type}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400">
                      {log.user_email ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-600 dark:text-neutral-400">
                      {log.org_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-400 font-mono">
                      {log.ip_address ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-neutral-500">
            <span>
              {offset + 1}–{Math.min(offset + limit, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + limit >= data.total}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── System Health tab ──────────────────────────────────────────────────────

function SystemHealthTab() {
  const { data, isLoading, refetch } = useSystemHealth();

  const overallColor =
    data?.overall === "ok"
      ? "text-green-600 dark:text-green-400"
      : data?.overall === "degraded"
        ? "text-amber-600 dark:text-amber-400"
        : "text-red-600 dark:text-red-400";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {data && <HealthDot status={data.overall} />}
          <span className={`text-lg font-semibold capitalize ${overallColor}`}>
            {isLoading ? "Checking..." : data?.overall ?? "Unknown"}
          </span>
          {data && (
            <span className="text-sm text-neutral-400">
              Checked {new Date(data.checked_at).toLocaleTimeString()}
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          Re-check
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      ) : !data ? (
        <EmptyState title="Health check failed" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.services.map((svc) => (
            <Card key={svc.name}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HealthDot status={svc.status} />
                    <span className="font-medium capitalize text-neutral-900 dark:text-neutral-100">
                      {svc.name}
                    </span>
                  </div>
                  <Badge variant={healthColor(svc.status)} className="capitalize">
                    {svc.status}
                  </Badge>
                </div>
                {svc.latency_ms !== null && (
                  <div className="mt-2 flex items-center gap-1.5 text-sm text-neutral-500">
                    <Clock className="h-3.5 w-3.5" />
                    <span>{svc.latency_ms.toFixed(1)}ms latency</span>
                  </div>
                )}
                {svc.detail && (
                  <p className="mt-2 text-xs text-red-500 dark:text-red-400">{svc.detail}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── AI Quality tab ──────────────────────────────────────────────────────────

function RateBar({ rate, color }: { rate: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${rate * 100}%` }} />
      </div>
      <span className="text-xs tabular-nums text-neutral-500">
        {(rate * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function AIQualityTab() {
  const [days, setDays] = useState(30);
  const [taskTypeFilter, setTaskTypeFilter] = useState("");
  const [correctionOffset, setCorrectionOffset] = useState(0);
  const correctionLimit = 20;

  const { data: report, isLoading: reportLoading } = useAIQualityReport(days);
  const { data: corrections, isLoading: correctionsLoading } = useAICorrections({
    task_type: taskTypeFilter || undefined,
    limit: correctionLimit,
    offset: correctionOffset,
  });

  return (
    <div className="space-y-8">
      {/* Period selector */}
      <div className="flex items-center gap-3">
        <select
          className="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Summary */}
      {reportLoading ? (
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-neutral-100 dark:bg-neutral-800" />
          ))}
        </div>
      ) : report ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Ratings" value={report.total_feedback.toLocaleString()} icon={BarChart3} />
            <StatCard
              label="Overall Positive Rate"
              value={`${(report.overall_positive_rate * 100).toFixed(1)}%`}
              sub={`${days}-day window`}
              icon={TrendingUp}
            />
            <StatCard
              label="Task Types Tracked"
              value={report.metrics_by_task_type.length}
              icon={Bot}
            />
          </div>

          {/* Quality breakdown table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Quality by Task Type</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50 dark:bg-neutral-900">
                    <tr>
                      {["Task Type", "Feedback", "Positive Rate", "Edit Rate", "Accept Rate"].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
                    {report.metrics_by_task_type.map((metric: QualityMetric) => (
                      <tr key={metric.task_type} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                        <td className="px-4 py-3">
                          <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs font-mono text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
                            {metric.task_type}
                          </code>
                        </td>
                        <td className="px-4 py-3 tabular-nums text-xs text-neutral-600 dark:text-neutral-400">
                          {metric.total_feedback.toLocaleString()}
                          <span className="ml-2 text-neutral-400">
                            (+{metric.positive_count} / -{metric.negative_count})
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <RateBar
                            rate={metric.positive_rate}
                            color={
                              metric.positive_rate >= 0.8
                                ? "bg-green-500"
                                : metric.positive_rate >= 0.5
                                  ? "bg-amber-400"
                                  : "bg-red-500"
                            }
                          />
                        </td>
                        <td className="px-4 py-3">
                          <RateBar rate={metric.edit_rate} color="bg-blue-400" />
                        </td>
                        <td className="px-4 py-3">
                          <RateBar rate={metric.accept_rate} color="bg-violet-400" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <EmptyState title="No quality data yet" description="Ratings will appear once users start providing feedback on AI outputs." />
      )}

      {/* Corrections section */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
            Significant Edits (Edit Distance &gt; 10%)
          </h3>
          <div className="flex items-center gap-2">
            <input
              className="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Filter by task type..."
              value={taskTypeFilter}
              onChange={(e) => {
                setTaskTypeFilter(e.target.value);
                setCorrectionOffset(0);
              }}
            />
          </div>
        </div>

        {correctionsLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800" />
            ))}
          </div>
        ) : !corrections?.items.length ? (
          <EmptyState title="No corrections found" description="Edits to AI outputs will appear here." />
        ) : (
          <>
            <div className="space-y-3">
              {corrections.items.map((item) => (
                <Card key={item.id}>
                  <CardContent className="p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs font-mono text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
                          {item.task_type}
                        </code>
                        {item.edit_distance_pct !== null && (
                          <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                            {(item.edit_distance_pct * 100).toFixed(1)}% changed
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-neutral-400">
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="mb-1 text-xs font-medium text-neutral-500">Original</p>
                        <p className="line-clamp-3 rounded bg-neutral-50 p-2 text-xs text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
                          {item.original_content}
                        </p>
                      </div>
                      <div>
                        <p className="mb-1 text-xs font-medium text-neutral-500">Edited</p>
                        <p className="line-clamp-3 rounded bg-neutral-50 p-2 text-xs text-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
                          {item.edited_content}
                        </p>
                      </div>
                    </div>
                    {item.comment && (
                      <p className="mt-2 text-xs text-neutral-500 italic">&ldquo;{item.comment}&rdquo;</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="mt-4 flex items-center justify-between text-sm text-neutral-500">
              <span>
                {correctionOffset + 1}–{Math.min(correctionOffset + correctionLimit, corrections.total)} of{" "}
                {corrections.total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={correctionOffset === 0}
                  onClick={() => setCorrectionOffset(Math.max(0, correctionOffset - correctionLimit))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={correctionOffset + correctionLimit >= corrections.total}
                  onClick={() => setCorrectionOffset(correctionOffset + correctionLimit)}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Main admin page ────────────────────────────────────────────────────────

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "organizations", label: "Organisations", icon: Building2 },
  { id: "users", label: "Users", icon: Users },
  { id: "ai-costs", label: "AI Costs", icon: Bot },
  { id: "ai-quality", label: "AI Quality", icon: TrendingUp },
  { id: "audit-logs", label: "Audit Logs", icon: FileText },
  { id: "system-health", label: "System Health", icon: Activity },
];

export default function AdminPage() {
  const { user } = useSCRUser();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  // Guard: must be admin org type
  if (user && user.org_type !== "admin") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <ShieldAlert className="mx-auto mb-4 h-12 w-12 text-red-400" />
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Access Denied
          </h2>
          <p className="mt-1 text-sm text-neutral-500">
            Platform administrator access is required.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600 text-white">
          <Shield className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            Admin Panel
          </h1>
          <p className="text-sm text-neutral-500">Platform-level administration</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200 dark:border-neutral-800">
        <nav className="-mb-px flex gap-1 overflow-x-auto">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={[
                "flex shrink-0 items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
                activeTab === id
                  ? "border-primary-600 text-primary-600 dark:text-primary-400"
                  : "border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700 dark:hover:text-neutral-300",
              ].join(" ")}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "dashboard" && <DashboardTab />}
        {activeTab === "organizations" && <OrganizationsTab />}
        {activeTab === "users" && <UsersTab />}
        {activeTab === "ai-costs" && <AICostsTab />}
        {activeTab === "ai-quality" && <AIQualityTab />}
        {activeTab === "audit-logs" && <AuditLogsTab />}
        {activeTab === "system-health" && <SystemHealthTab />}
      </div>
    </div>
  );
}
