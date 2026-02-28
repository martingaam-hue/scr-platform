"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Clock,
  ExternalLink,
  Link2,
  RefreshCw,
  Shield,
  ShieldCheck,
  XCircle,
} from "lucide-react";
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
  useAuditReport,
  useBatchSubmit,
  type AnchorResponse,
} from "@/lib/blockchain";

// ── Helpers ────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  string,
  { variant: "success" | "warning" | "error" | "neutral"; label: string }
> = {
  anchored: { variant: "success", label: "Anchored" },
  pending: { variant: "warning", label: "Pending" },
  failed: { variant: "error", label: "Failed" },
};

const EVENT_LABELS: Record<string, string> = {
  document_upload: "Document Upload",
  signal_score: "Signal Score",
  certification: "Certification",
  deal_transition: "Deal Transition",
  lp_report_approval: "LP Report Approval",
};

function AnchorRow({ anchor }: { anchor: AnchorResponse }) {
  const cfg = STATUS_CONFIG[anchor.status] ?? {
    variant: "neutral" as const,
    label: anchor.status,
  };
  return (
    <tr className="border-b hover:bg-neutral-50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {anchor.status === "anchored" ? (
            <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
          ) : anchor.status === "failed" ? (
            <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
          ) : (
            <Clock className="h-4 w-4 text-amber-400 flex-shrink-0" />
          )}
          <Badge variant={cfg.variant}>{cfg.label}</Badge>
        </div>
      </td>
      <td className="px-4 py-3">
        <p className="text-xs font-medium text-neutral-800">
          {EVENT_LABELS[anchor.event_type] ?? anchor.event_type}
        </p>
        <p className="text-[10px] text-neutral-400 capitalize">
          {anchor.entity_type}
        </p>
      </td>
      <td className="px-4 py-3 font-mono text-[10px] text-neutral-600 max-w-[180px] truncate">
        {anchor.data_hash}
      </td>
      <td className="px-4 py-3 font-mono text-[10px] text-neutral-600">
        {anchor.tx_hash ? (
          <a
            href={`https://polygonscan.com/tx/${anchor.tx_hash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-primary-600 hover:underline"
          >
            {anchor.tx_hash.slice(0, 10)}...
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-neutral-500">
        {anchor.anchored_at
          ? new Date(anchor.anchored_at).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
            })
          : "—"}
      </td>
    </tr>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function BlockchainAuditPage() {
  const [filter, setFilter] = useState<"all" | "anchored" | "pending" | "failed">("all");

  const { data, isLoading, refetch } = useAuditReport();
  const batchSubmit = useBatchSubmit();

  const filtered = (data?.items ?? []).filter(
    (a) => filter === "all" || a.status === filter
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Link2 className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Blockchain Audit Trail
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Immutable audit log of platform events anchored on Polygon
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
          <Button
            onClick={() => batchSubmit.mutate()}
            disabled={batchSubmit.isPending}
          >
            <ShieldCheck className="mr-2 h-4 w-4" />
            Submit Pending Batch
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !data ? (
        <EmptyState
          icon={<Shield className="h-12 w-12 text-neutral-400" />}
          title="No audit records"
          description="Blockchain anchors are created automatically when key platform events occur."
        />
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg flex-shrink-0">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Anchored</p>
                  <p className="text-2xl font-bold text-green-700">
                    {data.anchored}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg flex-shrink-0">
                  <Clock className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Pending</p>
                  <p className="text-2xl font-bold text-amber-700">
                    {data.pending}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-primary-100 rounded-lg flex-shrink-0">
                  <Shield className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Total Events</p>
                  <p className="text-2xl font-bold text-primary-700">
                    {data.total}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-2">
            {(["all", "anchored", "pending", "failed"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors ${
                  filter === f
                    ? "bg-primary-600 text-white"
                    : "bg-white text-neutral-600 border border-neutral-200 hover:bg-neutral-50"
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
                {f !== "all" && (
                  <span className="ml-1.5 text-xs opacity-70">
                    {data.items.filter((a) => a.status === f).length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Anchors table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                Audit Records ({filtered.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {filtered.length === 0 ? (
                <div className="py-12 text-center text-sm text-neutral-400">
                  No records match the current filter.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-neutral-50">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Status
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Event
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Data Hash
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          TX Hash
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Anchored
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((anchor) => (
                        <AnchorRow key={anchor.id} anchor={anchor} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Info */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <ShieldCheck className="h-5 w-5 text-primary-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-neutral-800">
                    How It Works
                  </p>
                  <p className="text-xs text-neutral-500 mt-1 leading-relaxed">
                    Critical platform events (document uploads, certifications,
                    deal transitions) are hashed using SHA-256 and grouped into
                    Merkle trees. The Merkle root is anchored on Polygon every
                    hour, creating an immutable proof of integrity that can be
                    verified by any third party without accessing your private
                    data.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
