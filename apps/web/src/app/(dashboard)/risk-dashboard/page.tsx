"use client";

import { useState } from "react";
import {
  Loader2,
  ShieldAlert,
  Lightbulb,
  BarChart2,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  Zap,
  DollarSign,
  Target,
  FileText,
  Send,
} from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  LineChart,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  cn,
} from "@scr/ui";
import {
  useAlleyRisks,
  useAlleyRiskDetail,
  useRiskDomains,
  useRunRiskCheck,
  useUpdateMitigation,
  riskScoreColor,
  MITIGATION_STATUS_LABELS,
  DOMAIN_LABELS,
} from "@/lib/alley-risk";
import {
  useAdvisorQuery,
  useFinancingReadiness,
  useMarketPositioning,
  useMilestonePlan,
  useRegulatoryGuidance,
  milestoneStatusVariant,
} from "@/lib/alley-advisor";
import { useAlleyScores } from "@/lib/alley-score";
import {
  useAlleyOverview,
  useStageDistribution,
  useScoreDistribution,
  useRiskHeatmap,
  useDocumentCompleteness,
  riskCellBg,
  formatCurrency,
} from "@/lib/alley-analytics";
import {
  useScorePerformanceList,
  useScoreJourney,
  useScoreInsights,
  trendVariant,
  trendIcon,
  impactColor,
} from "@/lib/score-journey";
import { InfoBanner } from "@/components/info-banner";

// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────────────────────

