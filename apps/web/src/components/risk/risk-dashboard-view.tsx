"use client";

import { useState, useMemo } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Clock,
  Search,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Loader2,
  Globe,
  DollarSign,
  Leaf,
  Settings,
  FileText,
  RefreshCw,
  TrendingDown,
  Lightbulb,
  Target,
  Zap,
  BarChart3,
} from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  EmptyState,
  cn,
} from "@scr/ui";
import {
  useAlleyRisks,
  useAlleyRiskDetail,
  useRiskDomains,
  useRunRiskCheck,
  useUpdateMitigation,
  useGenerateMitigation,
  useGeneratePortfolioMitigation,
  riskScoreColor,
  severityClasses,
  MITIGATION_STATUS_LABELS,
  DOMAIN_LABELS,
  type MitigationStrategy,
  type PortfolioMitigationPlan,
  type RiskItemSummary,
} from "@/lib/alley-risk";
import {
  useFinancingReadiness,
  useMilestonePlan,
  useAdvisorQuery,
} from "@/lib/alley-advisor";

// ── Local helpers ─────────────────────────────────────────────────────────

/** Signal Score color scale — high score = good (green) */
function healthColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 70) return "#3b82f6";
  if (score >= 60) return "#f59e0b";
  if (score >= 50) return "#eab308";
  return "#ef4444";
}

const DOMAIN_ICON: Record<string, React.ComponentType<{ className?: string }>> =
  {
    technical: Settings,
    financial: DollarSign,
    regulatory: FileText,
    esg: Leaf,
    market: Globe,
  };

function SectionLoader() {
  return (
    <div className="flex justify-center py-16">
      <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
    </div>
  );
}

function SelectProjectPrompt() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center text-neutral-500">
      <BarChart3 className="h-10 w-10 text-neutral-300 mb-3" />
      <p className="font-medium">Select a project above</p>
      <p className="text-sm mt-1">
        Choose a project to see detailed risk items
      </p>
    </div>
  );
}

// ── Hero Score Card — matches Signal Score design language ─────────────────

function HeroScoreCard({
  score,
  label,
}: {
  score: number;
  label?: string;
}) {
  const color = riskScoreColor(score);
  const size = 200;
  const strokeWidth = 14;
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(score, 0), 100) / 100;
  const offset = circ * (1 - pct);
  const cx = size / 2;

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-8 shadow-sm flex flex-col items-center h-full justify-center">
      <div className="relative">
        <svg
          width={size}
          height={size}
          className="rotate-[-90deg]"
        >
          <circle
            cx={cx}
            cy={cx}
            r={r}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={cx}
            cy={cx}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 800ms ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-bold tabular-nums leading-none"
            style={{ fontSize: "72px", color }}
          >
            {Math.ceil(score)}
          </span>
        </div>
      </div>
      <p className="mt-3 text-sm text-gray-500">
        {label ?? "Portfolio Risk Score"}
      </p>
      <p className="mt-1 text-xs text-neutral-400">Higher score = better risk management</p>
    </div>
  );
}

// ── Domain Bar ─────────────────────────────────────────────────────────────

