"use client";

import { useState } from "react";
import { Link2, X } from "lucide-react";
import { cn } from "@scr/ui";
import { useLineageTrace, type LineageRecord } from "@/lib/lineage";

// ── Types ──────────────────────────────────────────────────────────────────

interface LineagePanelProps {
  entityType: string;
  entityId: string;
  fieldName: string;
  /** Human-readable label for the field, e.g. "Enterprise Value" */
  fieldLabel: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function sourceTypeBadgeClass(sourceType: string): string {
  switch (sourceType) {
    case "document":
      return "bg-blue-100 text-blue-700";
    case "ai_inference":
      return "bg-purple-100 text-purple-700";
    case "user_input":
      return "bg-green-100 text-green-700";
    case "calculation":
      return "bg-amber-100 text-amber-700";
    case "external_api":
      return "bg-cyan-100 text-cyan-700";
    default:
      return "bg-neutral-100 text-neutral-600";
  }
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

// ── Lineage record row ─────────────────────────────────────────────────────

function LineageRecordRow({
  record,
  index,
  total,
}: {
  record: LineageRecord;
  index: number;
  total: number;
}) {
  return (
    <div className="relative flex gap-3">
      {/* Timeline vertical line */}
      <div className="flex flex-col items-center">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border-2 border-neutral-300 bg-white text-xs font-semibold text-neutral-500">
          {total - index}
        </div>
        {index < total - 1 && (
          <div className="mt-1 w-0.5 flex-1 bg-neutral-200" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1 pb-4">
        <div className="flex flex-wrap items-center gap-1.5 mb-1">
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              sourceTypeBadgeClass(record.source_type)
            )}
          >
            {record.source_type.replace(/_/g, " ")}
          </span>
          <span className="text-xs text-neutral-400">
            {formatDate(record.recorded_at)}
          </span>
        </div>
        <p className="text-sm text-neutral-700 leading-snug">
          {record.source_detail}
        </p>
        {record.value_snapshot && (
          <p className="mt-0.5 text-xs text-neutral-500">
            Value: <span className="font-mono">{record.value_snapshot}</span>
          </p>
        )}
        {record.actor && (
          <p className="mt-0.5 text-xs text-neutral-400">by {record.actor}</p>
        )}
      </div>
    </div>
  );
}

// ── Sliding panel ──────────────────────────────────────────────────────────

function LineageDrawer({
  isOpen,
  onClose,
  fieldLabel,
  entityType,
  entityId,
  fieldName,
}: {
  isOpen: boolean;
  onClose: () => void;
  fieldLabel: string;
  entityType: string;
  entityId: string;
  fieldName: string;
}) {
  const { data, isLoading } = useLineageTrace(
    entityType,
    isOpen ? entityId : "",
    isOpen ? fieldName : ""
  );

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <div
        className={cn(
          "fixed right-0 top-0 z-50 flex h-full w-80 flex-col bg-white shadow-xl transition-transform duration-300",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
        aria-label={`Lineage panel for ${fieldLabel}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">
              Data Lineage
            </p>
            <h2 className="text-sm font-semibold text-neutral-900">
              {fieldLabel}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
            aria-label="Close lineage panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {isLoading && (
            <div className="flex h-24 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
            </div>
          )}

          {!isLoading && (!data || data.chain.length === 0) && (
            <p className="text-sm text-neutral-400">
              No lineage data available for this field.
            </p>
          )}

          {!isLoading && data && data.chain.length > 0 && (
            <div>
              <p className="mb-4 text-xs text-neutral-500">
                {data.chain.length} provenance record
                {data.chain.length !== 1 ? "s" : ""} — most recent first
              </p>
              <div>
                {data.chain.map((record, i) => (
                  <LineageRecordRow
                    key={record.id}
                    record={record}
                    index={i}
                    total={data.chain.length}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function LineagePanel({
  entityType,
  entityId,
  fieldName,
  fieldLabel,
}: LineagePanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!entityId) return null;

  return (
    <>
      <button
        type="button"
        title={`View data lineage for ${fieldLabel}`}
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center justify-center rounded p-0.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-blue-600"
        aria-label={`View lineage for ${fieldLabel}`}
      >
        <Link2 className="h-3.5 w-3.5" />
      </button>

      <LineageDrawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        fieldLabel={fieldLabel}
        entityType={entityType}
        entityId={entityId}
        fieldName={fieldName}
      />
    </>
  );
}