function SectionLoader() {
  return (
    <div className="flex justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 1 — Overview
// ─────────────────────────────────────────────────────────────────────────────

function RiskArc({ score }: { score: number }) {
  const radius = 54;
  const circ = 2 * Math.PI * radius;
  const clamp = Math.min(100, Math.max(0, score));
  const dashOffset = circ * (1 - clamp / 100);
  const color =
    clamp >= 80 ? "#22c55e" : clamp >= 60 ? "#f59e0b" : clamp >= 40 ? "#f97316" : "#ef4444";

  return (
    <svg width="130" height="130" viewBox="0 0 130 130">
      <circle cx="65" cy="65" r={radius} fill="none" stroke="#ffffff20" strokeWidth="10" />
      <circle
        cx="65"
        cy="65"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeDasharray={circ}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        transform="rotate(-90 65 65)"
      />
      <text x="65" y="62" textAnchor="middle" fill="white" fontSize="28" fontWeight="700">
        {clamp}
      </text>
      <text x="65" y="78" textAnchor="middle" fill="#ffffff99" fontSize="11">
        / 100
      </text>
    </svg>
  );
}

function OverviewTab() {
  const { data: risks, isLoading } = useAlleyRisks();
  const { data: domainsData, isLoading: loadingDomains } = useRiskDomains();
  const domains = domainsData?.domains;

  const portfolioScore = risks?.portfolio_risk_score ?? 0;
  const logged = risks?.total_logged ?? 0;
  const auto = risks?.total_auto_identified ?? 0;
  const high = risks?.items?.reduce((sum, p) => sum + p.critical_count + p.high_count, 0) ?? 0;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="rounded-2xl bg-[#1B2A4A] p-6 flex flex-col sm:flex-row items-center gap-6">
        {isLoading ? (
          <Loader2 className="h-8 w-8 animate-spin text-white/60" />
        ) : (
          <RiskArc score={portfolioScore} />
        )}
        <div className="flex-1 text-white space-y-3">
          <div>
            <p className="text-sm text-white/60 uppercase tracking-wide">Portfolio Risk Score</p>
            <p className="text-lg font-semibold">
              {portfolioScore >= 80
                ? "Low Risk"
                : portfolioScore >= 60
                ? "Moderate Risk"
                : portfolioScore >= 40
                ? "Elevated Risk"
                : "High Risk"}
            </p>
          </div>
          <div className="flex gap-6 text-sm">
            <div>
              <p className="text-white/50">Logged risks</p>
              <p className="text-xl font-bold">{logged}</p>
            </div>
            <div>
              <p className="text-white/50">Auto-detected</p>
              <p className="text-xl font-bold">{auto}</p>
            </div>
            <div>
              <p className="text-white/50">High/Critical</p>
              <p className="text-xl font-bold text-red-300">{high}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Domain breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Risk by Domain</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingDomains ? (
            <SectionLoader />
          ) : !domains?.length ? (
            <p className="text-sm text-neutral-400 text-center py-6">No domain data available.</p>
          ) : (
            <div className="space-y-3">
              {domains.map((d) => {
                const pct = Math.min(100, d.risk_score ?? 0);
                const bar =
                  pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500";
                return (
                  <div key={d.domain} className="flex items-center gap-3">
                    <div className="w-32 shrink-0 text-sm text-neutral-700 font-medium">
                      {DOMAIN_LABELS[d.domain] ?? d.domain}
                    </div>
                    <div className="flex-1 h-3 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className={cn("h-full rounded-full transition-all", bar)}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="w-12 text-right text-sm font-semibold text-neutral-700">
                      {pct.toFixed(0)}
                    </div>
                    <Badge variant={(d.critical_count + d.high_count) > 0 ? "warning" : "success"} className="shrink-0">
                      {d.total} total
                    </Badge>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 2 — Project Risk
// ─────────────────────────────────────────────────────────────────────────────

function SeverityDot({ severity }: { severity: string }) {
  const cls =
    severity === "critical"
      ? "bg-red-600"
      : severity === "high"
      ? "bg-red-400"
      : severity === "medium"
      ? "bg-amber-400"
      : "bg-green-400";
  return <span className={cn("inline-block h-2 w-2 rounded-full shrink-0", cls)} />;
}

function SeverityChip({ severity }: { severity: string }) {
  const variant =
    severity === "critical" || severity === "high"
      ? "error"
      : severity === "medium"
      ? "warning"
      : "success";
  return <Badge variant={variant as "error" | "warning" | "success"}>{severity}</Badge>;
}

function RiskDetailPanel({ projectId }: { projectId: string }) {
  const { data, isLoading } = useAlleyRiskDetail(projectId);
  const updateMutation = useUpdateMitigation();
  const [selectedRiskId, setSelectedRiskId] = useState<string | null>(null);
  const [newStatus, setNewStatus] = useState("");
  const [notes, setNotes] = useState("");

  if (isLoading) return <SectionLoader />;
  if (!data?.risk_items?.length)
    return (
      <div className="border-t border-neutral-100 bg-neutral-50 px-5 py-4 text-sm text-neutral-400">
        No risk items recorded yet.
      </div>
    );

  return (
    <div className="border-t border-neutral-100 bg-neutral-50 px-5 py-5 rounded-b-lg space-y-2">
      {data.risk_items.map((item) => (
        <div key={item.id} className="bg-white rounded-lg border border-neutral-100 p-3 space-y-2">
          <div className="flex items-start gap-2">
            <SeverityDot severity={item.severity} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-neutral-900">{item.title}</p>
              <p className="text-xs text-neutral-500 mt-0.5">{item.description}</p>
            </div>
            <SeverityChip severity={item.severity} />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="neutral" className="text-xs capitalize">{item.dimension}</Badge>
            <Badge variant="neutral" className="text-xs">
              {MITIGATION_STATUS_LABELS[item.mitigation_status] ?? item.mitigation_status}
            </Badge>
          </div>
          {/* Inline update */}
          {selectedRiskId === item.id ? (
            <div className="flex gap-2 flex-wrap pt-1">
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="rounded border border-neutral-200 text-xs px-2 py-1"
              >
                <option value="">Set status…</option>
                {Object.entries(MITIGATION_STATUS_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
              <input
                placeholder="Notes…"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="flex-1 min-w-[120px] rounded border border-neutral-200 text-xs px-2 py-1"
              />
              <button
                disabled={!newStatus || updateMutation.isPending}
                onClick={() => {
                  updateMutation.mutate(
                    { projectId, riskId: item.id, status: newStatus, notes },
                    { onSuccess: () => { setSelectedRiskId(null); setNewStatus(""); setNotes(""); } }
                  );
                }}
                className="rounded bg-[#1B2A4A] px-2 py-1 text-xs text-white disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => setSelectedRiskId(null)}
                className="rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-600"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setSelectedRiskId(item.id); setNewStatus(""); setNotes(""); }}
              className="text-xs text-blue-600 hover:underline"
            >
              Update mitigation
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function ProjectRiskTab() {
  const { data, isLoading } = useAlleyRisks();
  const runCheck = useRunRiskCheck();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const projects = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-500">{projects.length} projects in portfolio</p>
      </div>

      {isLoading ? (
        <SectionLoader />
      ) : !projects.length ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16 text-center">
            <ShieldAlert className="h-10 w-10 text-neutral-300 mb-3" />
            <p className="text-base font-semibold text-neutral-700">No projects yet</p>
            <p className="text-sm text-neutral-400 mt-1 max-w-xs">
              Risk data will appear here once you have projects in your pipeline.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {projects.map((project) => (
            <div key={project.project_id} className="border border-neutral-200 rounded-lg bg-white overflow-hidden">
              <button
                onClick={() => setExpandedId((p) => (p === project.project_id ? null : project.project_id))}
                className="w-full px-5 py-4 flex items-center gap-3 text-left hover:bg-neutral-50 transition-colors"
              >
                <div className="shrink-0 text-neutral-400">
                  {expandedId === project.project_id ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-neutral-900 truncate">{project.project_name}</p>
                  <p className="text-xs text-neutral-500">{project.total_risks} risks total</p>
                </div>
                <div className="hidden sm:flex items-center gap-3 shrink-0">
                  {project.critical_count > 0 && (
                    <Badge variant="error">{project.critical_count} critical</Badge>
                  )}
                  {project.high_count > 0 && (
                    <Badge variant="warning">{project.high_count} high</Badge>
                  )}
                  <span
                    className={cn(
                      "text-sm font-bold tabular-nums",
                      riskScoreColor(project.overall_risk_score)
                    )}
                  >
                    {project.overall_risk_score}
                  </span>
                  <button
                    disabled={runCheck.isPending}
                    onClick={(e) => { e.stopPropagation(); runCheck.mutate(project.project_id); }}
                    className="rounded bg-neutral-100 px-2 py-1 text-xs text-neutral-600 hover:bg-neutral-200 disabled:opacity-50"
                  >
                    {runCheck.isPending ? "…" : "Check"}
                  </button>
                </div>
              </button>
              {expandedId === project.project_id && <RiskDetailPanel projectId={project.project_id} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 3 — Development Advisor
// ─────────────────────────────────────────────────────────────────────────────

function FinancingTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useFinancingReadiness(projectId);
  if (isLoading) return <SectionLoader />;
  if (!data) return <p className="text-sm text-neutral-400 py-6 text-center">No data available.</p>;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="text-4xl font-bold text-neutral-900">{data.readiness_score}</div>
        <div>
          <p className="text-sm font-medium text-neutral-700">{data.readiness_label}</p>
        </div>
      </div>
      {data.strengths?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Strengths</p>
          <ul className="space-y-1">
            {data.strengths.map((s, i) => (
              <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                <span className="mt-0.5">✓</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.gaps?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Gaps</p>
          <ul className="space-y-1">
            {data.gaps.map((g, i) => (
              <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                <span className="mt-0.5">✗</span> {g}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.next_steps?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Next Steps</p>
          <ol className="space-y-1 list-decimal list-inside">
            {data.next_steps.map((s, i) => (
              <li key={i} className="text-sm text-neutral-700">{s}</li>
            ))}
          </ol>
        </div>
      )}
      {data.recommended_instruments?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Recommended Instruments</p>
          <div className="flex flex-wrap gap-2">
            {data.recommended_instruments.map((inst, i) => (
              <Badge key={i} variant="info">{inst}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PositioningTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useMarketPositioning(projectId);
  if (isLoading) return <SectionLoader />;
  if (!data) return <p className="text-sm text-neutral-400 py-6 text-center">No data available.</p>;
  return (
    <div className="space-y-4">
      {data.positioning_summary && (
        <p className="text-sm text-neutral-700">{data.positioning_summary}</p>
      )}
      {data.competitive_advantages?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Competitive Advantages</p>
          <ul className="space-y-1">
            {data.competitive_advantages.map((adv, i) => (
              <li key={i} className="text-sm text-neutral-700 flex items-start gap-2">
                <span className="text-green-500 mt-0.5">✓</span> {adv}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.market_risks?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Market Risks</p>
          <ul className="space-y-1">
            {data.market_risks.map((r, i) => (
              <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                <span className="mt-0.5">!</span> {r}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.target_investor_profiles?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Target Investor Profiles</p>
          <div className="flex flex-wrap gap-2">
            {data.target_investor_profiles.map((p, i) => (
              <Badge key={i} variant="neutral">{p}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MilestonesTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useMilestonePlan(projectId);
  if (isLoading) return <SectionLoader />;
  if (!data?.milestones?.length) return <p className="text-sm text-neutral-400 py-6 text-center">No milestones available.</p>;
  return (
    <div className="space-y-2">
      {data.milestones.map((m, i) => (
        <div key={i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-neutral-100">
          <Badge variant={milestoneStatusVariant(m.status) as "success" | "warning" | "neutral" | "error"}>
            {m.status}
          </Badge>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-neutral-900">{m.title}</p>
            {m.description && <p className="text-xs text-neutral-500 mt-0.5">{m.description}</p>}
          </div>
          {m.target_months != null && (
            <span className="text-xs text-neutral-400 shrink-0">
              {m.target_months}mo
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function RegulatoryTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useRegulatoryGuidance(projectId);
  if (isLoading) return <SectionLoader />;
  if (!data) return <p className="text-sm text-neutral-400 py-6 text-center">No data available.</p>;
  return (
    <div className="space-y-4">
      {data.jurisdiction && (
        <div className="flex items-center gap-2">
          <Badge variant="neutral">{data.jurisdiction}</Badge>
          {data.timeline_estimate && (
            <span className="text-sm text-neutral-500">Timeline: {data.timeline_estimate}</span>
          )}
        </div>
      )}
      {data.key_requirements?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Key Requirements</p>
          <ul className="space-y-1">
            {data.key_requirements.map((req, i) => (
              <li key={i} className="text-sm text-neutral-700 flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">→</span> {req}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.approvals_needed?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Approvals Needed</p>
          <div className="flex flex-wrap gap-2">
            {data.approvals_needed.map((a, i) => (
              <Badge key={i} variant="warning">{a}</Badge>
            ))}
          </div>
        </div>
      )}
      {data.risk_areas?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Risk Areas</p>
          <ul className="space-y-1">
            {data.risk_areas.map((r, i) => (
              <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                <span className="mt-0.5">!</span> {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AdvisorTab() {
  const { data: projects } = useAlleyScores();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [query, setQuery] = useState("");
  const advisorMutation = useAdvisorQuery();

  const effectiveProjectId = selectedProjectId || projects?.projects?.[0]?.project_id || "";

  return (
    <div className="space-y-6">
      {/* Project selector */}
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm font-medium text-neutral-700">Project:</label>
        <select
          value={selectedProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        >
          <option value="">
            {projects?.projects?.[0]?.project_name ?? "Select project…"}
          </option>
          {projects?.projects?.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.project_name}
            </option>
          ))}
        </select>
      </div>

      {/* Sub-tabs */}
      <Tabs defaultValue="financing">
        <TabsList>
          <TabsTrigger value="financing">Financing</TabsTrigger>
          <TabsTrigger value="positioning">Positioning</TabsTrigger>
          <TabsTrigger value="milestones">Milestones</TabsTrigger>
          <TabsTrigger value="regulatory">Regulatory</TabsTrigger>
        </TabsList>
        <TabsContent value="financing" className="mt-4">
          <FinancingTab projectId={effectiveProjectId} />
        </TabsContent>
        <TabsContent value="positioning" className="mt-4">
          <PositioningTab projectId={effectiveProjectId} />
        </TabsContent>
        <TabsContent value="milestones" className="mt-4">
          <MilestonesTab projectId={effectiveProjectId} />
        </TabsContent>
        <TabsContent value="regulatory" className="mt-4">
          <RegulatoryTab projectId={effectiveProjectId} />
        </TabsContent>
      </Tabs>

      {/* Ask advisor */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            Ask the Advisor
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && query.trim() && effectiveProjectId) {
                  advisorMutation.mutate({ id: effectiveProjectId, query: query.trim() });
                }
              }}
              placeholder="Ask about financing, risk, milestones…"
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              disabled={!query.trim() || !effectiveProjectId || advisorMutation.isPending}
              onClick={() => advisorMutation.mutate({ id: effectiveProjectId, query: query.trim() })}
              className="rounded-lg bg-[#1B2A4A] px-4 py-2 text-sm font-medium text-white hover:bg-[#243660] disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          {advisorMutation.isPending && <SectionLoader />}
          {advisorMutation.data && (
            <div className="mt-4 rounded-lg bg-blue-50 border border-blue-100 p-4">
              <p className="text-sm text-neutral-800 whitespace-pre-wrap">
                {advisorMutation.data.response}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 4 — Score Journey
// ─────────────────────────────────────────────────────────────────────────────

function ImprovementBadge({ value }: { value: number }) {
  if (value > 0)
    return <span className="text-sm font-bold text-green-600">+{value.toFixed(1)}</span>;
  if (value < 0)
    return <span className="text-sm font-bold text-red-600">{value.toFixed(1)}</span>;
  return <span className="text-sm font-bold text-neutral-400">0.0</span>;
}

function JourneyPanel({ projectId }: { projectId: string }) {
  const { data: journeyData, isLoading: loadingJourney } = useScoreJourney(projectId);
  const { data: insightsData, isLoading: loadingInsights } = useScoreInsights(projectId);

  const chartData =
    journeyData?.journey?.map((pt) => ({
      version: pt.version,
      score: pt.overall_score,
    })) ?? [];

  return (
    <div className="border-t border-neutral-100 bg-neutral-50 px-5 py-5 rounded-b-lg space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-neutral-800 mb-3">Score Journey</h3>
        {loadingJourney ? (
          <SectionLoader />
        ) : !chartData.length ? (
          <p className="text-sm text-neutral-400 text-center py-6">No score history recorded yet.</p>
        ) : (
          <div className="bg-white rounded-lg border border-neutral-100 p-3">
            <LineChart
              data={chartData}
              xKey="version"
              yKeys={["score"]}
              yLabels={{ score: "Overall Score" }}
              height={220}
            />
            {journeyData && (
              <div className="mt-2 text-xs text-neutral-400 text-center">
                {chartData.length} versions &middot; Total improvement:{" "}
                <span
                  className={cn(
                    "font-semibold",
                    journeyData.total_improvement >= 0 ? "text-green-600" : "text-red-600"
                  )}
                >
                  {journeyData.total_improvement >= 0 ? "+" : ""}
                  {journeyData.total_improvement.toFixed(1)} pts
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {journeyData?.journey?.some((pt) => pt.event_label) && (
        <div>
          <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
            Key Events
          </h4>
          <div className="space-y-1.5">
            {journeyData.journey
              .filter((pt) => pt.event_label)
              .map((pt) => (
                <div key={pt.version} className="flex items-center gap-3 text-sm">
                  <Badge variant="neutral" className="shrink-0">
                    v{pt.version}
                  </Badge>
                  <span className="text-neutral-700">{pt.event_label}</span>
                  <span className="text-neutral-400 text-xs ml-auto">
                    {new Date(pt.calculated_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-neutral-800 mb-3 flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          Score Insights
        </h3>
        {loadingInsights ? (
          <SectionLoader />
        ) : !insightsData?.insights?.length ? (
          <p className="text-sm text-neutral-400 text-center py-4">No insights available yet.</p>
        ) : (
          <div className="space-y-2">
            {insightsData.insights.map((insight, i) => (
              <div key={i} className="bg-white border border-neutral-100 rounded-lg px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="neutral" className="text-xs">
                        {insight.dimension}
                      </Badge>
                    </div>
                    <p className="text-sm text-neutral-800 mb-1">{insight.insight}</p>
                    <p className="text-xs text-blue-600">{insight.recommendation}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-xs text-neutral-400">Impact</p>
                    <p className={cn("text-sm", impactColor(insight.estimated_impact))}>
                      +{insight.estimated_impact} pts
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreJourneyTab() {
  const { data, isLoading } = useScorePerformanceList();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function toggle(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <div className="space-y-4">
      {isLoading ? (
        <SectionLoader />
      ) : !data?.items?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center py-16 text-center">
            <TrendingUp className="h-10 w-10 text-neutral-300 mb-3" />
            <p className="text-base font-semibold text-neutral-700">No score history yet</p>
            <p className="text-sm text-neutral-400 mt-1 max-w-xs">
              Score journeys appear here as signal scores are recalculated over time.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {data.items.map((project) => (
            <div
              key={project.project_id}
              className="border border-neutral-200 rounded-lg bg-white overflow-hidden"
            >
              <button
                onClick={() => toggle(project.project_id)}
                className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-neutral-50 transition-colors"
              >
                <div className="shrink-0 text-neutral-400">
                  {expandedId === project.project_id ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="font-semibold text-neutral-900 truncate block">
                    {project.project_name}
                  </span>
                </div>
                <div className="hidden sm:flex items-center gap-8">
                  <div className="text-center">
                    <p className="text-xs text-neutral-400 mb-0.5">Current</p>
                    <p className="text-lg font-bold text-neutral-900">
                      {project.current_score.toFixed(1)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-neutral-400 mb-0.5">Start</p>
                    <p className="text-base font-medium text-neutral-600">
                      {project.start_score.toFixed(1)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-neutral-400 mb-0.5">Change</p>
                    <ImprovementBadge value={project.total_improvement} />
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-neutral-400 mb-0.5">Versions</p>
                    <p className="text-sm font-medium text-neutral-600">{project.versions}</p>
                  </div>
                  <Badge variant={trendVariant(project.trend)}>
                    {trendIcon(project.trend)} {project.trend}
                  </Badge>
                </div>
              </button>
              {expandedId === project.project_id && (
                <JourneyPanel projectId={project.project_id} />
              )}
            </div>
          ))}
        </div>
      )}
      {data && data.total > 0 && (
        <p className="text-xs text-neutral-400 text-center">
          Showing {data.items.length} of {data.total} projects
        </p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 5 — Pipeline Analytics
// ─────────────────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4">
        <div className="flex items-start justify-between mb-2">
          <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide">{label}</p>
          <span className="text-neutral-300">{icon}</span>
        </div>
        <p className="text-2xl font-bold text-neutral-900">{value}</p>
        {sub && <p className="text-xs text-neutral-400 mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function StageDistributionChart() {
  const { data, isLoading } = useStageDistribution();
  if (isLoading) return <SectionLoader />;
  if (!data?.length)
    return <p className="text-sm text-neutral-400 text-center py-8">No stage data available.</p>;

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const stageColors = [
    "bg-blue-500", "bg-indigo-500", "bg-violet-500",
    "bg-purple-500", "bg-pink-500", "bg-rose-500",
  ];

  return (
    <div className="space-y-3">
      {data.map((item, i) => {
        const pct = (item.count / maxCount) * 100;
        return (
          <div key={item.stage} className="flex items-center gap-3">
            <div className="w-28 shrink-0 text-xs text-neutral-600 text-right truncate">
              {item.stage}
            </div>
            <div className="flex-1 h-6 bg-neutral-100 rounded overflow-hidden flex items-center">
              <div
                className={cn(
                  "h-full rounded transition-all flex items-center px-2",
                  stageColors[i % stageColors.length]
                )}
                style={{ width: `${Math.max(pct, 4)}%` }}
              >
                <span className="text-xs text-white font-medium">{item.count}</span>
              </div>
            </div>
            <div className="w-24 shrink-0 text-xs text-neutral-400 text-right">
              {item.total_mw > 0 ? `${item.total_mw.toFixed(0)} MW` : ""}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ScoreDistributionChart() {
  const { data, isLoading } = useScoreDistribution();
  if (isLoading) return <SectionLoader />;
  if (!data?.length)
    return <p className="text-sm text-neutral-400 text-center py-8">No score distribution data.</p>;

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const bucketColors: Record<string, string> = {
    "0-20": "bg-red-500",
    "20-40": "bg-orange-500",
    "40-60": "bg-amber-500",
    "60-80": "bg-lime-500",
    "80-100": "bg-green-500",
  };

  return (
    <div className="flex items-end gap-2 h-32">
      {data.map((item) => {
        const heightPct = (item.count / maxCount) * 100;
        const color = bucketColors[item.bucket] ?? "bg-blue-500";
        return (
          <div key={item.bucket} className="flex flex-col items-center gap-1 flex-1">
            <span className="text-xs font-medium text-neutral-600">{item.count}</span>
            <div className="w-full flex items-end" style={{ height: "80px" }}>
              <div
                className={cn("w-full rounded-t transition-all", color)}
                style={{ height: `${Math.max(heightPct, 4)}%` }}
              />
            </div>
            <span className="text-xs text-neutral-400 truncate w-full text-center">
              {item.bucket}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function RiskHeatmapTable() {
  const { data, isLoading } = useRiskHeatmap();
  if (isLoading) return <SectionLoader />;
  if (!data?.length)
    return <p className="text-sm text-neutral-400 text-center py-8">No risk heatmap data.</p>;

  const RISK_DIMS = [
    { key: "technical" as const, label: "Technical" },
    { key: "financial" as const, label: "Financial" },
    { key: "regulatory" as const, label: "Regulatory" },
    { key: "esg" as const, label: "ESG" },
    { key: "market" as const, label: "Market" },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-100">
            <th className="pb-2 text-left text-xs font-medium text-neutral-500 pr-4">Project</th>
            {RISK_DIMS.map((d) => (
              <th key={d.key} className="pb-2 text-center text-xs font-medium text-neutral-500 px-2">
                {d.label}
              </th>
            ))}
            <th className="pb-2 text-center text-xs font-medium text-neutral-500 px-2">Overall</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.project_id} className="border-b border-neutral-50 last:border-0">
              <td className="py-2 pr-4 font-medium text-neutral-800 max-w-[140px] truncate">
                {row.project_name}
              </td>
              {RISK_DIMS.map((d) => {
                const score = row[d.key] as number;
                return (
                  <td key={d.key} className="py-2 px-2 text-center">
                    <span
                      className={cn(
                        "inline-block rounded px-2 py-0.5 text-xs font-semibold",
                        riskCellBg(score)
                      )}
                    >
                      {score}
                    </span>
                  </td>
                );
              })}
              <td className="py-2 px-2 text-center">
                <Badge
                  variant={
                    row.overall_risk_level === "high" || row.overall_risk_level === "critical"
                      ? "error"
                      : row.overall_risk_level === "medium"
                      ? "warning"
                      : "neutral"
                  }
                >
                  {row.overall_risk_level}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocumentCompletenessList() {
  const { data, isLoading } = useDocumentCompleteness();
  if (isLoading) return <SectionLoader />;
  if (!data?.length)
    return <p className="text-sm text-neutral-400 text-center py-8">No document completeness data.</p>;

  return (
    <div className="space-y-3">
      {data.map((item) => {
        const pct = Math.min(100, Math.max(0, item.completeness_pct));
        const barColor =
          pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
        return (
          <div key={item.project_id} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-neutral-800 truncate mr-2">{item.project_name}</span>
              <span className="shrink-0 text-neutral-500 text-xs">
                {item.uploaded_count}/{item.expected_count} docs &middot; {pct.toFixed(0)}%
              </span>
            </div>
            <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", barColor)}
                style={{ width: `${pct}%` }}
              />
            </div>
            {item.missing_types.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {item.missing_types.slice(0, 5).map((t) => (
                  <span key={t} className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                    Missing: {t}
                  </span>
                ))}
                {item.missing_types.length > 5 && (
                  <span className="text-xs text-neutral-400">+{item.missing_types.length - 5} more</span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function PipelineTab() {
  const { data: overview, isLoading: loadingOverview } = useAlleyOverview();

  return (
    <div className="space-y-6">
      {loadingOverview ? (
        <SectionLoader />
      ) : overview ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label="Total Projects"
            value={String(overview.total_projects)}
            sub={`${overview.scored_projects} scored`}
            icon={<Target className="h-5 w-5" />}
          />
          <StatCard
            label="Total Capacity"
            value={`${overview.total_mw.toFixed(0)} MW`}
            sub="Aggregate pipeline"
            icon={<Zap className="h-5 w-5" />}
          />
          <StatCard
            label="Avg Signal Score"
            value={overview.avg_score.toFixed(1)}
            sub="Portfolio average"
            icon={<BarChart2 className="h-5 w-5" />}
          />
          <StatCard
            label="Total Value"
            value={formatCurrency(overview.total_value, overview.currency)}
            sub="Aggregate investment"
            icon={<DollarSign className="h-5 w-5" />}
          />
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Stage Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <StageDistributionChart />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Score Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ScoreDistributionChart />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Risk Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <RiskHeatmapTable />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <FileText className="h-4 w-4 text-neutral-500" />
          <CardTitle className="text-sm">Document Completeness</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentCompletenessList />
        </CardContent>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default function RiskDashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ShieldAlert className="h-6 w-6 text-[#1B2A4A]" />
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Risk Dashboard</h1>
          <p className="text-sm text-neutral-500">
            Unified project intelligence — risk, advisor, score journey, and pipeline analytics
          </p>
        </div>
      </div>

      <InfoBanner>
        <strong>Risk Dashboard</strong> provides continuous monitoring of project and portfolio risks across technical, financial, regulatory, ESG, and market dimensions. Active alerts notify you when risks change status, and AI generates <strong>structured mitigation strategies</strong> on demand.
      </InfoBanner>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="project-risk">Project Risk</TabsTrigger>
          <TabsTrigger value="advisor">Development Advisor</TabsTrigger>
          <TabsTrigger value="score-journey">Score Journey</TabsTrigger>
          <TabsTrigger value="pipeline">Pipeline Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab />
        </TabsContent>

        <TabsContent value="project-risk" className="mt-6">
          <ProjectRiskTab />
        </TabsContent>

        <TabsContent value="advisor" className="mt-6">
          <AdvisorTab />
        </TabsContent>

        <TabsContent value="score-journey" className="mt-6">
          <ScoreJourneyTab />
        </TabsContent>

        <TabsContent value="pipeline" className="mt-6">
          <PipelineTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
