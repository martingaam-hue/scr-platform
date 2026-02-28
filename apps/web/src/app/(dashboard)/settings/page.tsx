"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Building2,
  Copy,
  Key,
  Loader2,
  Mail,
  Plus,
  Shield,
  Trash2,
  UserPlus,
  Users,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  CardContent,
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

interface DigestResult {
  status: string;
  days: number;
  narrative: string;
  data: Record<string, unknown>;
}

function DigestPreviewCard() {
  const [result, setResult] = useState<DigestResult | null>(null);

  const trigger = useMutation({
    mutationFn: () =>
      api.post<DigestResult>("/digest/trigger?days=7").then((r) => r.data),
    onSuccess: (data) => setResult(data),
  });

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
            onClick={() => trigger.mutate()}
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
      </Tabs>
    </div>
  );
}
