"use client";

import { useState } from "react";
import { Globe, Loader2, Trash2, ShieldCheck, RefreshCw, Copy, Check } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import {
  useCustomDomain,
  useSetDomain,
  useVerifyDomain,
  useDeleteDomain,
  type CustomDomainRecord,
} from "@/lib/custom-domain";

// ── Helpers ───────────────────────────────────────────────────────────────────

type StatusVariant = "neutral" | "info" | "success" | "error" | "warning";

function statusVariant(s: CustomDomainRecord["status"]): StatusVariant {
  switch (s) {
    case "pending":
      return "neutral";
    case "verifying":
      return "info";
    case "verified":
    case "active":
      return "success";
    case "failed":
      return "error";
    default:
      return "neutral";
  }
}

function statusLabel(s: CustomDomainRecord["status"]): string {
  switch (s) {
    case "pending":
      return "Pending";
    case "verifying":
      return "Verifying";
    case "verified":
      return "Verified";
    case "active":
      return "Active";
    case "failed":
      return "Failed";
    default:
      return s;
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <button
      onClick={handleCopy}
      className="ml-2 inline-flex items-center text-neutral-400 hover:text-neutral-600 transition-colors"
      title="Copy"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

// ── DNS record row ────────────────────────────────────────────────────────────

function DnsRow({
  label,
  record,
}: {
  label: string;
  record: { type: string; name: string; value: string; ttl: number };
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {label}
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-neutral-400">
            <th className="pb-1 text-left font-medium w-20">Type</th>
            <th className="pb-1 text-left font-medium w-1/3">Name</th>
            <th className="pb-1 text-left font-medium">Value</th>
            <th className="pb-1 text-left font-medium w-16">TTL</th>
          </tr>
        </thead>
        <tbody>
          <tr className="font-mono text-xs">
            <td className="py-0.5 text-neutral-700">{record.type}</td>
            <td className="py-0.5 text-neutral-700 break-all">
              {record.name}
              <CopyButton text={record.name} />
            </td>
            <td className="py-0.5 text-neutral-700 break-all">
              {record.value}
              <CopyButton text={record.value} />
            </td>
            <td className="py-0.5 text-neutral-500">{record.ttl}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ── Set domain form ───────────────────────────────────────────────────────────

function SetDomainForm() {
  const [domain, setDomain] = useState("");
  const setDomainMutation = useSetDomain();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!domain.trim()) return;
    setDomainMutation.mutate(domain.trim(), {
      onSuccess: () => setDomain(""),
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Configure Custom Domain</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-neutral-500">
          Use your own domain (e.g. <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs">app.acme.com</code>)
          instead of your default <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs">scr.io</code> subdomain.
          You&apos;ll need to add two DNS records to your DNS provider.
        </p>
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="mb-1.5 block text-sm font-medium text-neutral-700">
              Domain
            </label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="app.acme.com"
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              disabled={setDomainMutation.isPending}
            />
          </div>
          <Button
            type="submit"
            disabled={setDomainMutation.isPending || !domain.trim()}
          >
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

// ── Configured domain view ────────────────────────────────────────────────────

function ConfiguredDomain({ record }: { record: CustomDomainRecord }) {
  const verifyMutation = useVerifyDomain();
  const deleteMutation = useDeleteDomain();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const setDomainMutation = useSetDomain();
  const [editMode, setEditMode] = useState(false);
  const [newDomain, setNewDomain] = useState(record.domain);

  function handleVerify() {
    verifyMutation.mutate();
  }

  function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    deleteMutation.mutate();
    setConfirmDelete(false);
  }

  function handleUpdateDomain(e: React.FormEvent) {
    e.preventDefault();
    if (!newDomain.trim() || newDomain.trim() === record.domain) {
      setEditMode(false);
      return;
    }
    setDomainMutation.mutate(newDomain.trim(), {
      onSuccess: () => setEditMode(false),
    });
  }

  const isVerified = record.status === "verified" || record.status === "active";
  const isFailed = record.status === "failed";

  return (
    <div className="space-y-4">
      {/* Domain + status card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Custom Domain</CardTitle>
            <Badge variant={statusVariant(record.status)}>
              {statusLabel(record.status)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {editMode ? (
            <form onSubmit={handleUpdateDomain} className="flex items-end gap-3">
              <div className="flex-1">
                <label className="mb-1.5 block text-sm font-medium text-neutral-700">
                  New Domain
                </label>
                <input
                  type="text"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  disabled={setDomainMutation.isPending}
                />
              </div>
              <Button type="submit" disabled={setDomainMutation.isPending}>
                {setDomainMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Save
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditMode(false);
                  setNewDomain(record.domain);
                }}
              >
                Cancel
              </Button>
            </form>
          ) : (
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <p className="text-xs text-neutral-400 uppercase tracking-wide mb-0.5">Domain</p>
                <p className="font-mono text-sm font-medium text-neutral-800">
                  {record.domain}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditMode(true);
                  setNewDomain(record.domain);
                }}
              >
                Change
              </Button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-neutral-400 uppercase tracking-wide mb-0.5">
                Last Checked
              </p>
              <p className="text-neutral-700">{formatDate(record.last_checked_at)}</p>
            </div>
            {isVerified && (
              <div>
                <p className="text-xs text-neutral-400 uppercase tracking-wide mb-0.5">
                  Verified At
                </p>
                <p className="text-neutral-700">{formatDate(record.verified_at)}</p>
              </div>
            )}
          </div>

          {isVerified && record.ssl_provisioned_at && (
            <div className="flex items-center gap-2 rounded-md bg-green-50 border border-green-200 px-3 py-2">
              <ShieldCheck className="h-4 w-4 text-green-600 flex-shrink-0" />
              <span className="text-sm text-green-700">
                SSL certificate provisioned on {formatDate(record.ssl_provisioned_at)}
              </span>
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

          <div className="flex items-center gap-3 pt-1">
            <Button
              onClick={handleVerify}
              disabled={verifyMutation.isPending}
              variant={isVerified ? "outline" : "default"}
            >
              {verifyMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              {isVerified ? "Re-verify DNS" : "Verify DNS"}
            </Button>

            <Button
              variant={confirmDelete ? "destructive" : "outline"}
              onClick={handleDelete}
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
              <Button
                variant="outline"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* DNS instructions */}
      {!isVerified && (
        <Card>
          <CardHeader>
            <CardTitle>DNS Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-neutral-500">
              Add both DNS records to your DNS provider, then click{" "}
              <strong>Verify DNS</strong>. {record.dns_instructions.note}
            </p>
            <DnsRow label="CNAME Record" record={record.dns_instructions.cname_record} />
            <DnsRow label="TXT Verification Record" record={record.dns_instructions.txt_record} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CustomDomainPage() {
  const { data: record, isLoading } = useCustomDomain();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-neutral-900">Custom Domain</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Point your own domain to your SCR Platform workspace.
        </p>
      </div>

      {record ? (
        <ConfiguredDomain record={record} />
      ) : (
        <SetDomainForm />
      )}
    </div>
  );
}
