"use client";

import { useState } from "react";
import {
  Loader2,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  cn,
} from "@scr/ui";
import {
  useAlleyRisks,
  useAlleyRiskDetail,
  useRiskDomains,
  useRunRiskCheck,
  useUpdateMitigation,
  severityClasses,
  riskScoreColor,
  MITIGATION_STATUS_LABELS,
  DOMAIN_LABELS,
  type ProjectRiskSummary,
} from "@/lib/alley-risk";
import { usePermission } from "@/lib/auth";

// ── Risk Arc (inline — arc length = risk level, color = severity) ────────────

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

// ── Severity dot ──────────────────────────────────────────────────────────────

function SeverityDot({ severity }: { severity: string }) {
  const c = severityClasses(severity);
  return <span className={cn("inline-block h-2 w-2 rounded-full shrink-0", c.dot)} />;
}

// ── Severity chip (4-tier) ────────────────────────────────────────────────────

function SeverityChip({ label, count, severity }: { label: string; count: number; severity: string }) {
  if (count === 0) return null;
  const c = severityClasses(severity);
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border", c.bg, c.text, c.border)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
      <span className="font-bold">{count}</span>
      <span>{label}</span>
    </span>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ pct, className }: { pct: number; className?: string }) {
  const clamped = Math.min(100, Math.max(0, pct));
  const color =
    clamped >= 75 ? "bg-green-500" : clamped >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className={cn("h-2 bg-neutral-100 rounded-full overflow-hidden", className)}>
      <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${clamped}%` }} />
    </div>
  );
}

// ── Risk Detail Panel ─────────────────────────────────────────────────────────

function RiskDetailPanel({
  projectId,
  canEdit,
}: {
  projectId: string;
  canEdit: boolean;
}) {
  const { data, isLoading } = useAlleyRiskDetail(projectId);
  const runCheck = useRunRiskCheck();
  const updateMitigation = useUpdateMitigation();
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  async function handleStatusChange(riskId: string, status: string, notes?: string) {
    setUpdatingId(riskId);
    try {
      await updateMitigation.mutateAsync({ projectId, riskId, status, notes });
    } finally {
      setUpdatingId(null);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!data?.risk_items?.length) {
    return (
      <p className="text-sm text-neutral-400 text-center py-8">
        No risk items found for this project.
      </p>
    );
  }

  return (
    <div className="space-y-2 mt-1">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-neutral-500">
          <span className="font-medium">{data.addressed_risks}</span> of{" "}
          <span className="font-medium">{data.total_risks}</span> risks addressed ·{" "}
          <span className="font-medium">{data.mitigation_progress_pct.toFixed(0)}%</span> complete
        </div>
        {canEdit && (
          <button
            onClick={() => runCheck.mutate(projectId)}
            disabled={runCheck.isPending}
            className="flex items-center gap-1.5 text-xs text-primary-600 hover:text-primary-700 font-medium disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", runCheck.isPending && "animate-spin")} />
            Run New Check
          </button>
        )}
      </div>
      <ProgressBar pct={data.mitigation_progress_pct} className="mb-4" />

      {data.risk_items.map((item) => {
        const sc = severityClasses(item.severity);
        return (
          <div
            key={item.id}
            className={cn(
              "bg-white border rounded-lg px-4 py-3 space-y-2",
              sc.border
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <SeverityDot severity={item.severity} />
                  <span className="font-medium text-sm text-neutral-800">{item.title}</span>
                  <span className={cn("text-xs font-medium px-1.5 py-0.5 rounded", sc.bg, sc.text)}>
                    {item.severity.charAt(0).toUpperCase() + item.severity.slice(1)}
                  </span>
                  <Badge variant="neutral" className="text-xs">
                    {DOMAIN_LABELS[item.dimension] ?? item.dimension}
                  </Badge>
                  {item.source === "auto" && (
                    <span className="text-xs text-neutral-400">Auto</span>
                  )}
                </div>
                <p className="text-xs text-neutral-500">{item.description}</p>
                {item.guidance && (
                  <p className="text-xs text-blue-600 mt-1 italic">{item.guidance}</p>
                )}
              </div>

              <div className="shrink-0 flex flex-col gap-1 items-end">
                <select
                  className="text-xs border border-neutral-200 rounded px-2 py-1 bg-white text-neutral-700 disabled:opacity-50"
                  value={item.mitigation_status}
                  disabled={!canEdit || updatingId === item.id}
                  onChange={(e) => handleStatusChange(item.id, e.target.value)}
                >
                  {Object.entries(MITIGATION_STATUS_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
                {updatingId === item.id && (
                  <Loader2 className="h-3 w-3 animate-spin text-neutral-400" />
                )}
              </div>
            </div>

            {item.notes && (
              <p className="text-xs text-neutral-400 border-t border-neutral-50 pt-1.5">
                Note: {item.notes}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Project Risk Row ──────────────────────────────────────────────────────────

function ProjectRiskRow({
  project,
  expanded,
  onToggle,
  canEdit,
}: {
  project: ProjectRiskSummary;
  expanded: boolean;
  onToggle: () => void;
  canEdit: boolean;
}) {
  const riskColor = riskScoreColor(project.overall_risk_score);

  return (
    <div className="border border-neutral-200 rounded-lg bg-white overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-neutral-50 transition-colors"
      >
        <div className="shrink-0 text-neutral-400">
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <span className="font-semibold text-neutral-900 truncate">
              {project.project_name}
            </span>
            <span className="text-xs text-neutral-400">{project.total_risks} risks</span>
            <span
              className="text-xs font-semibold"
              style={{ color: riskColor }}
            >
              Risk: {project.overall_risk_score.toFixed(0)}
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap mb-2">
            <SeverityChip label="Critical" count={project.critical_count} severity="critical" />
            <SeverityChip label="High" count={project.high_count} severity="high" />
            <SeverityChip label="Medium" count={project.medium_count} severity="medium" />
            <SeverityChip label="Low" count={project.low_count} severity="low" />
          </div>

          <div className="flex items-center gap-3">
            <ProgressBar pct={project.mitigation_progress_pct} className="flex-1" />
            <span className="text-xs font-medium text-neutral-600 shrink-0">
              {project.mitigation_progress_pct.toFixed(0)}% mitigated
            </span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 bg-neutral-50 border-t border-neutral-100">
          <RiskDetailPanel projectId={project.project_id} canEdit={canEdit} />
        </div>
      )}
    </div>
  );
}

// ── Domain Breakdown Tab ──────────────────────────────────────────────────────

function DomainBreakdown() {
  const { data, isLoading } = useRiskDomains();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-lg bg-neutral-100" />
        ))}
      </div>
    );
  }

  if (!data?.domains?.length) {
    return (
      <p className="text-sm text-neutral-400 text-center py-12">
        No domain data yet — generate a signal score to see risk breakdown.
      </p>
    );
  }

  const maxScore = Math.max(...data.domains.map((d) => d.risk_score), 1);

  return (
    <div className="space-y-4">
      <p className="text-xs text-neutral-500">
        Risk breakdown across 5 domains. Wider bars = higher risk. Score is severity-weighted, adjusted for mitigation.
      </p>
      {data.domains.map((domain) => {
        const pct = maxScore > 0 ? (domain.risk_score / maxScore) * 100 : 0;
        const color = riskScoreColor(domain.risk_score);
        const label = DOMAIN_LABELS[domain.domain] ?? domain.domain;
        return (
          <Card key={domain.domain}>
            <CardContent className="px-5 py-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-neutral-800">{label}</span>
                  <span className="text-xs text-neutral-400">
                    {domain.total} risk{domain.total !== 1 ? "s" : ""}
                  </span>
                </div>
                <span className="text-sm font-bold" style={{ color }}>
                  {domain.risk_score.toFixed(0)}
                </span>
              </div>

              {/* Risk bar */}
              <div className="h-3 bg-neutral-100 rounded-full overflow-hidden mb-3">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>

              {/* Severity distribution */}
              <div className="flex items-center gap-2 flex-wrap">
                {domain.critical_count > 0 && (
                  <SeverityChip label="Critical" count={domain.critical_count} severity="critical" />
                )}
                {domain.high_count > 0 && (
                  <SeverityChip label="High" count={domain.high_count} severity="high" />
                )}
                {domain.medium_count > 0 && (
                  <SeverityChip label="Medium" count={domain.medium_count} severity="medium" />
                )}
                {domain.low_count > 0 && (
                  <SeverityChip label="Low" count={domain.low_count} severity="low" />
                )}
                {domain.total === 0 && (
                  <span className="text-xs text-neutral-400 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                    No risks identified
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlleyRiskPage() {
  const { data, isLoading } = useAlleyRisks();
  const canEdit = usePermission("edit", "project");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function toggle(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  const portfolioScore = data?.portfolio_risk_score ?? 0;
  const totalAuto = data?.total_auto_identified ?? 0;
  const totalLogged = data?.total_logged ?? 0;

  const portfolioRiskLabel =
    portfolioScore >= 75
      ? "Critical"
      : portfolioScore >= 50
        ? "High"
        : portfolioScore >= 25
          ? "Medium"
          : "Low";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* ── Hero card ────────────────────────────────────────────────────── */}
      <Card className="border-primary-700 bg-primary-600">
        <CardContent className="px-8 pt-8 pb-6">
          {/* [arc left] [stats right] */}
          <div className="flex items-center gap-6">
            <RiskArc score={portfolioScore} size={120} strokeWidth={12} />
            <div>
              <p className="text-5xl font-bold tabular-nums text-white leading-none">
                {portfolioScore.toFixed(0)}
              </p>
              <p className="mt-1 text-lg font-medium text-white/80">
                Overall Risk Score
              </p>
              <p className="mt-0.5 text-sm font-medium text-white/60">
                {portfolioRiskLabel} Risk
              </p>
            </div>
            {/* Divider */}
            <div className="hidden sm:block w-px h-16 bg-white/20 mx-2" />
            {/* Stat chips */}
            <div className="hidden sm:flex flex-col gap-2">
              <div>
                <p className="text-2xl font-bold text-white tabular-nums">{totalLogged}</p>
                <p className="text-xs text-white/60">Logged Risks</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-white tabular-nums">{totalAuto}</p>
                <p className="text-xs text-white/60">Auto Identified</p>
              </div>
            </div>
          </div>
          {/* Mobile stat row */}
          <div className="sm:hidden mt-6 flex gap-6">
            <div>
              <p className="text-xl font-bold text-white tabular-nums">{totalLogged}</p>
              <p className="text-xs text-white/60">Logged</p>
            </div>
            <div>
              <p className="text-xl font-bold text-white tabular-nums">{totalAuto}</p>
              <p className="text-xs text-white/60">Auto Identified</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
      <Tabs defaultValue="projects">
        <TabsList>
          <TabsTrigger value="projects">My Projects</TabsTrigger>
          <TabsTrigger value="domains">By Domain</TabsTrigger>
        </TabsList>

        {/* ── Projects tab ─────────────────────────────────────────────── */}
        <TabsContent value="projects" className="mt-6 space-y-4">
          {isLoading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="h-7 w-7 animate-spin text-neutral-400" />
            </div>
          ) : !data?.items?.length ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-20 text-center">
                <ShieldAlert className="h-10 w-10 text-neutral-300 mb-3" />
                <h3 className="text-base font-semibold text-neutral-700 mb-1">
                  No risk assessments yet
                </h3>
                <p className="text-sm text-neutral-400 max-w-xs">
                  Risk assessments are generated automatically when signal scores are
                  calculated for your projects.
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Legend */}
              <div className="flex items-center gap-3 text-xs text-neutral-500">
                <span className="font-medium">Severity:</span>
                {(["critical", "high", "medium", "low"] as const).map((s) => {
                  const c = severityClasses(s);
                  return (
                    <span key={s} className="flex items-center gap-1">
                      <span className={cn("h-2 w-2 rounded-full", c.dot)} />
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </span>
                  );
                })}
              </div>

              <div className="space-y-3">
                {data.items.map((project) => (
                  <ProjectRiskRow
                    key={project.project_id}
                    project={project}
                    expanded={expandedId === project.project_id}
                    onToggle={() => toggle(project.project_id)}
                    canEdit={canEdit}
                  />
                ))}
              </div>
            </>
          )}
        </TabsContent>

        {/* ── Domains tab ──────────────────────────────────────────────── */}
        <TabsContent value="domains" className="mt-6">
          <DomainBreakdown />
        </TabsContent>
      </Tabs>
    </div>
  );
}
