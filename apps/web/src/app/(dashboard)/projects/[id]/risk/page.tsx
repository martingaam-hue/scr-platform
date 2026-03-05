"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  cn,
} from "@scr/ui";
import {
  useAlleyRiskDetail,
  useAlleyRiskProgress,
  useUpdateMitigation,
  useRunRiskCheck,
  severityClasses,
  riskScoreColor,
  MITIGATION_STATUS_LABELS,
  DOMAIN_LABELS,
  type RiskItemSummary,
} from "@/lib/alley-risk";

// ── Risk Arc ─────────────────────────────────────────────────────────────────

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
function describeArc(cx: number, cy: number, r: number, start: number, end: number) {
  const s = polarToCartesian(cx, cy, r, end);
  const e = polarToCartesian(cx, cy, r, start);
  const la = end - start <= 180 ? "0" : "1";
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${la} 0 ${e.x} ${e.y}`;
}

function RiskArc({ score, size = 120, strokeWidth = 12 }: { score: number; size?: number; strokeWidth?: number }) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const radius = (size - strokeWidth) / 2;
  const color = riskScoreColor(clamped);
  const cx = size / 2;
  const cy = size / 2;
  return (
    <svg
      width={size}
      height={size / 2 + strokeWidth}
      viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}
      className="overflow-visible"
    >
      <path
        d={describeArc(cx, cy, radius, 180, 360)}
        fill="none"
        stroke="rgba(255,255,255,0.22)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
      {clamped > 0 && (
        <path
          d={describeArc(cx, cy, radius, 180, 180 + (clamped / 100) * 180)}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}

// ── Severity Chip ─────────────────────────────────────────────────────────────

function SeverityChip({ severity }: { severity: string }) {
  const c = severityClasses(severity);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold border",
        c.bg,
        c.text,
        c.border
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", c.dot)} />
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

// ── Risk Item Card ────────────────────────────────────────────────────────────

function RiskItemCard({
  item,
  projectId,
}: {
  item: RiskItemSummary;
  projectId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState(item.mitigation_status);
  const [notes, setNotes] = useState(item.notes ?? "");
  const updateMitigation = useUpdateMitigation();

  const handleStatusChange = async (status: string) => {
    setSelectedStatus(status);
    await updateMitigation.mutateAsync({ projectId, riskId: item.id, status, notes });
  };

  const handleSaveNotes = async () => {
    await updateMitigation.mutateAsync({ projectId, riskId: item.id, status: selectedStatus, notes });
  };

  return (
    <Card className="overflow-hidden">
      <button
        className="w-full text-left px-5 py-4 hover:bg-neutral-50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <SeverityChip severity={item.severity} />
              <Badge variant="neutral" className="text-xs">
                {DOMAIN_LABELS[item.dimension] ?? item.dimension}
              </Badge>
              {item.source === "auto" && (
                <Badge variant="info" className="text-xs">AI Identified</Badge>
              )}
            </div>
            <h3 className="font-semibold text-neutral-900 text-sm leading-snug">
              {item.title}
            </h3>
            {!expanded && (
              <p className="text-xs text-neutral-500 mt-1 line-clamp-1">
                {item.description}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-neutral-500">
              {MITIGATION_STATUS_LABELS[item.mitigation_status] ?? item.mitigation_status}
            </span>
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-neutral-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-neutral-400" />
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t px-5 pb-5 pt-4 space-y-4">
          {/* Description */}
          <p className="text-sm text-neutral-700">{item.description}</p>

          {/* Guidance */}
          {item.guidance && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
                Recommended Mitigation
              </p>
              <p className="text-sm text-neutral-700">{item.guidance}</p>
            </div>
          )}

          {/* Status update */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
              Mitigation Status
            </label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(MITIGATION_STATUS_LABELS).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  disabled={updateMitigation.isPending}
                  onClick={() => handleStatusChange(value)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                    selectedStatus === value
                      ? "bg-primary-600 text-white border-primary-600"
                      : "bg-white text-neutral-600 border-neutral-200 hover:border-primary-300"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
              Notes
            </label>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={2}
              placeholder="Add mitigation notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div className="flex justify-end">
              <Button
                size="sm"
                variant="outline"
                onClick={handleSaveNotes}
                disabled={updateMitigation.isPending}
              >
                {updateMitigation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                ) : null}
                Save Notes
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProjectRiskPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const { data: detail, isLoading } = useAlleyRiskDetail(id);
  const { data: progress } = useAlleyRiskProgress(id);
  const runCheck = useRunRiskCheck();

  const risks = detail?.risk_items ?? [];

  const filtered =
    severityFilter === "all"
      ? risks
      : risks.filter((r) => r.severity.toLowerCase() === severityFilter);

  const criticalCount = risks.filter((r) => r.severity === "critical").length;
  const highCount = risks.filter((r) => r.severity === "high").length;
  const mediumCount = risks.filter((r) => r.severity === "medium").length;
  const lowCount = risks.filter((r) => r.severity === "low").length;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.push(`/projects/${id}`)}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Project
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Risk Dashboard</h1>
            <p className="mt-1 text-sm text-neutral-500">
              AI-identified and manually logged risk items with mitigation tracking.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => runCheck.mutate(id)}
            disabled={runCheck.isPending}
          >
            {runCheck.isPending ? (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-1.5" />
            )}
            Run New Check
          </Button>
        </div>
      </div>

      {/* Hero card */}
      {detail && (
        <Card className="bg-primary-600 border-primary-700">
          <CardContent className="px-8 pt-8 pb-6">
            <div className="flex items-center gap-8">
              <div className="shrink-0">
                <RiskArc score={detail.overall_risk_score} size={120} strokeWidth={12} />
              </div>
              <div className="flex-1">
                <p
                  className="text-5xl font-bold tabular-nums leading-none"
                  style={{ color: riskScoreColor(detail.overall_risk_score) }}
                >
                  {detail.overall_risk_score}
                </p>
                <p className="mt-1 text-lg font-medium text-white/80">Overall Risk Score</p>
                <div className="mt-4 flex flex-wrap gap-4">
                  {criticalCount > 0 && (
                    <div className="text-center">
                      <p className="text-xl font-bold text-white">{criticalCount}</p>
                      <p className="text-xs text-white/60">Critical</p>
                    </div>
                  )}
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{highCount}</p>
                    <p className="text-xs text-white/60">High</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{mediumCount}</p>
                    <p className="text-xs text-white/60">Medium</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{lowCount}</p>
                    <p className="text-xs text-white/60">Low</p>
                  </div>
                </div>
              </div>
              {progress && (
                <div className="shrink-0 text-right hidden sm:block">
                  <p className="text-3xl font-bold text-white">
                    {Math.round(progress.progress_pct)}%
                  </p>
                  <p className="text-xs text-white/60 mt-0.5">Mitigation Progress</p>
                  <div className="mt-2 h-2 w-32 rounded-full bg-white/20 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-white"
                      style={{ width: `${progress.progress_pct}%` }}
                    />
                  </div>
                  <p className="text-xs text-white/50 mt-1">
                    {progress.addressed}/{progress.total_risks} addressed
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Severity filter tabs */}
      {risks.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {[
            { value: "all", label: `All (${risks.length})` },
            ...(criticalCount > 0 ? [{ value: "critical", label: `Critical (${criticalCount})` }] : []),
            ...(highCount > 0 ? [{ value: "high", label: `High (${highCount})` }] : []),
            ...(mediumCount > 0 ? [{ value: "medium", label: `Medium (${mediumCount})` }] : []),
            ...(lowCount > 0 ? [{ value: "low", label: `Low (${lowCount})` }] : []),
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSeverityFilter(opt.value)}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
                severityFilter === opt.value
                  ? "bg-primary-600 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {risks.length === 0 && (
        <EmptyState
          icon={<ShieldAlert className="h-12 w-12 text-neutral-400" />}
          title="No risks identified yet"
          description="Run a risk check to automatically identify risks across technical, financial, regulatory, ESG, and market dimensions."
          action={
            <Button onClick={() => runCheck.mutate(id)} disabled={runCheck.isPending}>
              {runCheck.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Run First Check
            </Button>
          }
        />
      )}

      {/* Risk items */}
      {filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map((item) => (
            <RiskItemCard key={item.id} item={item} projectId={id} />
          ))}
        </div>
      )}

      {filtered.length === 0 && risks.length > 0 && (
        <p className="text-center text-sm text-neutral-400 py-8">
          No risks at this severity level.
        </p>
      )}
    </div>
  );
}
