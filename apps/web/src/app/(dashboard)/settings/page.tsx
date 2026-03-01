"use client";

import { useState, useEffect } from "react";
import {
  Building2,
  Copy,
  Globe,
  Key,
  Loader2,
  Mail,
  Palette,
  Plus,
  Shield,
  Trash2,
  UserPlus,
  Users,
  Check,
  Webhook,
  Eye,
  EyeOff,
} from "lucide-react";
import { useTriggerDigest, type DigestTriggerResponse } from "@/lib/digest";
import {
  useWebhooks,
  useWebhookDeliveries,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useEnableWebhook,
  useDisableWebhook,
  WEBHOOK_EVENTS,
  type WebhookSubscription,
  type WebhookDelivery,
} from "@/lib/webhooks";
import {
  useCRMConnections,
  useCRMOAuthURL,
  useDisconnectCRM,
  useTriggerSync,
  useSyncLogs,
  useSalesforceSyncProjects,
  useSalesforceContacts,
} from "@/lib/crm";
import { useBranding, useUpdateBranding } from "@/lib/branding";
import {
  useCustomDomain,
  useSetDomain,
  useVerifyDomain,
  useDeleteDomain,
  type CustomDomainRecord,
} from "@/lib/custom-domain";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  DataTable,
  EmptyState,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
} from "@scr/ui";
import {
  useOrg,
  useUpdateOrg,
  useTeam,
  useInviteUser,
  useUpdateUserRole,
  useToggleUserStatus,
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  usePreferences,
  useUpdatePreferences,
  ROLE_OPTIONS,
  TIER_LABELS,
  STATUS_LABELS,
  tierVariant,
  statusVariant,
  roleVariant,
  type TeamMember,
  type ApiKeyItem,
  type UserRole,
  type NotificationPreferences,
} from "@/lib/settings";

// ── Org tab ───────────────────────────────────────────────────────────────

