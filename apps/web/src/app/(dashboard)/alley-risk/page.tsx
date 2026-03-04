"use client";

import { useState } from "react";
import { Loader2, ShieldAlert, ChevronDown, ChevronRight } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  cn,
} from "@scr/ui";
import {
  useAlleyRisks,
  useAlleyRiskDetail,
  useUpdateMitigation,
  severityVariant,
  MITIGATION_STATUS_LABELS,
  type ProjectRiskSummary,
} from "@/lib/alley-risk";

// ── Helpers ──────────────────────────────────────────────────────────────────

function ProgressBar({ pct, className }: { pct: number; className?: string }) {
  const clamped = Math.min(100, Math.max(0, pct));
  const color =
    clamped >= 75
      ? "bg-green-500"
      : clamped >= 40
      ? "bg-amber-500"
      : "bg-red-500";
  return (
    <div
      className={cn(
        "h-2 bg-neutral-100 rounded-full overflow-hidden",
        className
      )}
    >
      <div
        className={cn("h-full rounded-full transition-all", color)}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

function RiskCountChip({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full",
        color
      )}
    >
      <span className="font-bold">{count}</span>
      <span>{label}</span>
    </span>
  );
}

// ── Risk Detail Panel ─────────────────────────────────────────────────────────

function RiskDetailPanel({ projectId }: { projectId: string }) {
  const { data, isLoading } = useAlleyRiskDetail(projectId);
  const updateMitigation = useUpdateMitigation();
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  async function handleStatusChange(
    riskId: string,
    status: string,
    notes?: string
  ) {
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
      <div className="flex items-center justify-between text-xs text-neutral-500 mb-2">
        <span>
          {data.addressed_risks} of {data.total_risks} risks addressed
        </span>
        <span className="font-medium">
          {data.mitigation_progress_pct.toFixed(0)}% complete
        </span>
      </div>
      <ProgressBar pct={data.mitigation_progress_pct} className="mb-4" />

      {data.risk_items.map((item) => (
        <div
          key={item.id}
          className="bg-white border border-neutral-100 rounded-lg px-4 py-3 space-y-2"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="font-medium text-sm text-neutral-800">
                  {item.title}
                </span>
                <Badge variant={severityVariant(item.severity)}>
                  {item.severity}
                </Badge>
                <Badge variant="neutral" className="text-xs">
                  {item.dimension}
                </Badge>
              </div>
              <p className="text-xs text-neutral-500">{item.description}</p>
              {item.guidance && (
                <p className="text-xs text-blue-600 mt-1 italic">
                  {item.guidance}
                </p>
              )}
            </div>

            <div className="shrink-0 flex flex-col gap-1 items-end">
              <select
                className="text-xs border border-neutral-200 rounded px-2 py-1 bg-white text-neutral-700 disabled:opacity-50"
                value={item.mitigation_status}
                disabled={updatingId === item.id}
                onChange={(e) => handleStatusChange(item.id, e.target.value)}
              >
                {Object.entries(MITIGATION_STATUS_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
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
      ))}
    </div>
  );
}

// ── Project Risk Row ─────────────────────────────────────────────────────────

function ProjectRiskRow({
  project,
  expanded,
  onToggle,
}: {
  project: ProjectRiskSummary;
  expanded: boolean;
  onToggle: () => void;
}) {
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
            <span className="text-xs text-neutral-400">
              {project.total_risks} risks
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap mb-2">
            {project.critical_count > 0 && (
              <RiskCountChip
                label="Critical"
                count={project.critical_count}
                color="bg-red-100 text-red-700"
              />
            )}
            {project.high_count > 0 && (
              <RiskCountChip
                label="High"
                count={project.high_count}
                color="bg-orange-100 text-orange-700"
              />
            )}
            {project.medium_count > 0 && (
              <RiskCountChip
                label="Medium"
                count={project.medium_count}
                color="bg-amber-100 text-amber-700"
              />
            )}
            {project.low_count > 0 && (
              <RiskCountChip
                label="Low"
                count={project.low_count}
                color="bg-neutral-100 text-neutral-600"
              />
            )}
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
          <RiskDetailPanel projectId={project.project_id} />
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AlleyRiskPage() {
  const { data, isLoading } = useAlleyRisks();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function toggle(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  // Overall portfolio progress
  const overallProgress =
    data?.items && data.items.length > 0
      ? data.items.reduce((s, p) => s + p.mitigation_progress_pct, 0) /
        data.items.length
      : 0;

  const totalCritical = data?.items?.reduce((s, p) => s + p.critical_count, 0) ?? 0;
  const totalHigh = data?.items?.reduce((s, p) => s + p.high_count, 0) ?? 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ShieldAlert className="h-6 w-6 text-orange-500" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">My Risk Profile</h1>
          <p className="text-sm text-neutral-500">
            Identify and track risk mitigation across your projects
          </p>
        </div>
      </div>

      {/* Portfolio summary */}
      {data && data.total > 0 && (
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-neutral-700">
                Portfolio Mitigation Progress
              </span>
              <span className="text-sm font-bold text-neutral-800">
                {overallProgress.toFixed(0)}%
              </span>
            </div>
            <ProgressBar pct={overallProgress} />
            <div className="flex items-center gap-4 mt-3 text-xs text-neutral-500">
              <span>
                <strong>{data.total}</strong> projects
              </span>
              {totalCritical > 0 && (
                <span className="text-red-600 font-medium">
                  {totalCritical} critical risks
                </span>
              )}
              {totalHigh > 0 && (
                <span className="text-orange-600 font-medium">
                  {totalHigh} high risks
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Content */}
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
        <div className="space-y-3">
          {data.items.map((project) => (
            <ProjectRiskRow
              key={project.project_id}
              project={project}
              expanded={expandedId === project.project_id}
              onToggle={() => toggle(project.project_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