function DomainBar({
  domain,
  riskScore,
  total,
}: {
  domain: string;
  riskScore: number;
  total: number;
}) {
  const color = riskScoreColor(riskScore);
  const Icon = DOMAIN_ICON[domain] ?? Globe;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-neutral-700 font-medium">
          <Icon className="h-3.5 w-3.5 text-neutral-400" />
          {DOMAIN_LABELS[domain] ?? domain}
        </span>
        <span className="text-xs font-semibold" style={{ color }}>
          {Math.ceil(riskScore)}
          <span className="text-neutral-400 font-normal"> / {total} risks</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
        <div
          className="h-2 rounded-full transition-all duration-500"
          style={{ width: `${riskScore}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ── Severity Badge ─────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const cls = severityClasses(severity);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold border",
        cls.bg,
        cls.text,
        cls.border
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", cls.dot)} />
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

// ── Risk Item Card ─────────────────────────────────────────────────────────

function RiskItemCard({
  item,
  projectId,
  onMitigationGenerate,
  generatedStrategy,
}: {
  item: RiskItemSummary;
  projectId: string;
  onMitigationGenerate: (riskId: string) => void;
  generatedStrategy?: MitigationStrategy;
}) {
  const [expanded, setExpanded] = useState(false);
  const generateMutation = useGenerateMitigation();
  const updateMutation = useUpdateMitigation();

  return (
    <div className="rounded-lg border border-neutral-200 bg-white">
      <div
        className="flex items-start gap-3 p-4 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-neutral-900 text-sm">
              {item.title}
            </span>
            <SeverityBadge severity={item.severity} />
            <span className="text-xs text-neutral-400 capitalize">
              {DOMAIN_LABELS[item.dimension] ?? item.dimension}
            </span>
          </div>
          <p className="text-xs text-neutral-500 mt-1 line-clamp-2">
            {item.description}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-neutral-400 capitalize">
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

      {expanded && (
        <div className="border-t border-neutral-100 p-4 space-y-4">
          {item.guidance && (
            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">
                Guidance
              </p>
              <p className="text-sm text-neutral-700">{item.guidance}</p>
            </div>
          )}

          <div className="flex items-center gap-2">
            <select
              className="text-xs border border-neutral-200 rounded px-2 py-1.5 bg-white"
              value={item.mitigation_status}
              onChange={(e) =>
                updateMutation.mutate({
                  projectId,
                  riskId: item.id,
                  status: e.target.value,
                })
              }
            >
              {Object.entries(MITIGATION_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <button
              onClick={(e) => {
                e.stopPropagation();
                generateMutation.mutate(
                  { projectId, riskId: item.id },
                  {
                    onSuccess: () => onMitigationGenerate(item.id),
                  }
                );
              }}
              disabled={generateMutation.isPending}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
            >
              {generateMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Sparkles className="h-3 w-3" />
              )}
              Generate Strategy
            </button>
          </div>

          {generatedStrategy && (
            <div className="rounded-lg border border-purple-100 bg-purple-50 p-3 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-700">
                <Sparkles className="h-3.5 w-3.5" />
                AI Mitigation Strategy
                <span className="ml-auto font-normal text-purple-400">
                  {new Date(generatedStrategy.generated_at).toLocaleString()}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-purple-500 font-medium">
                    Timeline
                  </p>
                  <p className="text-xs text-purple-900">
                    {generatedStrategy.overall_timeline}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-purple-500 font-medium">
                    Expected Impact
                  </p>
                  <p className="text-xs text-purple-900">
                    {generatedStrategy.expected_impact}
                  </p>
                </div>
              </div>
              {generatedStrategy.recommended_actions.length > 0 && (
                <div>
                  <p className="text-xs text-purple-500 font-medium mb-1.5">
                    Recommended Actions
                  </p>
                  <div className="space-y-1.5">
                    {generatedStrategy.recommended_actions.map((a, i) => (
                      <div
                        key={i}
                        className="rounded bg-white p-2 text-xs text-neutral-700 border border-purple-100"
                      >
                        <p className="font-medium">{a.action}</p>
                        <p className="text-neutral-400 mt-0.5">
                          {a.timeline} · {a.owner} · {a.expected_impact}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Overview Tab ───────────────────────────────────────────────────────────

const COMPACT_STATS_CLASSES = [
  { label: "Total Projects", key: "total", color: "text-blue-700", border: "border-blue-100", bg: "bg-blue-50" },
  { label: "Auto-Identified", key: "auto_identified", color: "text-amber-700", border: "border-amber-100", bg: "bg-amber-50" },
  { label: "Logged Risks", key: "logged", color: "text-purple-700", border: "border-purple-100", bg: "bg-purple-50" },
  { label: "Critical Projects", key: "critical_projects", color: "text-red-700", border: "border-red-100", bg: "bg-red-50" },
] as const;

function PortfolioOverviewTab() {
  const { data: risks, isLoading } = useAlleyRisks();
  const { data: domains } = useRiskDomains();

  if (isLoading) return <SectionLoader />;

  const portfolioScore = risks?.portfolio_risk_score ?? 0;
  const stats = {
    total: risks?.total ?? 0,
    auto_identified: risks?.total_auto_identified ?? 0,
    logged: risks?.total_logged ?? 0,
    critical_projects: risks?.items.filter((p) => p.critical_count > 0).length ?? 0,
  };

  return (
    <div className="space-y-6">
      {/* Hero 60% + Stats 40% */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-stretch">
        <div className="lg:col-span-3">
          <HeroScoreCard score={portfolioScore} label="Portfolio Risk Score" />
        </div>
        <div className="lg:col-span-2 grid grid-cols-2 gap-3">
          {COMPACT_STATS_CLASSES.map(({ label, key, color, border, bg }) => (
            <div key={key} className={cn("rounded-xl border p-4 flex flex-col justify-center", bg, border)}>
              <p className={cn("text-3xl font-bold tabular-nums", color)}>{stats[key]}</p>
              <p className="text-xs text-neutral-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Domain bars */}
      {domains && domains.domains.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Risk by Domain</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {domains.domains.map((d) => (
              <DomainBar key={d.domain} domain={d.domain} riskScore={d.risk_score} total={d.total} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Project risk table */}
      {risks && risks.items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Project Risk Summary</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-neutral-50">
                    {["Project", "Risk Score", "Critical", "High", "Medium", "Low", "Progress"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {risks.items
                    .slice()
                    .sort((a, b) => b.overall_risk_score - a.overall_risk_score)
                    .map((p) => (
                      <tr key={p.project_id} className="hover:bg-neutral-50">
                        <td className="px-4 py-3">
                          <p className="font-medium text-neutral-900 text-xs">{p.project_name}</p>
                          <p className="text-xs text-neutral-400">{p.project_id}</p>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-bold" style={{ color: riskScoreColor(p.overall_risk_score) }}>
                            {Math.ceil(p.overall_risk_score)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-red-700 font-semibold">{p.critical_count}</td>
                        <td className="px-4 py-3 text-xs text-orange-600">{p.high_count}</td>
                        <td className="px-4 py-3 text-xs text-amber-600">{p.medium_count}</td>
                        <td className="px-4 py-3 text-xs text-green-600">{p.low_count}</td>
                        <td className="px-4 py-3">
                          {(() => {
                            const pct = p.total_risks > 0
                              ? Math.round((p.mitigated_count / p.total_risks) * 100)
                              : 0;
                            return (
                              <div className="flex items-center gap-2">
                                <div className="h-1.5 w-20 rounded-full bg-neutral-100 overflow-hidden">
                                  <div className="h-1.5 rounded-full bg-green-500" style={{ width: `${pct}%` }} />
                                </div>
                                <span className="text-xs text-neutral-500">{pct}%</span>
                              </div>
                            );
                          })()}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ProjectOverviewTab({ projectId }: { projectId: string }) {
  const { data: detail, isLoading } = useAlleyRiskDetail(projectId);
  const runCheck = useRunRiskCheck();

  if (isLoading) return <SectionLoader />;

  const score = detail?.overall_risk_score ?? 0;
  const items = detail?.risk_items ?? [];
  const critical = items.filter((r) => r.severity === "critical").length;
  const high = items.filter((r) => r.severity === "high").length;
  const medium = items.filter((r) => r.severity === "medium").length;
  const low = items.filter((r) => r.severity === "low").length;

  // Domain breakdown from risk items
  const domainGroups = Object.entries(
    items.reduce<Record<string, { count: number; critical: number; high: number }>>((acc, r) => {
      const d = acc[r.dimension] ?? { count: 0, critical: 0, high: 0 };
      d.count++;
      if (r.severity === "critical") d.critical++;
      else if (r.severity === "high") d.high++;
      acc[r.dimension] = d;
      return acc;
    }, {})
  );

  const projectStats = [
    { label: "Critical", value: critical, color: "text-red-700", border: "border-red-100", bg: "bg-red-50" },
    { label: "High", value: high, color: "text-orange-700", border: "border-orange-100", bg: "bg-orange-50" },
    { label: "Medium", value: medium, color: "text-amber-700", border: "border-amber-100", bg: "bg-amber-50" },
    { label: "Low", value: low, color: "text-green-700", border: "border-green-100", bg: "bg-green-50" },
  ];

  return (
    <div className="space-y-6">
      {/* Hero 60% + Severity stats 40% */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-stretch">
        <div className="lg:col-span-3">
          <HeroScoreCard score={score} label="Project Risk Score" />
        </div>
        <div className="lg:col-span-2 grid grid-cols-2 gap-3">
          {projectStats.map(({ label, value, color, border, bg }) => (
            <div key={label} className={cn("rounded-xl border p-4 flex flex-col justify-center", bg, border)}>
              <p className={cn("text-3xl font-bold tabular-nums", color)}>{value}</p>
              <p className="text-xs text-neutral-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Domain breakdown */}
      {domainGroups.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Risk by Domain</CardTitle>
              <button
                onClick={() => runCheck.mutate(projectId)}
                disabled={runCheck.isPending}
                className="flex items-center gap-1.5 text-xs px-2 py-1 border border-neutral-200 rounded hover:bg-neutral-50 disabled:opacity-50"
              >
                {runCheck.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                Run Risk Check
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {domainGroups.map(([domain, { count, critical: c, high: h }]) => {
              const Icon = DOMAIN_ICON[domain] ?? Globe;
              return (
                <div key={domain} className="flex items-center gap-3">
                  <Icon className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                  <span className="text-sm font-medium text-neutral-700 w-24 flex-shrink-0">
                    {DOMAIN_LABELS[domain] ?? domain}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                    <div
                      className="h-2 rounded-full bg-primary-500"
                      style={{ width: `${Math.min((count / items.length) * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-neutral-500 w-16 text-right flex-shrink-0">
                    {count} risk{count !== 1 ? "s" : ""}
                    {c > 0 && <span className="text-red-600 font-semibold ml-1">·{c}C</span>}
                    {h > 0 && <span className="text-orange-500 ml-1">·{h}H</span>}
                  </span>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* Mitigation progress */}
      {detail && (
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="flex-1">
              <div className="flex justify-between text-xs text-neutral-500 mb-1">
                <span>Mitigation Progress</span>
                <span className="font-semibold text-neutral-700">{Math.round(detail.mitigation_progress_pct)}%</span>
              </div>
              <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
                <div className="h-2 rounded-full bg-green-500 transition-all" style={{ width: `${detail.mitigation_progress_pct}%` }} />
              </div>
            </div>
            <div className="text-xs text-neutral-400">{detail.addressed_risks}/{detail.total_risks} addressed</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function OverviewTab({ projectId, isProjectView }: { projectId: string | undefined; isProjectView: boolean }) {
  if (isProjectView && projectId) {
    return <ProjectOverviewTab projectId={projectId} />;
  }
  return <PortfolioOverviewTab />;
}

// ── Alerts Tab ─────────────────────────────────────────────────────────────

function AlertsTab({ projectId }: { projectId: string | undefined }) {
  const [filter, setFilter] = useState<string>("all");
  const { data: risks } = useAlleyRisks();
  const { data: detail } = useAlleyRiskDetail(projectId);

  const SEVERITIES = ["all", "critical", "high", "medium", "low"];

  const alerts = useMemo(() => {
    if (detail) {
      const items = detail.risk_items.filter(
        (r) =>
          filter === "all" || r.severity.toLowerCase() === filter
      );
      return items;
    }
    // Portfolio: derive alerts from project summaries
    return [];
  }, [detail, filter]);

  return (
    <div className="space-y-4">
      {/* Filter pills */}
      <div className="flex gap-2">
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={cn(
              "px-3 py-1 rounded-full text-sm font-medium capitalize transition-colors",
              filter === s
                ? "bg-primary-600 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            )}
          >
            {s}
          </button>
        ))}
      </div>

      {!projectId ? (
        /* Portfolio alert summary */
        <div className="space-y-3">
          {risks?.items
            .filter(
              (p) =>
                filter === "all" ||
                (filter === "critical" && p.critical_count > 0) ||
                (filter === "high" && p.high_count > 0) ||
                (filter === "medium" && p.medium_count > 0) ||
                (filter === "low" && p.low_count > 0)
            )
            .sort(
              (a, b) =>
                b.critical_count * 1000 +
                b.high_count * 100 -
                (a.critical_count * 1000 + a.high_count * 100)
            )
            .map((p) => (
              <Card key={p.project_id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-sm text-neutral-900">
                        {p.project_name}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        {p.critical_count > 0 && (
                          <SeverityBadge severity="critical" />
                        )}
                        {p.high_count > 0 && (
                          <SeverityBadge severity="high" />
                        )}
                        {p.medium_count > 0 && (
                          <SeverityBadge severity="medium" />
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-neutral-400">Risk Score</p>
                      <p
                        className="text-lg font-bold"
                        style={{
                          color: riskScoreColor(p.overall_risk_score),
                        }}
                      >
                        {Math.ceil(p.overall_risk_score)}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 mt-3 text-center">
                    {[
                      {
                        label: "Critical",
                        count: p.critical_count,
                        color: "text-red-700",
                      },
                      {
                        label: "High",
                        count: p.high_count,
                        color: "text-orange-600",
                      },
                      {
                        label: "Medium",
                        count: p.medium_count,
                        color: "text-amber-600",
                      },
                      {
                        label: "Low",
                        count: p.low_count,
                        color: "text-green-600",
                      },
                    ].map(({ label, count, color }) => (
                      <div key={label} className="rounded bg-neutral-50 p-2">
                        <p className={cn("text-lg font-bold", color)}>
                          {count}
                        </p>
                        <p className="text-xs text-neutral-400">{label}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
        </div>
      ) : alerts.length > 0 ? (
        <div className="space-y-3">
          {alerts.map((item) => {
            const cls = severityClasses(item.severity);
            return (
              <div
                key={item.id}
                className={cn(
                  "rounded-lg border p-4 space-y-2",
                  cls.bg,
                  cls.border
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={cn("h-4 w-4", cls.text)} />
                    <span className={cn("text-sm font-semibold", cls.text)}>
                      {item.title}
                    </span>
                    <SeverityBadge severity={item.severity} />
                  </div>
                  <span className="text-xs text-neutral-400 capitalize">
                    {DOMAIN_LABELS[item.dimension] ?? item.dimension}
                  </span>
                </div>
                <p className="text-sm text-neutral-700">{item.description}</p>
                {item.guidance && (
                  <p className="text-xs text-neutral-500 italic">
                    {item.guidance}
                  </p>
                )}
              </div>
            );
          })}

          {/* AI Analysis summary bar */}
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-blue-500 flex-shrink-0" />
            <p className="text-xs text-blue-700">
              <strong>AI Analysis:</strong>{" "}
              {alerts.filter((a) => a.severity === "critical").length > 0
                ? `${alerts.filter((a) => a.severity === "critical").length} critical risk(s) require immediate attention. `
                : ""}
              {alerts.filter((a) => a.severity === "high").length > 0
                ? `${alerts.filter((a) => a.severity === "high").length} high severity item(s) should be addressed within 30 days. `
                : ""}
              {alerts.filter((a) => a.mitigation_status === "unaddressed").length > 0
                ? `${alerts.filter((a) => a.mitigation_status === "unaddressed").length} risks remain unaddressed.`
                : "All identified risks have been acknowledged."}
            </p>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={<CheckCircle className="h-10 w-10 text-green-400" />}
          title="No alerts"
          description={
            projectId ? "No risks match the selected filter." : "Select a project to view detailed alerts."
          }
        />
      )}
    </div>
  );
}

// ── Severity Tab ───────────────────────────────────────────────────────────

function SeverityTab({ projectId }: { projectId: string | undefined }) {
  const { data: risks } = useAlleyRisks();
  const { data: detail } = useAlleyRiskDetail(projectId);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["critical", "high"])
  );
  const generateMitigation = useGenerateMitigation();
  const [strategies, setStrategies] = useState<
    Map<string, MitigationStrategy>
  >(new Map());

  const SEVERITY_GROUPS = [
    {
      key: "critical",
      label: "Critical",
      color: "text-black",
      bg: "bg-black/5 border-black/10",
    },
    {
      key: "high",
      label: "High",
      color: "text-red-700",
      bg: "bg-red-50 border-red-200",
    },
    {
      key: "medium",
      label: "Medium",
      color: "text-amber-700",
      bg: "bg-amber-50 border-amber-200",
    },
    {
      key: "low",
      label: "Low",
      color: "text-green-700",
      bg: "bg-green-50 border-green-200",
    },
  ];

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (!projectId) {
    // Portfolio: aggregate counts
    const totals = risks?.items.reduce(
      (acc, p) => ({
        critical: acc.critical + p.critical_count,
        high: acc.high + p.high_count,
        medium: acc.medium + p.medium_count,
        low: acc.low + p.low_count,
      }),
      { critical: 0, high: 0, medium: 0, low: 0 }
    );

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {SEVERITY_GROUPS.map(({ key, label, color, bg }) => (
            <div key={key} className={cn("rounded-xl border p-4", bg)}>
              <p className={cn("text-3xl font-bold", color)}>
                {totals?.[key as keyof typeof totals] ?? 0}
              </p>
              <p className="text-sm text-neutral-600 mt-1">{label}</p>
            </div>
          ))}
        </div>
        <SelectProjectPrompt />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {SEVERITY_GROUPS.map(({ key, label, color }) => {
        const items =
          detail?.risk_items.filter(
            (r) => r.severity.toLowerCase() === key
          ) ?? [];
        const isOpen = expandedSections.has(key);

        return (
          <div key={key} className="rounded-lg border border-neutral-200">
            <button
              className="w-full flex items-center justify-between p-4 hover:bg-neutral-50"
              onClick={() => toggleSection(key)}
            >
              <div className="flex items-center gap-3">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 text-neutral-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-neutral-400" />
                )}
                <span className={cn("font-semibold capitalize", color)}>
                  {label}
                </span>
                <span className="text-xs text-neutral-400 bg-neutral-100 px-2 py-0.5 rounded-full">
                  {items.length}
                </span>
              </div>
            </button>
            {isOpen && items.length > 0 && (
              <div className="border-t border-neutral-100 p-3 space-y-2">
                {items.map((item) => (
                  <RiskItemCard
                    key={item.id}
                    item={item}
                    projectId={projectId}
                    generatedStrategy={strategies.get(item.id)}
                    onMitigationGenerate={(riskId) => {
                      generateMitigation.mutate(
                        { projectId, riskId },
                        {
                          onSuccess: (data) => {
                            setStrategies((prev) =>
                              new Map(prev).set(riskId, data)
                            );
                          },
                        }
                      );
                    }}
                  />
                ))}
              </div>
            )}
            {isOpen && items.length === 0 && (
              <div className="border-t border-neutral-100 px-4 py-3 text-xs text-neutral-400">
                No {label.toLowerCase()} severity risks.
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Domain Tab ─────────────────────────────────────────────────────────────

function DomainTab({ projectId }: { projectId: string | undefined }) {
  const { data: domains } = useRiskDomains();
  const { data: detail } = useAlleyRiskDetail(projectId);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const generateMitigation = useGenerateMitigation();
  const [strategies, setStrategies] = useState<
    Map<string, MitigationStrategy>
  >(new Map());

  const domainItems = useMemo(() => {
    if (!detail || !selectedDomain) return [];
    return detail.risk_items.filter(
      (r) => r.dimension.toLowerCase() === selectedDomain.toLowerCase()
    );
  }, [detail, selectedDomain]);

  return (
    <div className="space-y-4">
      {/* Domain cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {domains?.domains.map((d) => {
          const Icon = DOMAIN_ICON[d.domain] ?? Globe;
          const color = riskScoreColor(d.risk_score);
          const isSelected = selectedDomain === d.domain;
          return (
            <button
              key={d.domain}
              onClick={() =>
                setSelectedDomain(isSelected ? null : d.domain)
              }
              className={cn(
                "rounded-lg border p-3 text-left transition-all",
                isSelected
                  ? "border-primary-500 ring-1 ring-primary-500 bg-primary-50"
                  : "border-neutral-200 bg-white hover:border-neutral-300"
              )}
            >
              <div className="flex items-center gap-1.5 mb-2">
                <Icon className="h-4 w-4 text-neutral-400" />
                <span className="text-xs font-semibold text-neutral-700">
                  {DOMAIN_LABELS[d.domain] ?? d.domain}
                </span>
              </div>
              <p className="text-2xl font-bold" style={{ color }}>
                {Math.ceil(d.risk_score)}
              </p>
              <p className="text-xs text-neutral-400 mt-0.5">
                {d.total} risks
              </p>
              <div className="flex gap-1 mt-2">
                {d.critical_count > 0 && (
                  <span className="text-[10px] font-bold text-red-700 bg-red-50 px-1 py-0.5 rounded">
                    {d.critical_count}C
                  </span>
                )}
                {d.high_count > 0 && (
                  <span className="text-[10px] font-bold text-orange-600 bg-orange-50 px-1 py-0.5 rounded">
                    {d.high_count}H
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Domain detail */}
      {selectedDomain && projectId ? (
        domainItems.length > 0 ? (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-neutral-700">
              {DOMAIN_LABELS[selectedDomain] ?? selectedDomain} Risks
            </p>
            {domainItems.map((item) => (
              <RiskItemCard
                key={item.id}
                item={item}
                projectId={projectId}
                generatedStrategy={strategies.get(item.id)}
                onMitigationGenerate={(riskId) => {
                  generateMitigation.mutate(
                    { projectId, riskId },
                    {
                      onSuccess: (data) =>
                        setStrategies((prev) =>
                          new Map(prev).set(riskId, data)
                        ),
                    }
                  );
                }}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-neutral-400 text-center py-8">
            No risks recorded for this domain.
          </p>
        )
      ) : selectedDomain && !projectId ? (
        <SelectProjectPrompt />
      ) : null}
    </div>
  );
}

// ── All Risks Tab ──────────────────────────────────────────────────────────

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function AllRisksTab({ projectId }: { projectId: string | undefined }) {
  const { data: risks } = useAlleyRisks();
  const { data: detail } = useAlleyRiskDetail(projectId);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [domainFilter, setDomainFilter] = useState("all");
  const [sortField, setSortField] = useState<"severity" | "domain" | "status">(
    "severity"
  );

  const filteredItems = useMemo(() => {
    if (!detail) return [];
    return detail.risk_items
      .filter((r) => {
        const matchSearch =
          !search ||
          r.title.toLowerCase().includes(search.toLowerCase()) ||
          r.description.toLowerCase().includes(search.toLowerCase());
        const matchSeverity =
          severityFilter === "all" ||
          r.severity.toLowerCase() === severityFilter;
        const matchDomain =
          domainFilter === "all" ||
          r.dimension.toLowerCase() === domainFilter;
        return matchSearch && matchSeverity && matchDomain;
      })
      .sort((a, b) => {
        if (sortField === "severity") {
          return (
            (SEVERITY_ORDER[a.severity.toLowerCase()] ?? 99) -
            (SEVERITY_ORDER[b.severity.toLowerCase()] ?? 99)
          );
        }
        if (sortField === "domain") return a.dimension.localeCompare(b.dimension);
        return a.mitigation_status.localeCompare(b.mitigation_status);
      });
  }, [detail, search, severityFilter, domainFilter, sortField]);

  if (!projectId) {
    // Portfolio: project summaries table
    return (
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white"
          />
        </div>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-neutral-50">
                    {["Project", "Risk Score", "C", "H", "M", "L", "Mitigation Progress"].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide"
                        >
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(risks?.items ?? [])
                    .filter(
                      (p) =>
                        !search ||
                        p.project_name
                          .toLowerCase()
                          .includes(search.toLowerCase())
                    )
                    .map((p) => (
                      <tr key={p.project_id} className="hover:bg-neutral-50">
                        <td className="px-4 py-3 font-medium text-xs text-neutral-900">
                          {p.project_name}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className="font-bold text-sm"
                            style={{
                              color: riskScoreColor(p.overall_risk_score),
                            }}
                          >
                            {Math.ceil(p.overall_risk_score)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-red-700 font-semibold">
                          {p.critical_count}
                        </td>
                        <td className="px-4 py-3 text-xs text-orange-600">
                          {p.high_count}
                        </td>
                        <td className="px-4 py-3 text-xs text-amber-600">
                          {p.medium_count}
                        </td>
                        <td className="px-4 py-3 text-xs text-green-600">
                          {p.low_count}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-neutral-500">
                            {p.total_risks > 0 ? Math.round((p.mitigated_count / p.total_risks) * 100) : 0}%
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search risks..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white"
          />
        </div>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white"
        >
          <option value="all">All Severities</option>
          {["critical", "high", "medium", "low"].map((s) => (
            <option key={s} value={s} className="capitalize">
              {s}
            </option>
          ))}
        </select>
        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white"
        >
          <option value="all">All Domains</option>
          {Object.entries(DOMAIN_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          value={sortField}
          onChange={(e) =>
            setSortField(e.target.value as "severity" | "domain" | "status")
          }
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white"
        >
          <option value="severity">Sort: Severity</option>
          <option value="domain">Sort: Domain</option>
          <option value="status">Sort: Status</option>
        </select>
      </div>

      <p className="text-xs text-neutral-400">
        {filteredItems.length} of {detail?.risk_items.length ?? 0} risks
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-neutral-50">
                  {["Risk", "Domain", "Severity", "Status"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredItems.map((item) => (
                  <tr key={item.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-neutral-900 text-xs">
                        {item.title}
                      </p>
                      <p className="text-xs text-neutral-400 mt-0.5 line-clamp-1">
                        {item.description}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-600 capitalize">
                      {DOMAIN_LABELS[item.dimension] ?? item.dimension}
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={item.severity} />
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-600 capitalize">
                      {MITIGATION_STATUS_LABELS[item.mitigation_status] ??
                        item.mitigation_status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Mitigation Tab ─────────────────────────────────────────────────────────

function MitigationTab({ projectId }: { projectId: string | undefined }) {
  const { data: detail } = useAlleyRiskDetail(projectId);
  const [strategies, setStrategies] = useState<
    Map<string, MitigationStrategy>
  >(new Map());
  const [portfolioPlan, setPortfolioPlan] =
    useState<PortfolioMitigationPlan | null>(null);
  const generateMitigation = useGenerateMitigation();
  const generatePortfolio = useGeneratePortfolioMitigation();
  const [severityFilter, setSeverityFilter] = useState("all");

  const filteredItems = useMemo(() => {
    if (!detail) return [];
    return detail.risk_items.filter(
      (r) =>
        severityFilter === "all" ||
        r.severity.toLowerCase() === severityFilter
    );
  }, [detail, severityFilter]);

  return (
    <div className="space-y-6">
      {/* Portfolio mitigation plan */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Portfolio Mitigation Plan</CardTitle>
            <button
              onClick={() =>
                generatePortfolio.mutate(projectId, {
                  onSuccess: setPortfolioPlan,
                })
              }
              disabled={generatePortfolio.isPending}
              className="flex items-center gap-1.5 text-sm px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {generatePortfolio.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Generate Portfolio Plan
            </button>
          </div>
        </CardHeader>
        <CardContent>
          {portfolioPlan ? (
            <div className="space-y-4">
              <p className="text-sm text-neutral-700">
                {portfolioPlan.portfolio_summary}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">
                    Top Priorities
                  </p>
                  <ul className="space-y-1">
                    {portfolioPlan.top_priorities.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="flex-shrink-0 h-5 w-5 rounded-full bg-red-100 text-red-700 text-xs flex items-center justify-center font-bold">
                          {i + 1}
                        </span>
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">
                    Cross-Project Recommendations
                  </p>
                  <ul className="space-y-1">
                    {portfolioPlan.cross_project_recommendations.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-400">
                <Clock className="h-3.5 w-3.5" />
                Timeline: {portfolioPlan.risk_reduction_timeline}
              </div>
            </div>
          ) : (
            <p className="text-sm text-neutral-400">
              Generate an AI-powered mitigation plan for your entire portfolio or
              selected project.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Per-risk strategies */}
      {projectId ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-neutral-700">
              Individual Risk Strategies
            </p>
            <div className="flex gap-2">
              {["all", "critical", "high", "medium", "low"].map((s) => (
                <button
                  key={s}
                  onClick={() => setSeverityFilter(s)}
                  className={cn(
                    "px-2 py-1 rounded text-xs font-medium capitalize",
                    severityFilter === s
                      ? "bg-primary-600 text-white"
                      : "bg-neutral-100 text-neutral-600"
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          {filteredItems.map((item) => (
            <RiskItemCard
              key={item.id}
              item={item}
              projectId={projectId}
              generatedStrategy={strategies.get(item.id)}
              onMitigationGenerate={(riskId) => {
                generateMitigation.mutate(
                  { projectId, riskId },
                  {
                    onSuccess: (data) =>
                      setStrategies((prev) => new Map(prev).set(riskId, data)),
                  }
                );
              }}
            />
          ))}
        </div>
      ) : (
        <SelectProjectPrompt />
      )}
    </div>
  );
}

// ── Advisor Tab ────────────────────────────────────────────────────────────

function AdvisorTab({ projectId }: { projectId: string | undefined }) {
  const { data: financing } = useFinancingReadiness(projectId);
  const { data: milestones } = useMilestonePlan(projectId);
  const advisorQuery = useAdvisorQuery();
  const [generatedPlan, setGeneratedPlan] = useState<string | null>(null);

  if (!projectId) return <SelectProjectPrompt />;

  const HORIZON_GROUPS = [
    {
      label: "Immediate",
      subtitle: "Next 7 days",
      icon: Zap,
      color: "text-red-600",
      bg: "bg-red-50 border-red-100",
      maxMonths: 0.25,
    },
    {
      label: "Short-term",
      subtitle: "Next 30 days",
      icon: Target,
      color: "text-amber-600",
      bg: "bg-amber-50 border-amber-100",
      maxMonths: 1,
    },
    {
      label: "Strategic",
      subtitle: "Next 90 days",
      icon: TrendingDown,
      color: "text-blue-600",
      bg: "bg-blue-50 border-blue-100",
      maxMonths: Infinity,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Financing Readiness */}
      {financing && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Financing Readiness</CardTitle>
              <Badge
                variant={
                  financing.readiness_score >= 70
                    ? "success"
                    : financing.readiness_score >= 50
                      ? "warning"
                      : "error"
                }
              >
                {financing.readiness_label}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-2 flex-1 rounded-full bg-neutral-100 overflow-hidden">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${financing.readiness_score}%`,
                    backgroundColor: healthColor(financing.readiness_score),
                  }}
                />
              </div>
              <span
                className="text-sm font-bold"
                style={{ color: healthColor(financing.readiness_score) }}
              >
                {financing.readiness_score}/100
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold text-green-600 uppercase mb-1.5">
                  Strengths
                </p>
                <ul className="space-y-1">
                  {financing.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-neutral-700">
                      <CheckCircle className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold text-red-500 uppercase mb-1.5">
                  Gaps
                </p>
                <ul className="space-y-1">
                  {financing.gaps.map((g, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-neutral-700">
                      <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Milestone plan by horizon */}
      {milestones && milestones.milestones.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-neutral-700">
              Development Roadmap
            </p>
            <button
              onClick={() =>
                advisorQuery.mutate(
                  {
                    id: projectId,
                    query:
                      "Generate a comprehensive development plan covering all key milestones, risks, financing steps, and strategic recommendations for the next 90 days.",
                  },
                  { onSuccess: (data) => setGeneratedPlan(data.response) }
                )
              }
              disabled={advisorQuery.isPending}
              className="flex items-center gap-1.5 text-sm px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {advisorQuery.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Generate Development Plan
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {HORIZON_GROUPS.map(
              ({ label, subtitle, icon: Icon, color, bg }) => {
                const items = milestones.milestones.filter(
                  (m) =>
                    label === "Immediate"
                      ? m.target_months <= 0.25
                      : label === "Short-term"
                        ? m.target_months > 0.25 && m.target_months <= 1
                        : m.target_months > 1
                );
                return (
                  <div key={label} className={cn("rounded-lg border p-4", bg)}>
                    <div className="flex items-center gap-2 mb-3">
                      <Icon className={cn("h-4 w-4", color)} />
                      <div>
                        <p className={cn("text-sm font-semibold", color)}>
                          {label}
                        </p>
                        <p className="text-xs text-neutral-400">{subtitle}</p>
                      </div>
                    </div>
                    {items.length > 0 ? (
                      <div className="space-y-2">
                        {items.map((m, i) => (
                          <div
                            key={i}
                            className="rounded bg-white p-2.5 border border-white/60"
                          >
                            <p className="text-xs font-semibold text-neutral-900">
                              {m.title}
                            </p>
                            <p className="text-xs text-neutral-500 mt-0.5 line-clamp-2">
                              {m.description}
                            </p>
                            {m.dependencies.length > 0 && (
                              <p className="text-[10px] text-neutral-400 mt-1">
                                Depends on: {m.dependencies.join(", ")}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-neutral-400">
                        No milestones in this window.
                      </p>
                    )}
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}

      {/* Generated Development Plan */}
      {generatedPlan && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-500" />
              <CardTitle className="text-sm">AI Development Plan</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none text-neutral-700 whitespace-pre-wrap text-sm leading-relaxed">
              {generatedPlan}
            </div>
          </CardContent>
        </Card>
      )}

      {!financing && !milestones && (
        <EmptyState
          icon={<Lightbulb className="h-10 w-10 text-neutral-300" />}
          title="No advisor data"
          description="Run the advisor analysis for this project to see recommendations."
        />
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

interface RiskDashboardViewProps {
  /** Pre-filter to a specific project. If omitted, shows portfolio selector. */
  projectId?: string;
}

export function RiskDashboardView({ projectId: fixedProjectId }: RiskDashboardViewProps) {
  const { data: risks } = useAlleyRisks();
  // selectedProjectId is only used in portfolio/main-nav mode (no fixedProjectId)
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  // If fixedProjectId is set we're entered from project nav — always in project view
  const isProjectNavMode = !!fixedProjectId;
  const activeProjectId = fixedProjectId ?? (selectedProjectId || undefined);
  // isProjectView = came from project nav OR user selected a project from the dropdown
  const isProjectView = isProjectNavMode || !!selectedProjectId;

  return (
    <div className="space-y-6">
      {/* Controls bar — only shown in main-nav (portfolio) mode */}
      {!isProjectNavMode && (
        <div className="flex items-center gap-3">
          {isProjectView ? (
            // "Back to Portfolio" when a project was selected from the dropdown
            <button
              onClick={() => setSelectedProjectId("")}
              className="flex items-center gap-1.5 text-sm font-medium text-neutral-500 hover:text-neutral-800 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Portfolio View
            </button>
          ) : (
            // Project selector shown in portfolio view
            <>
              <label className="text-sm font-medium text-neutral-600">Project:</label>
              <select
                className="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 bg-white"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
              >
                <option value="">All projects (portfolio view)</option>
                {risks?.items.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.project_name}
                  </option>
                ))}
              </select>
            </>
          )}
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList className="mb-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="severity">Severity</TabsTrigger>
          <TabsTrigger value="domain">Domain</TabsTrigger>
          <TabsTrigger value="all-risks">All Risks</TabsTrigger>
          <TabsTrigger value="mitigation">Mitigation</TabsTrigger>
          <TabsTrigger value="advisor">Advisor</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab projectId={activeProjectId} isProjectView={isProjectView} />
        </TabsContent>
        <TabsContent value="alerts">
          <AlertsTab projectId={activeProjectId} />
        </TabsContent>
        <TabsContent value="severity">
          <SeverityTab projectId={activeProjectId} />
        </TabsContent>
        <TabsContent value="domain">
          <DomainTab projectId={activeProjectId} />
        </TabsContent>
        <TabsContent value="all-risks">
          <AllRisksTab projectId={activeProjectId} />
        </TabsContent>
        <TabsContent value="mitigation">
          <MitigationTab projectId={activeProjectId} />
        </TabsContent>
        <TabsContent value="advisor">
          <AdvisorTab projectId={activeProjectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