function OrgTab() {
  const { data: org, isLoading } = useOrg();
  const updateOrg = useUpdateOrg();
  const [name, setName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [editing, setEditing] = useState(false);

  function startEdit() {
    if (!org) return;
    setName(org.name);
    setLogoUrl(org.logo_url ?? "");
    setEditing(true);
  }

  function save() {
    updateOrg.mutate(
      { name: name || undefined, logo_url: logoUrl || undefined },
      { onSuccess: () => setEditing(false) }
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!org) {
    return (
      <EmptyState
        icon={<Building2 className="h-10 w-10 text-neutral-300" />}
        title="Organisation data unavailable"
        description="Your organisation details could not be loaded. Please try refreshing the page."
      />
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Profile card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-6">
            <h2 className="text-base font-semibold text-neutral-900">
              Organisation Profile
            </h2>
            {!editing && (
              <Button variant="outline" size="sm" onClick={startEdit}>
                Edit
              </Button>
            )}
          </div>

          <div className="space-y-4">
            {/* Logo */}
            <div className="flex items-center gap-4">
              {org.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={org.logo_url}
                  alt={org.name}
                  className="h-16 w-16 rounded-xl object-contain border border-neutral-200 bg-white"
                />
              ) : (
                <div className="h-16 w-16 rounded-xl bg-neutral-100 flex items-center justify-center">
                  <Building2 className="h-8 w-8 text-neutral-400" />
                </div>
              )}
              {editing && (
                <div className="flex-1">
                  <label className="block text-xs font-medium text-neutral-600 mb-1">
                    Logo URL
                  </label>
                  <input
                    type="url"
                    className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="https://..."
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                  />
                </div>
              )}
            </div>

            {/* Name */}
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Organisation Name
              </label>
              {editing ? (
                <input
                  type="text"
                  className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              ) : (
                <p className="text-sm font-semibold text-neutral-900">
                  {org.name}
                </p>
              )}
            </div>

            {/* Slug */}
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Slug
              </label>
              <p className="text-sm text-neutral-600 font-mono">{org.slug}</p>
            </div>

            {/* Type */}
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Type
              </label>
              <Badge variant="neutral" className="capitalize">
                {org.type}
              </Badge>
            </div>
          </div>

          {editing && (
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-neutral-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={save}
                disabled={updateOrg.isPending}
              >
                {updateOrg.isPending ? "Saving…" : "Save Changes"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Subscription card */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-base font-semibold text-neutral-900 mb-4">
            Subscription
          </h2>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-neutral-500 mb-1">Current Plan</p>
              <div className="flex items-center gap-2">
                <Badge variant={tierVariant(org.subscription_tier)}>
                  {TIER_LABELS[org.subscription_tier]}
                </Badge>
                <Badge variant={statusVariant(org.subscription_status)}>
                  {STATUS_LABELS[org.subscription_status]}
                </Badge>
              </div>
            </div>
          </div>
          <p className="text-xs text-neutral-400 mt-4">
            To upgrade or manage billing, contact{" "}
            <span className="text-primary-600">support@scrplatform.com</span>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Team tab ──────────────────────────────────────────────────────────────

function InviteModal({ onClose }: { onClose: () => void }) {
  const invite = useInviteUser();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");

  function submit() {
    invite.mutate(
      { email, full_name: fullName, role },
      { onSuccess: () => onClose() }
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-neutral-100">
          <h2 className="text-lg font-bold text-neutral-900">Invite Team Member</h2>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Email Address
            </label>
            <input
              type="email"
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="colleague@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Full Name
            </label>
            <input
              type="text"
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Jane Smith"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Role
            </label>
            <select
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
            >
              {ROLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-neutral-100">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={submit}
            disabled={!email || !fullName || invite.isPending}
          >
            {invite.isPending ? "Sending…" : "Send Invite"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function TeamTab() {
  const { data, isLoading } = useTeam();
  const updateRole = useUpdateUserRole();
  const toggleStatus = useToggleUserStatus();
  const [showInvite, setShowInvite] = useState(false);

  const columns: ColumnDef<TeamMember>[] = [
    {
      accessorKey: "full_name",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-sm text-neutral-900">
            {row.original.full_name}
          </p>
          <p className="text-xs text-neutral-500">{row.original.email}</p>
        </div>
      ),
    },
    {
      accessorKey: "role",
      header: "Role",
      cell: ({ row }) => (
        <select
          className="text-xs border border-neutral-200 rounded px-2 h-7 bg-white"
          value={row.original.role}
          onChange={(e) =>
            updateRole.mutate({
              userId: row.original.id,
              role: e.target.value as UserRole,
            })
          }
        >
          {ROLE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ),
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "success" : "neutral"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      accessorKey: "mfa_enabled",
      header: "MFA",
      cell: ({ row }) =>
        row.original.mfa_enabled ? (
          <Badge variant="success">Enabled</Badge>
        ) : (
          <Badge variant="neutral">Off</Badge>
        ),
    },
    {
      accessorKey: "last_login_at",
      header: "Last Login",
      cell: ({ row }) =>
        row.original.last_login_at
          ? new Date(row.original.last_login_at).toLocaleDateString()
          : "—",
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <button
          className="text-xs text-neutral-500 hover:text-neutral-800 transition-colors"
          onClick={() =>
            toggleStatus.mutate({
              userId: row.original.id,
              is_active: !row.original.is_active,
            })
          }
        >
          {row.original.is_active ? "Deactivate" : "Activate"}
        </button>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-semibold text-neutral-800">
          Team Members{" "}
          {data && (
            <span className="text-neutral-400 font-normal text-sm">
              ({data.total})
            </span>
          )}
        </h2>
        <Button size="sm" onClick={() => setShowInvite(true)}>
          <UserPlus className="h-4 w-4 mr-1.5" />
          Invite
        </Button>
      </div>

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Users className="h-8 w-8" />}
          title="No team members"
          description="Invite colleagues to collaborate on the platform."
        />
      ) : (
        <DataTable columns={columns} data={data.items} />
      )}

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} />}
    </div>
  );
}

// ── API Keys tab ──────────────────────────────────────────────────────────

function CreatedKeyBanner({
  apiKey,
  onDismiss,
}: {
  apiKey: string;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);

  function copyKey() {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <Shield className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-amber-800 mb-1">
            Copy your API key now — it won&apos;t be shown again.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <code className="flex-1 text-xs bg-white border border-amber-200 rounded px-3 py-2 font-mono truncate">
              {apiKey}
            </code>
            <button
              onClick={copyKey}
              className="shrink-0 flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 transition-colors"
            >
              {copied ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
        <button
          onClick={onDismiss}
          className="text-amber-500 hover:text-amber-800 text-sm"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

function ApiKeysTab() {
  const { data, isLoading } = useApiKeys();
  const createKey = useCreateApiKey();
  const revokeKey = useRevokeApiKey();
  const [newKeyName, setNewKeyName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  function handleCreate() {
    if (!newKeyName.trim()) return;
    createKey.mutate(newKeyName.trim(), {
      onSuccess: (data) => {
        setCreatedKey(data.key);
        setNewKeyName("");
        setShowCreate(false);
      },
    });
  }

  const columns: ColumnDef<ApiKeyItem>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-sm">{row.original.name}</p>
          <code className="text-xs text-neutral-400">{row.original.prefix}…</code>
        </div>
      ),
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "success" : "neutral"}>
          {row.original.is_active ? "Active" : "Revoked"}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) =>
        new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      accessorKey: "last_used_at",
      header: "Last Used",
      cell: ({ row }) =>
        row.original.last_used_at
          ? new Date(row.original.last_used_at).toLocaleDateString()
          : "Never",
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) =>
        row.original.is_active ? (
          <button
            onClick={() => revokeKey.mutate(row.original.id)}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Revoke
          </button>
        ) : null,
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-semibold text-neutral-800">API Keys</h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            Authenticate programmatic access to the SCR API.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreate((v) => !v)}>
          <Plus className="h-4 w-4 mr-1.5" />
          New Key
        </Button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="mb-5 bg-neutral-50 border border-neutral-200 rounded-xl p-4 flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Key Name
            </label>
            <input
              type="text"
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. CI Pipeline"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
          </div>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={!newKeyName.trim() || createKey.isPending}
          >
            {createKey.isPending ? "Creating…" : "Create"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCreate(false)}
          >
            Cancel
          </Button>
        </div>
      )}

      {/* New key banner */}
      {createdKey && (
        <CreatedKeyBanner
          apiKey={createdKey}
          onDismiss={() => setCreatedKey(null)}
        />
      )}

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Key className="h-8 w-8" />}
          title="No API keys"
          description="Create an API key to integrate with external systems."
        />
      ) : (
        <DataTable columns={columns} data={data.items} />
      )}
    </div>
  );
}

// ── Preferences tab ───────────────────────────────────────────────────────

interface ToggleRowProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

function ToggleRow({ label, description, checked, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-neutral-100 last:border-0">
      <div>
        <p className="text-sm font-medium text-neutral-800">{label}</p>
        <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
          checked ? "bg-primary-600" : "bg-neutral-200"
        }`}
      >
        <span
          className={`block h-4 w-4 rounded-full bg-white shadow transition-transform absolute top-1 ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

function PreferencesTab() {
  const { data, isLoading } = usePreferences();
  const updatePrefs = useUpdatePreferences();
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [saved, setSaved] = useState(false);

  // Initialise local state from fetched data
  const notif = prefs ?? data?.notification;

  function toggle(key: keyof NotificationPreferences) {
    if (!notif) return;
    setPrefs({
      ...(prefs ?? notif),
      [key]: !notif[key],
    });
  }

  function save() {
    if (!notif) return;
    updatePrefs.mutate(notif as NotificationPreferences, {
      onSuccess: () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      },
    });
  }

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!notif) return null;

  const emailToggles: {
    key: keyof NotificationPreferences;
    label: string;
    description: string;
  }[] = [
    {
      key: "email_match_alerts",
      label: "Match Alerts",
      description: "Email when new investors are matched to your projects.",
    },
    {
      key: "email_project_updates",
      label: "Project Updates",
      description: "Email when project status or milestones change.",
    },
    {
      key: "email_report_ready",
      label: "Report Ready",
      description: "Email when a generated report or memo is ready.",
    },
    {
      key: "email_weekly_digest",
      label: "Weekly Digest",
      description: "Summary of activity across your portfolio each week.",
    },
  ];

  const inAppToggles: {
    key: keyof NotificationPreferences;
    label: string;
    description: string;
  }[] = [
    {
      key: "in_app_mentions",
      label: "Mentions",
      description: "In-app alert when you are @mentioned in a comment.",
    },
    {
      key: "in_app_match_alerts",
      label: "Match Alerts",
      description: "In-app badge when new matches are available.",
    },
    {
      key: "in_app_status_changes",
      label: "Status Changes",
      description: "In-app alert when match or project status changes.",
    },
  ];

  return (
    <div className="max-w-2xl space-y-6">
      {/* Email notifications */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-base font-semibold text-neutral-900 mb-1">
            Email Notifications
          </h2>
          <p className="text-xs text-neutral-500 mb-4">
            Choose which emails you receive from the platform.
          </p>
          <div>
            {emailToggles.map((t) => (
              <ToggleRow
                key={t.key}
                label={t.label}
                description={t.description}
                checked={notif[t.key] as boolean}
                onChange={() => toggle(t.key)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* In-app notifications */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-base font-semibold text-neutral-900 mb-1">
            In-App Notifications
          </h2>
          <p className="text-xs text-neutral-500 mb-4">
            Control which alerts appear in the notification centre.
          </p>
          <div>
            {inAppToggles.map((t) => (
              <ToggleRow
                key={t.key}
                label={t.label}
                description={t.description}
                checked={notif[t.key] as boolean}
                onChange={() => toggle(t.key)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Digest frequency */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-base font-semibold text-neutral-900 mb-1">
            Digest Frequency
          </h2>
          <p className="text-xs text-neutral-500 mb-4">
            How often to receive activity summary emails.
          </p>
          <select
            className="text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
            value={notif.digest_frequency}
            onChange={(e) =>
              setPrefs({
                ...(prefs ?? notif),
                digest_frequency: e.target.value as NotificationPreferences["digest_frequency"],
              })
            }
          >
            <option value="never">Never</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </CardContent>
      </Card>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <Button onClick={save} disabled={updatePrefs.isPending}>
          {updatePrefs.isPending ? "Saving…" : "Save Preferences"}
        </Button>
        {saved && (
          <span className="flex items-center gap-1 text-sm text-green-600">
            <Check className="h-4 w-4" />
            Saved
          </span>
        )}
      </div>

      {/* Digest Preview */}
      <DigestPreviewCard />
    </div>
  );
}

// ── Digest Preview ─────────────────────────────────────────────────────────

function DigestPreviewCard() {
  const [result, setResult] = useState<DigestTriggerResponse | null>(null);

  const trigger = useTriggerDigest();

  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
              <Mail className="h-4 w-4 text-neutral-500" />
              Digest Preview
            </h2>
            <p className="text-xs text-neutral-500 mt-1">
              Generate a preview of your weekly activity digest.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => trigger.mutate(7, { onSuccess: (data) => setResult(data) })}
            disabled={trigger.isPending}
            className="h-8 text-xs"
          >
            {trigger.isPending ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin mr-1.5" />
                Generating…
              </>
            ) : (
              "Generate Preview"
            )}
          </Button>
        </div>

        {result && (
          <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-4 space-y-3">
            <p className="text-sm text-neutral-800 leading-relaxed italic">
              "{result.narrative}"
            </p>
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-neutral-200">
              <div className="text-center">
                <p className="text-xl font-bold text-primary-600">
                  {(result.data as { ai_tasks_completed?: number }).ai_tasks_completed ?? 0}
                </p>
                <p className="text-xs text-neutral-500">AI tasks completed</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-primary-600">
                  {(result.data as { new_projects?: number }).new_projects ?? 0}
                </p>
                <p className="text-xs text-neutral-500">New projects</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── CRM Tab ───────────────────────────────────────────────────────────────

function CRMProviderCard({
  label,
  provider,
  oauthURL,
  active,
  disconnect,
  triggerSync,
  logs,
  sfSyncProjects,
  sfContacts,
}: {
  label: string;
  provider: string;
  oauthURL: { data?: { url: string }; isLoading: boolean };
  active?: { id: string; provider: string; sync_direction: string; last_synced_at: string | null; connection_name: string } | null;
  disconnect: ReturnType<typeof useDisconnectCRM>;
  triggerSync: ReturnType<typeof useTriggerSync>;
  logs?: ReturnType<typeof useSyncLogs>["data"];
  sfSyncProjects?: ReturnType<typeof useSalesforceSyncProjects>;
  sfContacts?: ReturnType<typeof useSalesforceContacts>["data"];
}) {
  const isSalesforce = provider === "salesforce";

  if (!active) {
    return (
      <Card>
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-neutral-900">{label}</p>
              <p className="text-xs text-neutral-500">Not connected</p>
            </div>
            <Button
              size="sm"
              onClick={() => {
                if (oauthURL.data?.url) window.location.href = oauthURL.data.url;
              }}
              disabled={oauthURL.isLoading}
            >
              {oauthURL.isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Connect {label}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-neutral-900">{active.connection_name}</p>
              <p className="text-xs text-neutral-500 capitalize">
                {active.provider} · {active.sync_direction}
              </p>
              {active.last_synced_at && (
                <p className="text-xs text-neutral-400">
                  Last synced: {new Date(active.last_synced_at).toLocaleString()}
                </p>
              )}
            </div>
            <div className="flex gap-2">
              {!isSalesforce && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => triggerSync.mutate(active.id)}
                  disabled={triggerSync.isPending}
                >
                  {triggerSync.isPending ? (
                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                  ) : null}
                  Sync Now
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => disconnect.mutate(active.id)}
                disabled={disconnect.isPending}
              >
                Disconnect
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {isSalesforce && sfContacts && sfContacts.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-3 text-sm font-semibold text-neutral-900">
              Salesforce Contacts ({sfContacts.length})
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-neutral-500">
                    <th className="py-2 pr-4 font-medium">Name</th>
                    <th className="py-2 font-medium">Email</th>
                  </tr>
                </thead>
                <tbody>
                  {sfContacts.slice(0, 10).map((c) => (
                    <tr key={c.id ?? c.email ?? c.name} className="border-b last:border-0">
                      <td className="py-2 pr-4 text-neutral-700">{c.name ?? "—"}</td>
                      <td className="py-2 text-neutral-700">{c.email ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {logs && logs.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-3 text-sm font-semibold text-neutral-900">Sync Logs</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-neutral-500">
                    <th className="py-2 pr-4 font-medium">Direction</th>
                    <th className="py-2 pr-4 font-medium">Entity</th>
                    <th className="py-2 pr-4 font-medium">Action</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice(0, 20).map((log) => (
                    <tr key={log.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 text-neutral-700 capitalize">{log.direction}</td>
                      <td className="py-2 pr-4 text-neutral-700">{log.entity_type}</td>
                      <td className="py-2 pr-4 text-neutral-700">{log.action}</td>
                      <td className="py-2 pr-4">
                        <Badge
                          variant={
                            log.status === "success"
                              ? "success"
                              : log.status === "failed"
                              ? "error"
                              : "neutral"
                          }
                        >
                          {log.status}
                        </Badge>
                      </td>
                      <td className="py-2 text-neutral-400 text-xs">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CRMTab() {
  const { data: connections, isLoading } = useCRMConnections();
  const hubspotOAuthURL = useCRMOAuthURL("hubspot");
  const salesforceOAuthURL = useCRMOAuthURL("salesforce");
  const disconnect = useDisconnectCRM();
  const triggerSync = useTriggerSync();

  const activeHubspot = connections?.find((c) => c.is_active && c.provider === "hubspot");
  const activeSalesforce = connections?.find((c) => c.is_active && c.provider === "salesforce");

  const { data: hubspotLogs } = useSyncLogs(activeHubspot?.id);
  const { data: salesforceLogs } = useSyncLogs(activeSalesforce?.id);

  const sfSyncProjects = useSalesforceSyncProjects(activeSalesforce?.id ?? "");
  const { data: sfContacts } = useSalesforceContacts(activeSalesforce?.id, !!activeSalesforce);

  if (isLoading) {
    return (
      <div className="flex h-24 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
      </div>
    );
  }

  const hasAny = activeHubspot || activeSalesforce;

  return (
    <div className="space-y-8">
      {!hasAny && (
        <Card>
          <CardContent className="p-6">
            <EmptyState
              icon={<Shield className="h-10 w-10 text-neutral-400" />}
              title="No CRM connected"
              description="Connect HubSpot or Salesforce to sync your pipeline and contacts bidirectionally."
            />
          </CardContent>
        </Card>
      )}

      <div>
        <h3 className="mb-3 text-sm font-semibold text-neutral-700">HubSpot</h3>
        <CRMProviderCard
          label="HubSpot"
          provider="hubspot"
          oauthURL={hubspotOAuthURL}
          active={activeHubspot}
          disconnect={disconnect}
          triggerSync={triggerSync}
          logs={hubspotLogs}
        />
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold text-neutral-700">Salesforce</h3>
        <CRMProviderCard
          label="Salesforce"
          provider="salesforce"
          oauthURL={salesforceOAuthURL}
          active={activeSalesforce}
          disconnect={disconnect}
          triggerSync={triggerSync}
          logs={salesforceLogs}
          sfSyncProjects={sfSyncProjects}
          sfContacts={sfContacts}
        />
      </div>
    </div>
  );
}

// ── Branding tab ──────────────────────────────────────────────────────────

function BrandingTab() {
  const { data: branding } = useBranding();
  const update = useUpdateBranding();
  const [form, setForm] = useState({
    primary_color: branding?.primary_color ?? "#6366f1",
    accent_color: branding?.accent_color ?? "#8b5cf6",
    company_name: branding?.company_name ?? "",
    logo_url: branding?.logo_url ?? "",
    font_family: branding?.font_family ?? "Inter",
  });

  // Update form when branding loads
  useEffect(() => {
    if (branding) {
      setForm({
        primary_color: branding.primary_color,
        accent_color: branding.accent_color,
        company_name: branding.company_name ?? "",
        logo_url: branding.logo_url ?? "",
        font_family: branding.font_family,
      });
    }
  }, [branding]);

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <CardContent className="p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-neutral-900 mb-1">
              Brand Colors
            </h2>
            <p className="text-xs text-neutral-500 mb-4">
              Customise the platform colours to match your organisation identity.
            </p>
            {/* Color pickers */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Primary Color
                </label>
                <input
                  type="color"
                  value={form.primary_color}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, primary_color: e.target.value }))
                  }
                  className="h-10 w-full rounded border border-neutral-200 cursor-pointer p-0.5"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Accent Color
                </label>
                <input
                  type="color"
                  value={form.accent_color}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, accent_color: e.target.value }))
                  }
                  className="h-10 w-full rounded border border-neutral-200 cursor-pointer p-0.5"
                />
              </div>
            </div>
          </div>

          {/* Text inputs */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Company Name
              </label>
              <input
                type="text"
                value={form.company_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, company_name: e.target.value }))
                }
                className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Your Company"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Logo URL
              </label>
              <input
                type="url"
                value={form.logo_url}
                onChange={(e) =>
                  setForm((f) => ({ ...f, logo_url: e.target.value }))
                }
                className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="https://..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Font Family
              </label>
              <select
                value={form.font_family}
                onChange={(e) =>
                  setForm((f) => ({ ...f, font_family: e.target.value }))
                }
                className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
              >
                {["Inter", "Roboto", "Poppins", "DM Sans"].map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Live preview */}
          <div
            className="rounded-lg border p-4"
            style={{ borderColor: form.primary_color }}
          >
            <p
              className="text-sm font-semibold mb-3"
              style={{ color: form.primary_color }}
            >
              Live Preview
            </p>
            <div className="flex gap-2 mb-3">
              <span
                className="px-3 py-1 rounded text-white text-xs font-medium"
                style={{ background: form.primary_color }}
              >
                Primary
              </span>
              <span
                className="px-3 py-1 rounded text-white text-xs font-medium"
                style={{ background: form.accent_color }}
              >
                Accent
              </span>
            </div>
            {form.company_name && (
              <p
                className="text-xs font-medium"
                style={{ color: form.accent_color }}
              >
                {form.company_name}
              </p>
            )}
          </div>

          <Button
            onClick={() =>
              update.mutate({
                primary_color: form.primary_color,
                accent_color: form.accent_color,
                company_name: form.company_name || undefined,
                logo_url: form.logo_url || undefined,
                font_family: form.font_family,
              })
            }
            disabled={update.isPending}
          >
            {update.isPending ? "Saving…" : "Save Branding"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Webhooks tab ──────────────────────────────────────────────────────────

function statusVariantForDelivery(
  status: WebhookDelivery["status"]
): "success" | "error" | "warning" | "neutral" {
  if (status === "delivered") return "success";
  if (status === "failed") return "error";
  if (status === "retrying") return "warning";
  return "neutral";
}

function DeliveryLog({ subscriptionId }: { subscriptionId: string }) {
  const { data: deliveries, isLoading } = useWebhookDeliveries(subscriptionId);

  if (isLoading) {
    return (
      <div className="flex h-16 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!deliveries || deliveries.length === 0) {
    return (
      <p className="text-xs text-neutral-400 py-2">No deliveries yet.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b text-left text-neutral-500">
            <th className="py-1.5 pr-3 font-medium">Event</th>
            <th className="py-1.5 pr-3 font-medium">Status</th>
            <th className="py-1.5 pr-3 font-medium">Code</th>
            <th className="py-1.5 pr-3 font-medium">Attempts</th>
            <th className="py-1.5 font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {deliveries.slice(0, 10).map((d) => (
            <tr key={d.id} className="border-b last:border-0">
              <td className="py-1.5 pr-3 font-mono text-neutral-700">
                {d.event_type}
              </td>
              <td className="py-1.5 pr-3">
                <Badge variant={statusVariantForDelivery(d.status)}>
                  {d.status}
                </Badge>
              </td>
              <td className="py-1.5 pr-3 text-neutral-500">
                {d.response_status_code ?? "—"}
              </td>
              <td className="py-1.5 pr-3 text-neutral-500">{d.attempts}</td>
              <td className="py-1.5 text-neutral-400">
                {new Date(d.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface AddWebhookFormProps {
  onClose: () => void;
}

function AddWebhookForm({ onClose }: AddWebhookFormProps) {
  const create = useCreateWebhook();
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [description, setDescription] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [showSecret, setShowSecret] = useState(false);

  function toggleEvent(event: string) {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  }

  function submit() {
    if (!url.trim() || !secret.trim() || selectedEvents.length === 0) return;
    create.mutate(
      {
        url: url.trim(),
        secret: secret.trim(),
        events: selectedEvents,
        description: description.trim() || undefined,
      },
      { onSuccess: () => onClose() }
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-neutral-100">
          <h2 className="text-lg font-bold text-neutral-900">
            Add Webhook Endpoint
          </h2>
        </div>
        <div className="p-6 space-y-4">
          {/* URL */}
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Endpoint URL
            </label>
            <input
              type="url"
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="https://your-service.example.com/webhooks"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>

          {/* Secret */}
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Signing Secret
            </label>
            <div className="relative">
              <input
                type={showSecret ? "text" : "password"}
                className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 pr-9 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Your HMAC signing secret"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowSecret((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-700"
              >
                {showSecret ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            <p className="mt-1 text-xs text-neutral-400">
              Payloads are signed with HMAC-SHA256. Verify the{" "}
              <code className="font-mono">X-SCR-Signature</code> header.
            </p>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Description (optional)
            </label>
            <input
              type="text"
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. Notify Slack on score updates"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* Events */}
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-2">
              Events to subscribe to
            </label>
            <div className="grid grid-cols-1 gap-1 max-h-48 overflow-y-auto border border-neutral-200 rounded-lg p-3">
              {WEBHOOK_EVENTS.map((event) => (
                <label
                  key={event}
                  className="flex items-center gap-2 cursor-pointer hover:bg-neutral-50 rounded px-1 py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(event)}
                    onChange={() => toggleEvent(event)}
                    className="accent-primary-600"
                  />
                  <span className="text-xs font-mono text-neutral-700">
                    {event}
                  </span>
                </label>
              ))}
            </div>
            {selectedEvents.length === 0 && (
              <p className="text-xs text-red-500 mt-1">
                Select at least one event.
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 p-6 border-t border-neutral-100">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={submit}
            disabled={
              !url.trim() ||
              !secret.trim() ||
              selectedEvents.length === 0 ||
              create.isPending
            }
          >
            {create.isPending ? "Adding…" : "Add Webhook"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function WebhookRow({ sub }: { sub: WebhookSubscription }) {
  const [expanded, setExpanded] = useState(false);
  const deleteWebhook = useDeleteWebhook();
  const testWebhook = useTestWebhook();
  const enableWebhook = useEnableWebhook();
  const disableWebhook = useDisableWebhook();
  const update = useUpdateWebhook(sub.id);

  return (
    <div className="border border-neutral-200 rounded-xl overflow-hidden">
      {/* Header row */}
      <div className="p-4 flex items-start gap-4 bg-white">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm text-neutral-900 truncate max-w-xs">
              {sub.url}
            </span>
            <Badge variant={sub.is_active ? "success" : "neutral"}>
              {sub.is_active ? "Active" : "Disabled"}
            </Badge>
            {sub.failure_count > 0 && (
              <Badge variant="warning">{sub.failure_count} failures</Badge>
            )}
          </div>
          {sub.description && (
            <p className="text-xs text-neutral-500 mt-0.5">{sub.description}</p>
          )}
          {sub.disabled_reason && (
            <p className="text-xs text-red-500 mt-0.5">{sub.disabled_reason}</p>
          )}
          <div className="flex flex-wrap gap-1 mt-2">
            {sub.events.map((e) => (
              <span
                key={e}
                className="text-xs font-mono bg-neutral-100 text-neutral-600 px-1.5 py-0.5 rounded"
              >
                {e}
              </span>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-neutral-500 hover:text-neutral-800 transition-colors"
          >
            {expanded ? "Hide logs" : "Show logs"}
          </button>
          <button
            onClick={() =>
              testWebhook.mutate({ id: sub.id, event_type: "test.ping" })
            }
            disabled={testWebhook.isPending}
            className="text-xs text-primary-600 hover:text-primary-800 transition-colors"
          >
            {testWebhook.isPending ? "Testing…" : "Test"}
          </button>
          {sub.is_active ? (
            <button
              onClick={() => disableWebhook.mutate(sub.id)}
              disabled={disableWebhook.isPending}
              className="text-xs text-neutral-500 hover:text-neutral-800 transition-colors"
            >
              Disable
            </button>
          ) : (
            <button
              onClick={() => enableWebhook.mutate(sub.id)}
              disabled={enableWebhook.isPending}
              className="text-xs text-green-600 hover:text-green-800 transition-colors"
            >
              Enable
            </button>
          )}
          <button
            onClick={() => {
              if (confirm("Delete this webhook subscription?")) {
                deleteWebhook.mutate(sub.id);
              }
            }}
            className="text-xs text-red-500 hover:text-red-700 transition-colors flex items-center gap-1"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      </div>

      {/* Delivery log */}
      {expanded && (
        <div className="border-t border-neutral-100 bg-neutral-50 p-4">
          <h4 className="text-xs font-semibold text-neutral-600 mb-2">
            Recent Deliveries
          </h4>
          <DeliveryLog subscriptionId={sub.id} />
        </div>
      )}
    </div>
  );
}

function WebhooksTab() {
  const { data: webhooks, isLoading } = useWebhooks();
  const [showAdd, setShowAdd] = useState(false);

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-semibold text-neutral-800">Webhook Endpoints</h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            Receive real-time HTTP POST notifications when events occur in the
            platform. Payloads are signed with HMAC-SHA256.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          Add Webhook
        </Button>
      </div>

      {/* Subscriptions list */}
      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : !webhooks || webhooks.length === 0 ? (
        <EmptyState
          icon={<Webhook className="h-8 w-8" />}
          title="No webhook endpoints"
          description="Add a webhook to receive real-time event notifications."
        />
      ) : (
        <div className="space-y-3">
          {webhooks.map((sub) => (
            <WebhookRow key={sub.id} sub={sub} />
          ))}
        </div>
      )}

      {/* Events catalog */}
      <div className="mt-8">
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">
              Supported Event Types
            </h3>
            <div className="grid grid-cols-2 gap-1.5">
              {WEBHOOK_EVENTS.map((event) => {
                const [domain, name] = event.split(".");
                return (
                  <div
                    key={event}
                    className="flex items-start gap-2 rounded-lg bg-neutral-50 px-3 py-2"
                  >
                    <span className="font-mono text-xs text-neutral-700">
                      <span className="text-primary-600">{domain}</span>
                      <span className="text-neutral-400">.</span>
                      {name}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {showAdd && <AddWebhookForm onClose={() => setShowAdd(false)} />}
    </div>
  );
}

// ── Custom Domain Tab ─────────────────────────────────────────────────────

type DomainStatus = CustomDomainRecord["status"];

function domainStatusVariant(s: DomainStatus): "neutral" | "info" | "success" | "error" {
  switch (s) {
    case "pending": return "neutral";
    case "verifying": return "info";
    case "verified":
    case "active": return "success";
    case "failed": return "error";
    default: return "neutral";
  }
}

function domainStatusLabel(s: DomainStatus): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function CopyInline({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        });
      }}
      className="ml-1.5 inline-flex items-center text-neutral-400 hover:text-neutral-600"
      title="Copy"
    >
      {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

function CustomDomainTab() {
  const { data: record, isLoading } = useCustomDomain();
  const setDomainMutation = useSetDomain();
  const verifyMutation = useVerifyDomain();
  const deleteMutation = useDeleteDomain();
  const [domain, setDomain] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  // No domain configured
  if (!record) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Configure Custom Domain</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-neutral-500">
            Use your own domain (e.g.{" "}
            <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs">app.acme.com</code>)
            instead of your default <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs">scr.io</code> subdomain.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (domain.trim()) setDomainMutation.mutate(domain.trim(), { onSuccess: () => setDomain("") });
            }}
            className="flex items-end gap-3"
          >
            <div className="flex-1">
              <label className="mb-1.5 block text-sm font-medium text-neutral-700">Domain</label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="app.acme.com"
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                disabled={setDomainMutation.isPending}
              />
            </div>
            <Button type="submit" disabled={setDomainMutation.isPending || !domain.trim()}>
              {setDomainMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Globe className="mr-2 h-4 w-4" />
              )}
              Set Domain
            </Button>
          </form>
          {setDomainMutation.isError && (
            <p className="mt-2 text-sm text-red-600">
              {(setDomainMutation.error as Error)?.message ?? "Failed to set domain"}
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  const isVerified = record.status === "verified" || record.status === "active";
  const isFailed = record.status === "failed";
  const { dns_instructions: dns } = record;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Custom Domain</CardTitle>
            <Badge variant={domainStatusVariant(record.status)}>
              {domainStatusLabel(record.status)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs text-neutral-400 uppercase tracking-wide mb-0.5">Domain</p>
            <p className="font-mono text-sm font-medium">{record.domain}</p>
          </div>

          {isVerified && record.ssl_provisioned_at && (
            <div className="flex items-center gap-2 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
              <Shield className="h-4 w-4 text-green-600 flex-shrink-0" />
              SSL provisioned on{" "}
              {new Date(record.ssl_provisioned_at).toLocaleDateString("en-GB", {
                day: "numeric", month: "short", year: "numeric",
              })}
            </div>
          )}

          {isFailed && record.error_message && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2">
              <p className="text-sm font-medium text-red-700 mb-0.5">Verification Failed</p>
              <p className="text-sm text-red-600">{record.error_message}</p>
            </div>
          )}

          {verifyMutation.isError && (
            <p className="text-sm text-red-600">
              {(verifyMutation.error as Error)?.message ?? "Verification request failed"}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending}
              variant={isVerified ? "outline" : "default"}
            >
              {verifyMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Globe className="mr-2 h-4 w-4" />
              )}
              {isVerified ? "Re-verify DNS" : "Verify DNS"}
            </Button>

            <Button
              variant={confirmDelete ? "destructive" : "outline"}
              onClick={() => {
                if (!confirmDelete) { setConfirmDelete(true); return; }
                deleteMutation.mutate();
                setConfirmDelete(false);
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              {confirmDelete ? "Click again to confirm" : "Remove Domain"}
            </Button>

            {confirmDelete && (
              <Button variant="outline" onClick={() => setConfirmDelete(false)}>
                Cancel
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* DNS instructions — always shown so user can re-add if needed */}
      <Card>
        <CardHeader>
          <CardTitle>DNS Records</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-neutral-500">{dns.note}</p>

          {[
            { label: "CNAME Record", rec: dns.cname_record },
            { label: "TXT Verification Record", rec: dns.txt_record },
          ].map(({ label, rec }) => (
            <div key={label} className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {label}
              </p>
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-neutral-400">
                    <th className="pb-1 text-left font-medium w-14">Type</th>
                    <th className="pb-1 text-left font-medium w-1/3">Name</th>
                    <th className="pb-1 text-left font-medium">Value</th>
                    <th className="pb-1 text-left font-medium w-14">TTL</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="text-neutral-700">
                    <td className="py-0.5">{rec.type}</td>
                    <td className="py-0.5 break-all">
                      {rec.name}<CopyInline text={rec.name} />
                    </td>
                    <td className="py-0.5 break-all">
                      {rec.value}<CopyInline text={rec.value} />
                    </td>
                    <td className="py-0.5 text-neutral-400">{rec.ttl}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Settings</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Manage your organisation, team, API access, and notification preferences.
        </p>
      </div>

      <Tabs defaultValue="org">
        <TabsList className="mb-6">
          <TabsTrigger value="org">
            <Building2 className="h-4 w-4 mr-1.5" />
            Organisation
          </TabsTrigger>
          <TabsTrigger value="team">
            <Users className="h-4 w-4 mr-1.5" />
            Team
          </TabsTrigger>
          <TabsTrigger value="api-keys">
            <Key className="h-4 w-4 mr-1.5" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="preferences">
            Preferences
          </TabsTrigger>
          <TabsTrigger value="crm">
            CRM
          </TabsTrigger>
          <TabsTrigger value="branding">
            <Palette className="h-4 w-4 mr-1.5" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="webhooks">
            <Webhook className="h-4 w-4 mr-1.5" />
            Webhooks
          </TabsTrigger>
          <TabsTrigger value="custom-domain">
            <Globe className="h-4 w-4 mr-1.5" />
            Custom Domain
          </TabsTrigger>
        </TabsList>

        <TabsContent value="org">
          <OrgTab />
        </TabsContent>

        <TabsContent value="team">
          <TeamTab />
        </TabsContent>

        <TabsContent value="api-keys">
          <ApiKeysTab />
        </TabsContent>

        <TabsContent value="preferences">
          <PreferencesTab />
        </TabsContent>

        <TabsContent value="crm">
          <CRMTab />
        </TabsContent>

        <TabsContent value="branding">
          <BrandingTab />
        </TabsContent>

        <TabsContent value="webhooks">
          <WebhooksTab />
        </TabsContent>

        <TabsContent value="custom-domain">
          <CustomDomainTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
