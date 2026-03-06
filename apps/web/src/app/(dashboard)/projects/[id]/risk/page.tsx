"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  ClipboardCopy,
  Download,
  Loader2,
  RefreshCw,
  Save,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
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
import {
  useGenerateBusinessPlan,
  useBusinessPlanResult,
} from "@/lib/business-plan";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

// ── Risk Arc ──────────────────────────────────────────────────────────────

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
function describeArc(
  cx: number,
  cy: number,
  r: number,
  start: number,
  end: number
) {
  const s = polarToCartesian(cx, cy, r, end);
  const e = polarToCartesian(cx, cy, r, start);
  const la = end - start <= 180 ? "0" : "1";
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${la} 0 ${e.x} ${e.y}`;
}

function RiskArc({
  score,
  size = 120,
  strokeWidth = 12,
}: {
  score: number;
  size?: number;
  strokeWidth?: number;
}) {
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

// ── Severity Chip ─────────────────────────────────────────────────────────

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

// ── Alert severity badge (bild16 style) ───────────────────────────────────

function AlertBadge({ severity }: { severity: string }) {
  const s = severity.toUpperCase();
  const styles =
    s === "HIGH" || s === "CRITICAL"
      ? "bg-red-500 text-white"
      : s === "MEDIUM"
        ? "bg-amber-400 text-white"
        : "bg-neutral-200 text-neutral-600";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-bold tracking-wide shrink-0",
        styles
      )}
    >
      {s}
    </span>
  );
}

// ── Mitigation Strategy Generator ─────────────────────────────────────────

function MitigationStrategyPanel({
  projectId,
  riskTitle,
}: {
  projectId: string;
  riskTitle: string;
}) {
  const [taskLogId, setTaskLogId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const qc = useQueryClient();
  const generate = useGenerateBusinessPlan(projectId);
  const { data: result } = useBusinessPlanResult(
    projectId,
    taskLogId ?? undefined
  );

  const isPending =
    generate.isPending ||
    result?.status === "pending" ||
    result?.status === "processing";
  const isComplete = result?.status === "completed";

  const handleGenerate = async () => {
    const res = await generate.mutateAsync("risk_narrative");
    setTaskLogId(res.task_log_id);
  };

  const handleCopy = () => {
    if (result?.content) {
      navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSave = async () => {
    if (!result?.content) return;
    try {
      await api.post("/legal/documents", {
        template_id: null,
        title: `Mitigation Strategy — ${riskTitle}`,
        content: result.content,
      });
      qc.invalidateQueries({ queryKey: ["legal-documents"] });
    } catch {
      // silent
    }
  };

  const handleDownload = () => {
    if (!result?.content) return;
    const blob = new Blob([result.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Mitigation_Strategy_${riskTitle.replace(/\s+/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-3 border-t pt-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
          AI Mitigation Strategy
        </span>
        {!isComplete && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleGenerate}
            disabled={isPending}
            className="h-7 text-xs px-2"
          >
            {isPending ? (
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
            ) : (
              <Sparkles className="h-3 w-3 mr-1" />
            )}
            {isPending ? "Generating…" : "Generate Mitigation Strategy"}
          </Button>
        )}
        {isComplete && (
          <div className="flex gap-1.5">
            <Button
              size="sm"
              variant="outline"
              onClick={handleCopy}
              className="h-7 text-xs px-2"
            >
              <ClipboardCopy className="h-3 w-3 mr-1" />
              {copied ? "Copied!" : "Copy"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSave}
              className="h-7 text-xs px-2"
            >
              <Save className="h-3 w-3 mr-1" />
              Save
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleDownload}
              className="h-7 text-xs px-2"
            >
              <Download className="h-3 w-3 mr-1" />
              Download
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerate}
              disabled={isPending}
              className="h-7 text-xs px-2"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Regenerate
            </Button>
          </div>
        )}
      </div>

      {isComplete && result.content && (
        <div className="text-sm text-neutral-700 bg-neutral-50 rounded-lg p-3 border border-neutral-200 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
          {result.content}
        </div>
      )}
    </div>
  );
}

// ── Risk Item Card ────────────────────────────────────────────────────────

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
    await updateMitigation.mutateAsync({
      projectId,
      riskId: item.id,
      status,
      notes,
    });
  };

  const handleSaveNotes = async () => {
    await updateMitigation.mutateAsync({
      projectId,
      riskId: item.id,
      status: selectedStatus,
      notes,
    });
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
                <Badge variant="info" className="text-xs">
                  AI Identified
                </Badge>
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
              {MITIGATION_STATUS_LABELS[item.mitigation_status] ??
                item.mitigation_status}
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
          <p className="text-sm text-neutral-700">{item.description}</p>

          {item.guidance && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
                Recommended Mitigation
              </p>
              <p className="text-sm text-neutral-700">{item.guidance}</p>
            </div>
          )}

          {/* Mitigation status */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
              Mitigation Status
            </label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(MITIGATION_STATUS_LABELS).map(
                ([value, label]) => (
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
                )
              )}
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

          {/* AI Mitigation Strategy */}
          <MitigationStrategyPanel
            projectId={projectId}
            riskTitle={item.title}
          />
        </div>
      )}
    </Card>
  );
}

// ── Domain section (from risk-analysis, embedded) ─────────────────────────

const DOMAIN_ORDER = ["regulatory", "financial", "technical", "esg", "market"];

function domainRiskLevel(
  items: RiskItemSummary[]
): "critical" | "high" | "medium" | "low" | "clear" {
  if (items.some((r) => r.severity === "critical")) return "critical";
  if (items.some((r) => r.severity === "high")) return "high";
  if (items.some((r) => r.severity === "medium")) return "medium";
  if (items.length > 0) return "low";
  return "clear";
}

function DomainStatusBadge({
  level,
}: {
  level: ReturnType<typeof domainRiskLevel>;
}) {
  const map: Record<
    string,
    {
      label: string;
      variant: "error" | "warning" | "success" | "neutral";
    }
  > = {
    critical: { label: "Critical", variant: "error" },
    high: { label: "High Risk", variant: "error" },
    medium: { label: "Medium Risk", variant: "warning" },
    low: { label: "Low Risk", variant: "neutral" },
    clear: { label: "Clear", variant: "success" },
  };
  const { label, variant } = map[level];
  return (
    <Badge variant={variant} className="text-xs">
      {label}
    </Badge>
  );
}

function MitigationStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "mitigated":
    case "accepted":
      return <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />;
    case "in_progress":
      return (
        <Loader2 className="h-4 w-4 text-amber-500 shrink-0 animate-spin" />
      );
    default:
      return <Circle className="h-4 w-4 text-neutral-300 shrink-0" />;
  }
}

function DomainSection({
  domain,
  items,
  projectId,
}: {
  domain: string;
  items: RiskItemSummary[];
  projectId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const updateMitigation = useUpdateMitigation();
  const level = domainRiskLevel(items);
  const c = severityClasses(level === "clear" ? "low" : level);

  const addressed = items.filter(
    (r) =>
      r.mitigation_status === "mitigated" || r.mitigation_status === "accepted"
  ).length;

  return (
    <Card className="overflow-hidden">
      <button
        className="w-full text-left px-5 py-4 hover:bg-neutral-50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "h-10 w-10 rounded-lg flex items-center justify-center",
                c.bg
              )}
            >
              <ShieldCheck className={cn("h-5 w-5", c.text)} />
            </div>
            <div>
              <p className="font-semibold text-neutral-900 text-sm">
                {DOMAIN_LABELS[domain] ?? domain}
              </p>
              <p className="text-xs text-neutral-500">
                {items.length} risk{items.length !== 1 ? "s" : ""} ·{" "}
                {addressed} addressed
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <DomainStatusBadge level={level} />
            {items.length > 0 && (
              <div className="flex gap-1">
                {items.filter((r) => r.severity === "critical").length > 0 && (
                  <span className="h-5 w-5 rounded-full bg-black text-white text-xs flex items-center justify-center font-bold">
                    {items.filter((r) => r.severity === "critical").length}
                  </span>
                )}
                {items.filter((r) => r.severity === "high").length > 0 && (
                  <span className="h-5 w-5 rounded-full bg-red-100 text-red-700 text-xs flex items-center justify-center font-bold">
                    {items.filter((r) => r.severity === "high").length}
                  </span>
                )}
                {items.filter((r) => r.severity === "medium").length > 0 && (
                  <span className="h-5 w-5 rounded-full bg-amber-100 text-amber-700 text-xs flex items-center justify-center font-bold">
                    {items.filter((r) => r.severity === "medium").length}
                  </span>
                )}
              </div>
            )}
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-neutral-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-neutral-400" />
            )}
          </div>
        </div>
      </button>

      {expanded && items.length > 0 && (
        <div className="border-t divide-y divide-neutral-100">
          {items.map((item) => {
            const sc = severityClasses(item.severity);
            return (
              <div
                key={item.id}
                className="px-5 py-3 flex items-start gap-3 hover:bg-neutral-50"
              >
                <MitigationStatusIcon status={item.mitigation_status} />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-0.5">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold border",
                        sc.bg,
                        sc.text,
                        sc.border
                      )}
                    >
                      <span
                        className={cn("h-1.5 w-1.5 rounded-full", sc.dot)}
                      />
                      {item.severity.charAt(0).toUpperCase() +
                        item.severity.slice(1)}
                    </span>
                    {item.source === "auto" && (
                      <Badge variant="info" className="text-xs">
                        AI
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm font-medium text-neutral-900">
                    {item.title}
                  </p>
                  {item.description && (
                    <p className="text-xs text-neutral-500 mt-0.5 line-clamp-2">
                      {item.description}
                    </p>
                  )}
                </div>
                <select
                  className="shrink-0 text-xs border rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={item.mitigation_status}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) =>
                    updateMitigation.mutate({
                      projectId,
                      riskId: item.id,
                      status: e.target.value,
                    })
                  }
                >
                  {Object.entries(MITIGATION_STATUS_LABELS).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    )
                  )}
                </select>
              </div>
            );
          })}
        </div>
      )}

      {expanded && items.length === 0 && (
        <div className="border-t px-5 py-4 text-sm text-neutral-400 text-center">
          No risks identified in this domain.
        </div>
      )}
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function ProjectRiskPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [activeView, setActiveView] = useState<"alerts" | "all" | "domains">(
    "alerts"
  );

  const { data: detail, isLoading } = useAlleyRiskDetail(id);
  const { data: progress } = useAlleyRiskProgress(id);
  const runCheck = useRunRiskCheck();

  const risks = detail?.risk_items ?? [];

  // Alert-style: unaddressed high/critical/medium risks
  const activeAlerts = risks
    .filter(
      (r) =>
        r.mitigation_status === "unaddressed" ||
        r.mitigation_status === "acknowledged"
    )
    .sort((a, b) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return (
        (order[a.severity as keyof typeof order] ?? 4) -
        (order[b.severity as keyof typeof order] ?? 4)
      );
    });

  const filtered =
    severityFilter === "all"
      ? risks
      : risks.filter((r) => r.severity.toLowerCase() === severityFilter);

  const criticalCount = risks.filter((r) => r.severity === "critical").length;
  const highCount = risks.filter((r) => r.severity === "high").length;
  const mediumCount = risks.filter((r) => r.severity === "medium").length;
  const lowCount = risks.filter((r) => r.severity === "low").length;

  // Status derived from unaddressed count
  const statusLabel =
    activeAlerts.length === 0
      ? "Active Monitoring"
      : activeAlerts.some(
            (r) => r.severity === "critical" || r.severity === "high"
          )
        ? "Needs Attention"
        : "Active Monitoring";
  const statusColor =
    statusLabel === "Active Monitoring" ? "text-green-600" : "text-amber-600";
  const statusDot =
    statusLabel === "Active Monitoring" ? "bg-green-500" : "bg-amber-500";

  // Last updated from most recent risk item (fallback to now)
  const lastUpdated =
    risks.length > 0
      ? new Date(
          Math.max(...risks.map((r) => new Date(r.id).getTime()))
        ).toLocaleDateString()
      : "—";

  // Domain grouping for domain view
  const byDomain = DOMAIN_ORDER.reduce<Record<string, RiskItemSummary[]>>(
    (acc, domain) => {
      acc[domain] = risks.filter((r) => r.dimension === domain);
      return acc;
    },
    {}
  );
  const otherDomains = [
    ...new Set(
      risks
        .map((r) => r.dimension)
        .filter((d) => !DOMAIN_ORDER.includes(d))
    ),
  ];

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
            <h1 className="text-2xl font-bold text-neutral-900">
              Risk Dashboard
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              Unified risk monitoring — severity tracking, active alerts, domain
              breakdown, and AI mitigation strategies.
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
                <RiskArc
                  score={detail.overall_risk_score}
                  size={120}
                  strokeWidth={12}
                />
              </div>
              <div className="flex-1">
                <p
                  className="text-5xl font-bold tabular-nums leading-none"
                  style={{ color: riskScoreColor(detail.overall_risk_score) }}
                >
                  {detail.overall_risk_score}
                </p>
                <p className="mt-1 text-lg font-medium text-white/80">
                  Overall Risk Score
                </p>
                <div className="mt-4 flex flex-wrap gap-4">
                  {criticalCount > 0 && (
                    <div className="text-center">
                      <p className="text-xl font-bold text-white">
                        {criticalCount}
                      </p>
                      <p className="text-xs text-white/60">Critical</p>
                    </div>
                  )}
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{highCount}</p>
                    <p className="text-xs text-white/60">High</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">
                      {mediumCount}
                    </p>
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
                  <p className="text-xs text-white/60 mt-0.5">
                    Mitigation Progress
                  </p>
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

      {/* Status cards row — bild16 style */}
      {detail && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className={cn("h-2 w-2 rounded-full shrink-0", statusDot)} />
                <span className="text-xs font-semibold text-neutral-500">
                  Status
                </span>
              </div>
              <p className={cn("text-sm font-semibold", statusColor)}>
                {statusLabel}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                <BarChart3 className="h-3.5 w-3.5 text-neutral-400" />
                <span className="text-xs font-semibold text-neutral-500">
                  Risk Items
                </span>
              </div>
              <p className="text-sm font-semibold text-neutral-900">
                {detail.total_risks} risk
                {detail.total_risks !== 1 ? "s" : ""} tracked
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                <RefreshCw className="h-3.5 w-3.5 text-neutral-400" />
                <span className="text-xs font-semibold text-neutral-500">
                  Last Update
                </span>
              </div>
              <p className="text-sm font-semibold text-neutral-900">
                {lastUpdated}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty state */}
      {risks.length === 0 && (
        <EmptyState
          icon={<ShieldAlert className="h-12 w-12 text-neutral-400" />}
          title="No risks identified yet"
          description="Run a risk check to automatically identify risks across technical, financial, regulatory, ESG, and market dimensions."
          action={
            <Button
              onClick={() => runCheck.mutate(id)}
              disabled={runCheck.isPending}
            >
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

      {/* Active Alerts — bild16 style */}
      {risks.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-neutral-500" />
              <h2 className="text-sm font-semibold text-neutral-900">
                Active Alerts
              </h2>
            </div>
            <span className="text-xs text-neutral-500 bg-neutral-100 rounded-full px-2.5 py-0.5 font-medium">
              {activeAlerts.length} alert
              {activeAlerts.length !== 1 ? "s" : ""}
            </span>
          </div>

          <Card>
            {activeAlerts.length === 0 ? (
              <CardContent className="p-4 text-center text-sm text-neutral-400">
                No active alerts — all identified risks have been addressed.
              </CardContent>
            ) : (
              <div className="divide-y divide-neutral-100">
                {activeAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <AlertBadge severity={alert.severity} />
                      <span className="text-sm text-neutral-800 truncate">
                        {alert.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-3">
                      <span className="text-xs text-neutral-400">
                        {DOMAIN_LABELS[alert.dimension] ?? alert.dimension}
                      </span>
                      <span className="text-xs text-neutral-500 font-medium">
                        1 item
                      </span>
                    </div>
                  </div>
                ))}

                {/* AI Analysis summary bar */}
                <div className="px-4 py-3 bg-neutral-50 border-t">
                  <p className="text-xs text-neutral-600 leading-relaxed">
                    <span className="font-semibold text-neutral-700">
                      AI Analysis:{" "}
                    </span>
                    {activeAlerts.length === 0
                      ? "All risk metrics are within acceptable thresholds. Continue monitoring to maintain compliance across all domains."
                      : activeAlerts.some(
                            (r) =>
                              r.severity === "critical" ||
                              r.severity === "high"
                          )
                        ? `${highCount + criticalCount} high-priority risk${highCount + criticalCount !== 1 ? "s" : ""} require immediate attention. Review mitigation strategies and update compliance documentation to reduce exposure.`
                        : `${activeAlerts.length} open alert${activeAlerts.length !== 1 ? "s" : ""} detected at medium or low severity. Automated monitoring continues — address flagged items to improve your risk score.`}
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* View selector tabs */}
      {risks.length > 0 && (
        <div className="flex items-center gap-1 border-b border-neutral-200">
          {[
            { value: "alerts" as const, label: "Severity View" },
            { value: "all" as const, label: "All Risks" },
            { value: "domains" as const, label: "Domain View" },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveView(tab.value)}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px",
                activeView === tab.value
                  ? "border-primary-600 text-primary-700"
                  : "border-transparent text-neutral-500 hover:text-neutral-700"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Severity View */}
      {risks.length > 0 && activeView === "alerts" && (
        <>
          <div className="flex flex-wrap gap-2">
            {[
              { value: "all", label: `All (${risks.length})` },
              ...(criticalCount > 0
                ? [
                    {
                      value: "critical",
                      label: `Critical (${criticalCount})`,
                    },
                  ]
                : []),
              ...(highCount > 0
                ? [{ value: "high", label: `High (${highCount})` }]
                : []),
              ...(mediumCount > 0
                ? [{ value: "medium", label: `Medium (${mediumCount})` }]
                : []),
              ...(lowCount > 0
                ? [{ value: "low", label: `Low (${lowCount})` }]
                : []),
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

          <div className="space-y-3">
            {filtered.map((item) => (
              <RiskItemCard key={item.id} item={item} projectId={id} />
            ))}
          </div>

          {filtered.length === 0 && risks.length > 0 && (
            <p className="text-center text-sm text-neutral-400 py-8">
              No risks at this severity level.
            </p>
          )}
        </>
      )}

      {/* All Risks View */}
      {risks.length > 0 && activeView === "all" && (
        <div className="space-y-3">
          {risks.map((item) => (
            <RiskItemCard key={item.id} item={item} projectId={id} />
          ))}
        </div>
      )}

      {/* Domain View */}
      {risks.length > 0 && activeView === "domains" && (
        <div className="space-y-3">
          {/* Summary stats */}
          {detail && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-2">
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs text-neutral-500 mb-1">Total Risks</p>
                  <p className="text-2xl font-bold text-neutral-900">
                    {detail.total_risks}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs text-neutral-500 mb-1">Unaddressed</p>
                  <p className="text-2xl font-bold text-red-600">
                    {risks.filter(
                      (r) =>
                        r.mitigation_status === "unaddressed" ||
                        r.mitigation_status === "acknowledged"
                    ).length}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs text-neutral-500 mb-1">Addressed</p>
                  <p className="text-2xl font-bold text-green-600">
                    {detail.addressed_risks}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs text-neutral-500 mb-1">Progress</p>
                  <p className="text-2xl font-bold text-primary-600">
                    {Math.round(detail.mitigation_progress_pct)}%
                  </p>
                  {progress && (
                    <div className="mt-1.5 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary-500"
                        style={{ width: `${progress.progress_pct}%` }}
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {DOMAIN_ORDER.map((domain) => (
            <DomainSection
              key={domain}
              domain={domain}
              items={byDomain[domain] ?? []}
              projectId={id}
            />
          ))}
          {otherDomains.map((domain) => (
            <DomainSection
              key={domain}
              domain={domain}
              items={risks.filter((r) => r.dimension === domain)}
              projectId={id}
            />
          ))}

          {/* Compliance note */}
          <Card className="bg-neutral-50 border-neutral-200">
            <CardContent className="p-4 flex gap-3">
              <ShieldCheck className="h-5 w-5 text-neutral-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-neutral-700">
                  Compliance Disclaimer
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Risk items are AI-generated based on project data and should
                  be reviewed by qualified legal and compliance professionals.
                  This is not legal or regulatory advice.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
