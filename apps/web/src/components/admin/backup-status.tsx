"use client";

import { useBackupStatus } from "@/lib/backup";
import { Badge } from "@scr/ui";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Database,
  HardDrive,
  Search,
  Lock,
  Shield,
  RefreshCw,
  Server,
  Archive,
} from "lucide-react";
import { formatDistanceToNow, parseISO } from "date-fns";

function StatusBadge({ status }: { status: string }) {
  if (!status) return <Badge variant="neutral">Unknown</Badge>;
  const s = status.toLowerCase();
  if (["success", "ok", "pass", "accepted", "enabled"].some((v) => s.includes(v))) {
    return <Badge variant="success">OK</Badge>;
  }
  if (["failed", "fail", "error"].some((v) => s.includes(v))) {
    return <Badge variant="error">Failed</Badge>;
  }
  if (["warning", "stale", "partial", "empty"].some((v) => s.includes(v))) {
    return <Badge variant="warning">Warning</Badge>;
  }
  if (["skipped", "unknown"].some((v) => s.includes(v))) {
    return <Badge variant="neutral">Unknown</Badge>;
  }
  return <Badge variant="neutral">{status}</Badge>;
}

function StatusIcon({ status }: { status: string }) {
  const s = (status || "").toLowerCase();
  if (["success", "ok", "pass", "accepted", "enabled"].some((v) => s.includes(v))) {
    return <CheckCircle2 className="w-5 h-5 text-green-500" />;
  }
  if (["failed", "fail", "error"].some((v) => s.includes(v))) {
    return <XCircle className="w-5 h-5 text-red-500" />;
  }
  if (["warning", "stale", "partial", "empty"].some((v) => s.includes(v))) {
    return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
  }
  return <Clock className="w-5 h-5 text-gray-400" />;
}

function BackupRow({
  icon: Icon,
  label,
  status,
  detail,
}: {
  icon: React.ElementType;
  label: string;
  status: string;
  detail?: string;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-neutral-100 last:border-0">
      <div className="flex items-center gap-3">
        <Icon className="w-4 h-4 text-neutral-400" />
        <span className="text-sm font-medium text-neutral-700">{label}</span>
      </div>
      <div className="flex items-center gap-3">
        {detail && <span className="text-xs text-neutral-400">{detail}</span>}
        <StatusBadge status={status} />
      </div>
    </div>
  );
}

function formatAge(isoString: string | null | undefined): string {
  if (!isoString) return "Never";
  try {
    return formatDistanceToNow(parseISO(isoString), { addSuffix: true });
  } catch {
    return "Unknown";
  }
}

export function BackupStatusPanel() {
  const { data, isLoading, error, refetch, isFetching } = useBackupStatus();

  if (isLoading) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white p-6 animate-pulse">
        <div className="h-4 bg-neutral-100 rounded w-48 mb-4" />
        {[...Array(7)].map((_, i) => (
          <div key={i} className="h-10 bg-neutral-50 rounded mb-2" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <div className="flex items-center gap-2 text-red-700">
          <XCircle className="w-5 h-5" />
          <span className="font-medium">Backup status unavailable</span>
        </div>
        <p className="text-sm text-red-600 mt-1">Could not load backup status from S3.</p>
      </div>
    );
  }

  const overall = data?.overall ?? "unknown";
  const isHealthy = overall === "success";
  const isPartial = overall === "partial_failure";

  // Build detail strings
  const pgDetail = data?.postgresql?.size_mb
    ? `${data.postgresql.size_mb} MB${data.postgresql.verified ? " · verified" : ""}`
    : undefined;

  const drDetail = data?.dr_copy?.dr_region ? `→ ${data.dr_copy.dr_region}` : undefined;

  const rdsDetail =
    data?.rds_snapshots?.age_hours != null
      ? `${data.rds_snapshots.snapshot_count} snapshots · ${data.rds_snapshots.age_hours}h ago`
      : data?.rds_snapshots?.snapshot_count != null
        ? `${data.rds_snapshots.snapshot_count} snapshots`
        : undefined;

  const tableDetail =
    data?.table_audit?.table_count != null
      ? `${data.table_audit.table_count} tables (min: ${data.table_audit.expected_min ?? 113})`
      : undefined;

  const s3Detail = data?.s3_replication?.buckets
    ? Object.entries(data.s3_replication.buckets)
        .map(([b, s]) => `${b.split("-").slice(-1)[0]}: ${s}`)
        .join(", ")
    : undefined;

  const restoreDetail = data?.last_restore_test ? formatAge(data.last_restore_test) : undefined;

  return (
    <div className="rounded-xl border border-neutral-200 bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
        <div className="flex items-center gap-3">
          <StatusIcon status={overall} />
          <div>
            <h3 className="text-sm font-semibold text-neutral-900">Backup & Recovery</h3>
            <p className="text-xs text-neutral-500">Last run: {formatAge(data?.last_run)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
              isHealthy
                ? "bg-green-50 text-green-700"
                : isPartial
                  ? "bg-yellow-50 text-yellow-700"
                  : "bg-neutral-100 text-neutral-600"
            }`}
          >
            {isHealthy ? "All Systems OK" : isPartial ? "Partial Failure" : "No Data"}
          </span>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-1.5 rounded-md hover:bg-neutral-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw
              className={`w-4 h-4 text-neutral-400 ${isFetching ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>

      {/* Backup checks */}
      <div className="px-6 divide-y divide-neutral-50">
        <BackupRow
          icon={Database}
          label="PostgreSQL Backup"
          status={data?.postgresql?.status ?? "unknown"}
          detail={pgDetail}
        />
        <BackupRow
          icon={Shield}
          label="Cross-Region DR Copy"
          status={data?.dr_copy?.status ?? "unknown"}
          detail={drDetail}
        />
        <BackupRow
          icon={Server}
          label="RDS Automated Snapshots"
          status={data?.rds_snapshots?.status ?? "unknown"}
          detail={rdsDetail}
        />
        <BackupRow
          icon={HardDrive}
          label="S3 Cross-Region Replication"
          status={data?.s3_replication?.status ?? "unknown"}
          detail={s3Detail}
        />
        <BackupRow
          icon={Search}
          label="OpenSearch Snapshot"
          status={data?.opensearch?.status ?? "unknown"}
          detail={data?.opensearch?.snapshot}
        />
        <BackupRow
          icon={Lock}
          label="Secrets Inventory"
          status={data?.secrets_inventory?.status ?? "unknown"}
          detail={
            data?.secrets_inventory?.secret_count != null
              ? `${data.secrets_inventory.secret_count} secrets`
              : undefined
          }
        />
        <BackupRow
          icon={Archive}
          label="Database Table Audit"
          status={data?.table_audit?.status ?? "unknown"}
          detail={tableDetail}
        />
      </div>

      {/* Restore test footer */}
      <div className="px-6 py-4 border-t border-neutral-100 bg-neutral-50 rounded-b-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4 text-neutral-400" />
            <span className="text-xs text-neutral-600">
              Last restore test:{" "}
              <span className="font-medium">{restoreDetail ?? "Not yet run"}</span>
            </span>
          </div>
          {data?.restore_test_result && (
            <StatusBadge status={data.restore_test_result} />
          )}
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-neutral-500">
          <div>
            <span className="font-medium">RTO target:</span> &lt;4h (region failure)
          </div>
          <div>
            <span className="font-medium">RPO target:</span> &lt;1h (critical data)
          </div>
          <div>
            <span className="font-medium">Restore test:</span> Weekly (Sunday 05:00 UTC)
          </div>
        </div>
      </div>
    </div>
  );
}
