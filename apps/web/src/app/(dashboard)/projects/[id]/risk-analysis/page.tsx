"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  Circle,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  LoadingSpinner,
  cn,
} from "@scr/ui";
import {
  useAlleyRiskDetail,
  useAlleyRiskProgress,
  useUpdateMitigation,
  useRunRiskCheck,
  severityClasses,
  MITIGATION_STATUS_LABELS,
  DOMAIN_LABELS,
  type RiskItemSummary,
} from "@/lib/alley-risk";

// ── Domain section ────────────────────────────────────────────────────────────

const DOMAIN_ORDER = ["regulatory", "financial", "technical", "esg", "market"];

function domainRiskLevel(items: RiskItemSummary[]): "critical" | "high" | "medium" | "low" | "clear" {
  if (items.some((r) => r.severity === "critical")) return "critical";
  if (items.some((r) => r.severity === "high")) return "high";
  if (items.some((r) => r.severity === "medium")) return "medium";
  if (items.length > 0) return "low";
  return "clear";
}

function DomainStatusBadge({ level }: { level: ReturnType<typeof domainRiskLevel> }) {
  const map: Record<string, { label: string; variant: "error" | "warning" | "success" | "neutral" }> = {
    critical: { label: "Critical", variant: "error" },
    high: { label: "High Risk", variant: "error" },
    medium: { label: "Medium Risk", variant: "warning" },
    low: { label: "Low Risk", variant: "neutral" },
    clear: { label: "Clear", variant: "success" },
  };
  const { label, variant } = map[level];
  return <Badge variant={variant} className="text-xs">{label}</Badge>;
}

function MitigationStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "mitigated":
    case "accepted":
      return <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />;
    case "in_progress":
      return <Loader2 className="h-4 w-4 text-amber-500 shrink-0 animate-spin" />;
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
    (r) => r.mitigation_status === "mitigated" || r.mitigation_status === "accepted"
  ).length;

  return (
    <Card className="overflow-hidden">
      <button
        className="w-full text-left px-5 py-4 hover:bg-neutral-50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center", c.bg)}>
              <ShieldCheck className={cn("h-5 w-5", c.text)} />
            </div>
            <div>
              <p className="font-semibold text-neutral-900 text-sm">
                {DOMAIN_LABELS[domain] ?? domain}
              </p>
              <p className="text-xs text-neutral-500">
                {items.length} risk{items.length !== 1 ? "s" : ""} · {addressed} addressed
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
            <RefreshCw
              className={cn(
                "h-4 w-4 text-neutral-400 transition-transform",
                expanded && "rotate-180"
              )}
            />
          </div>
        </div>
      </button>

      {expanded && items.length > 0 && (
        <div className="border-t divide-y divide-neutral-100">
          {items.map((item) => {
            const sc = severityClasses(item.severity);
            return (
              <div key={item.id} className="px-5 py-3 flex items-start gap-3 hover:bg-neutral-50">
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
                      <span className={cn("h-1.5 w-1.5 rounded-full", sc.dot)} />
                      {item.severity.charAt(0).toUpperCase() + item.severity.slice(1)}
                    </span>
                    {item.source === "auto" && (
                      <Badge variant="info" className="text-xs">AI</Badge>
                    )}
                  </div>
                  <p className="text-sm font-medium text-neutral-900">{item.title}</p>
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
                  {Object.entries(MITIGATION_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProjectRiskAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: detail, isLoading } = useAlleyRiskDetail(id);
  const { data: progress } = useAlleyRiskProgress(id);
  const runCheck = useRunRiskCheck();

  const risks = detail?.risk_items ?? [];

  // Group by domain
  const byDomain = DOMAIN_ORDER.reduce<Record<string, RiskItemSummary[]>>(
    (acc, domain) => {
      acc[domain] = risks.filter((r) => r.dimension === domain);
      return acc;
    },
    {}
  );

  // Any domains with risks not in DOMAIN_ORDER
  const otherDomains = [
    ...new Set(risks.map((r) => r.dimension).filter((d) => !DOMAIN_ORDER.includes(d))),
  ];

  const unaddressed = risks.filter(
    (r) =>
      r.mitigation_status === "unaddressed" || r.mitigation_status === "acknowledged"
  ).length;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner />
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
              Risk Analysis &amp; Compliance
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              Risk breakdown by domain with compliance status and mitigation tracking.
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

      {/* Summary stats */}
      {detail && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Total Risks</p>
              <p className="text-2xl font-bold text-neutral-900">{detail.total_risks}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Unaddressed</p>
              <p className="text-2xl font-bold text-red-600">{unaddressed}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Addressed</p>
              <p className="text-2xl font-bold text-green-600">{detail.addressed_risks}</p>
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

      {/* Empty state */}
      {risks.length === 0 && (
        <EmptyState
          icon={<ShieldCheck className="h-12 w-12 text-neutral-400" />}
          title="No risk data available"
          description="Run a risk check to analyse risks across regulatory, financial, technical, ESG, and market dimensions."
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

      {/* Domain breakdown */}
      {risks.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-neutral-700 uppercase tracking-wide">
            Domain Breakdown
          </h2>
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
        </div>
      )}

      {/* Compliance note */}
      {risks.length > 0 && (
        <Card className="bg-neutral-50 border-neutral-200">
          <CardContent className="p-4 flex gap-3">
            <ShieldCheck className="h-5 w-5 text-neutral-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-neutral-700">Compliance Disclaimer</p>
              <p className="text-xs text-neutral-500 mt-0.5">
                Risk items are AI-generated based on project data and should be reviewed by qualified legal and compliance professionals. This is not legal or regulatory advice.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
