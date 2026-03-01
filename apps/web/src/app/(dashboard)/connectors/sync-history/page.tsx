"use client";

import { useState } from "react";
import { RefreshCw, CheckCircle, XCircle, AlertCircle, ArrowRightLeft } from "lucide-react";
import {
  useCRMConnections,
  useSyncLogs,
  useTriggerSync,
  type CRMConnection,
  type SyncLog,
} from "@/lib/crm";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function statusBadge(status: string) {
  if (status === "success") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        <CheckCircle className="h-3 w-3" />
        Success
      </span>
    );
  }
  if (status === "error" || status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        <XCircle className="h-3 w-3" />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
      <AlertCircle className="h-3 w-3" />
      {status}
    </span>
  );
}

function directionBadge(direction: string) {
  const isInbound = direction === "inbound";
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        isInbound
          ? "bg-blue-100 text-blue-700"
          : "bg-violet-100 text-violet-700"
      }`}
    >
      {isInbound ? "Inbound" : "Outbound"}
    </span>
  );
}

// ── Connection card ────────────────────────────────────────────────────────

function ConnectionCard({
  conn,
  isSelected,
  onSelect,
}: {
  conn: CRMConnection;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const triggerSync = useTriggerSync();

  return (
    <button
      onClick={onSelect}
      className={`w-full rounded-lg border p-4 text-left transition-all ${
        isSelected
          ? "border-primary-500 bg-primary-50"
          : "border-neutral-200 bg-white hover:border-neutral-300"
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-neutral-900">{conn.connection_name}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {conn.provider} · {conn.sync_direction}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${conn.is_active ? "bg-green-400" : "bg-neutral-300"}`}
          />
          <span className="text-xs text-neutral-500">{conn.is_active ? "Active" : "Inactive"}</span>
        </div>
      </div>
      {conn.last_synced_at && (
        <p className="mt-2 text-xs text-neutral-400">Last sync: {formatDate(conn.last_synced_at)}</p>
      )}
      {conn.error_count > 0 && (
        <p className="mt-1 text-xs text-red-500">{conn.error_count} error{conn.error_count > 1 ? "s" : ""}</p>
      )}
      {isSelected && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            triggerSync.mutate(conn.id);
          }}
          disabled={triggerSync.isPending}
          className="mt-3 flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium text-primary-700 border border-primary-200 hover:bg-primary-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-3 w-3 ${triggerSync.isPending ? "animate-spin" : ""}`} />
          {triggerSync.isPending ? "Syncing…" : "Trigger Sync"}
        </button>
      )}
    </button>
  );
}

// ── Sync log row ───────────────────────────────────────────────────────────

function SyncLogRow({ log }: { log: SyncLog }) {
  return (
    <tr className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <td className="px-4 py-3 text-xs text-neutral-500 font-mono">{formatDate(log.created_at)}</td>
      <td className="px-4 py-3">{directionBadge(log.direction)}</td>
      <td className="px-4 py-3 text-sm text-neutral-700">{log.entity_type}</td>
      <td className="px-4 py-3 text-sm text-neutral-700">{log.action}</td>
      <td className="px-4 py-3">{statusBadge(log.status)}</td>
      <td className="px-4 py-3">
        {log.error_message ? (
          <span className="text-xs text-red-600 line-clamp-2">{log.error_message}</span>
        ) : (
          <span className="text-xs text-neutral-300">—</span>
        )}
      </td>
    </tr>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function SyncHistoryPage() {
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>("");

  const { data: connections, isLoading: connectionsLoading } = useCRMConnections();
  const { data: logs, isLoading: logsLoading } = useSyncLogs(selectedConnectionId || undefined);

  const allConnections: CRMConnection[] = connections ?? [];
  const allLogs: SyncLog[] = logs ?? [];

  const successCount = allLogs.filter((l) => l.status === "success").length;
  const failedCount = allLogs.filter((l) => l.status === "error" || l.status === "failed").length;
  const inboundCount = allLogs.filter((l) => l.direction === "inbound").length;
  const outboundCount = allLogs.filter((l) => l.direction === "outbound").length;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-100">
          <RefreshCw className="h-5 w-5 text-cyan-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">CRM Sync History</h1>
          <p className="text-sm text-neutral-500">Review sync logs across all CRM connections</p>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Connection list */}
        <div className="col-span-4 space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-neutral-400">
            Connections ({allConnections.length})
          </h2>
          {connectionsLoading ? (
            <div className="space-y-3 animate-pulse">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-20 rounded-lg border border-neutral-200 bg-neutral-100" />
              ))}
            </div>
          ) : allConnections.length === 0 ? (
            <div className="rounded-lg border border-neutral-200 bg-white py-8 text-center text-sm text-neutral-400">
              No connections found
            </div>
          ) : (
            allConnections.map((conn) => (
              <ConnectionCard
                key={conn.id}
                conn={conn}
                isSelected={selectedConnectionId === conn.id}
                onSelect={() =>
                  setSelectedConnectionId(
                    selectedConnectionId === conn.id ? "" : conn.id
                  )
                }
              />
            ))
          )}
        </div>

        {/* Sync log detail */}
        <div className="col-span-8 space-y-4">
          {/* Stats bar */}
          {selectedConnectionId && (
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-neutral-200 bg-white p-3">
                <p className="text-xs text-neutral-500">Total Logs</p>
                <p className="text-xl font-bold text-neutral-900">{allLogs.length}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-3">
                <p className="text-xs text-neutral-500">Successful</p>
                <p className="text-xl font-bold text-green-600">{successCount}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-3">
                <p className="text-xs text-neutral-500">Failed</p>
                <p className="text-xl font-bold text-red-500">{failedCount}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-3">
                <p className="text-xs text-neutral-500">In / Out</p>
                <p className="text-xl font-bold text-neutral-900">
                  {inboundCount} / {outboundCount}
                </p>
              </div>
            </div>
          )}

          {/* Log table */}
          <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
            <div className="border-b border-neutral-200 px-4 py-3 flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-neutral-400" />
              <h2 className="text-sm font-semibold text-neutral-900">
                {selectedConnectionId ? "Sync Logs" : "Select a connection to view logs"}
              </h2>
            </div>

            {logsLoading ? (
              <div className="animate-pulse">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="border-b border-neutral-100 px-4 py-4 flex gap-4">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
                    ))}
                  </div>
                ))}
              </div>
            ) : !selectedConnectionId ? (
              <div className="py-16 text-center text-neutral-400 text-sm">
                Select a connection from the left to view its sync history
              </div>
            ) : allLogs.length === 0 ? (
              <div className="py-16 text-center text-neutral-400 text-sm">No data available</div>
            ) : (
              <table className="w-full text-left">
                <thead className="border-b border-neutral-200 bg-neutral-50">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Timestamp</th>
                    <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Direction</th>
                    <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Entity Type</th>
                    <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Action</th>
                    <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Status</th>
                    <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {allLogs.map((log) => (
                    <SyncLogRow key={log.id} log={log} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
