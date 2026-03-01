"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Bell,
  BellOff,
  ChevronDown,
  ChevronRight,
  Download,
  Filter,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  LineChart,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@scr/ui";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import {
  useRiskDashboard,
  useRunScenario,
  useComplianceStatus,
  useAuditTrail,
  useDomainScores,
  useMonitoringAlerts,
  useResolveAlert,
  useTriggerMonitoringCheck,
  useGenerateMitigation,
  severityColor,
  severityBadge,
  probabilityLabel,
  sfdrLabel,
  sfdrColor,
  complianceStatusColor,
  paiStatusColor,
  domainRiskColor,
  domainRiskLabel,
  alertSeverityBadge,
  DOMAIN_LABELS,
  DOMAIN_COLORS,
  SEVERITY_ORDER,
  PROBABILITY_ORDER,
  SCENARIO_TYPES,
  type RiskDashboard,
  type ConcentrationItem,
  type ScenarioResult,
  type ComplianceStatus,
  type AuditEntry,
  type ScenarioType,
  type FiveDomainRisk,
  type MonitoringAlert,
  type MitigationResponse,
} from "@/lib/risk";
import { usePortfolios } from "@/lib/portfolio";
import { AIFeedback } from "@/components/ai-feedback";
import { CitationBadges } from "@/components/citations/citation-badges";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

// ── Portfolio Selector ────────────────────────────────────────────────────────

function PortfolioSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (id: string) => void;
}) {
  const { data } = usePortfolios();
  return (
    <select
      className="text-sm border border-neutral-200 rounded px-3 py-1.5 bg-white font-medium"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">Select portfolio…</option>
      {data?.items.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}

// ── Risk Heatmap ──────────────────────────────────────────────────────────────

const HEAT_COLORS: Record<number, string> = {
  0: "bg-neutral-100 text-neutral-400",
  1: "bg-green-100 text-green-700",
  2: "bg-amber-100 text-amber-700",
  3: "bg-orange-200 text-orange-700",
  4: "bg-red-100 text-red-700",
  5: "bg-red-200 text-red-800",
  6: "bg-red-400 text-white",
  7: "bg-red-600 text-white",
};

function heatColor(severity: string, probability: string, count: number): string {
  if (count === 0) return HEAT_COLORS[0];
  const si = SEVERITY_ORDER.indexOf(severity as any) + 1;
  const pi = PROBABILITY_ORDER.indexOf(probability as any) + 1;
  const score = Math.ceil((si + pi) / 2);
  return HEAT_COLORS[Math.min(score, 7)] ?? HEAT_COLORS[7];
}

function RiskHeatmap({ dashboard }: { dashboard: RiskDashboard }) {
  const { heatmap } = dashboard;

  const cellMap: Record<string, number> = {};
  for (const c of heatmap.cells) {
    cellMap[`${c.severity}:${c.probability}`] = c.count;
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[380px]">
        {/* Y-axis label */}
        <div className="flex">
          <div className="w-24 flex-shrink-0" />
          <p className="text-xs font-medium text-neutral-500 mb-1 flex-1 text-center">
            Probability →
          </p>
        </div>
        {/* Header row */}
        <div className="flex gap-1">
          <div className="w-24 flex-shrink-0" />
          {PROBABILITY_ORDER.map((prob) => (
            <div
              key={prob}
              className="flex-1 text-center text-xs text-neutral-500 font-medium py-1"
            >
              {probabilityLabel(prob)}
            </div>
          ))}
        </div>
        {/* Grid rows (severity high→low for visual convention) */}
        {[...SEVERITY_ORDER].reverse().map((sev) => (
          <div key={sev} className="flex gap-1 mb-1">
            <div className="w-24 flex-shrink-0 flex items-center">
              <span className="text-xs text-neutral-500 font-medium capitalize">
                {sev}
              </span>
            </div>
            {PROBABILITY_ORDER.map((prob) => {
              const count = cellMap[`${sev}:${prob}`] ?? 0;
              return (
                <div
                  key={prob}
                  className={`flex-1 h-12 rounded flex items-center justify-center text-sm font-semibold transition-colors ${heatColor(sev, prob, count)}`}
                >
                  {count > 0 ? count : ""}
                </div>
              );
            })}
          </div>
        ))}
        <p className="text-xs text-neutral-400 mt-2 text-center">
          {heatmap.total_risks} manual risks logged
        </p>
      </div>
    </div>
  );
}

// ── Concentration Bar ─────────────────────────────────────────────────────────

function ConcentrationBar({ item }: { item: ConcentrationItem }) {
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-neutral-600 truncate max-w-[140px]">{item.label}</span>
        <span
          className={`font-semibold ${item.is_concentrated ? "text-red-600" : "text-neutral-700"}`}
        >
          {item.pct.toFixed(1)}%
          {item.is_concentrated && (
            <AlertTriangle className="inline h-3 w-3 ml-1 text-red-500" />
          )}
        </span>
      </div>
      <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${item.is_concentrated ? "bg-red-400" : "bg-primary-500"}`}
          style={{ width: `${Math.min(item.pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

// ── Risk Dashboard Tab ────────────────────────────────────────────────────────

function DashboardTab({ portfolioId }: { portfolioId: string }) {
  const { data, isLoading } = useRiskDashboard(portfolioId);

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <NoPortfolio />;

  const trendData = data.risk_trend.map((p) => ({
    date: p.date,
    risk_score: p.risk_score,
  }));

  return (
    <div className="space-y-6">
      {/* Overview row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5 flex items-center gap-4">
            <ScoreGauge score={data.overall_risk_score} size={72} />
            <div>
              <p className="text-xs text-neutral-500 font-medium uppercase tracking-wide">
                Overall Risk Score
              </p>
              <p className="text-2xl font-bold text-neutral-800">
                {data.overall_risk_score.toFixed(0)}
                <span className="text-sm font-normal text-neutral-400">/100</span>
              </p>
              <p className="text-xs text-neutral-500 mt-0.5">
                {data.heatmap.total_risks} risks logged ·{" "}
                {data.auto_identified.length} auto-identified
              </p>
              <AIFeedback
                taskType="risk_assessment"
                entityType="portfolio"
                entityId={portfolioId}
                compact
                className="mt-2"
              />
              {/* Add aiTaskLogId from AI task log when available */}
              <CitationBadges aiTaskLogId={undefined} className="mt-1" />
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardContent className="p-4">
            <p className="text-xs font-medium text-neutral-500 mb-3">
              Risk Score Trend (6 months)
            </p>
            <LineChart
              data={trendData}
              xKey="date"
              yKeys={["risk_score"]}
              yLabels={{ risk_score: "Risk Score" }}
              height={100}
            />
          </CardContent>
        </Card>
      </div>

      {/* Heatmap + Top risks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-semibold text-neutral-700 mb-4">
              Risk Heatmap
            </p>
            <RiskHeatmap dashboard={data} />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-semibold text-neutral-700 mb-3">
              Top Risks
            </p>
            {data.top_risks.length === 0 && data.auto_identified.length === 0 ? (
              <p className="text-sm text-neutral-400">No risks logged yet.</p>
            ) : (
              <div className="space-y-2">
                {data.top_risks.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-start gap-2 p-2 rounded-lg bg-neutral-50"
                  >
                    <Badge variant={severityBadge(r.severity)} className="mt-0.5 flex-shrink-0 capitalize">
                      {r.severity}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-neutral-700 capitalize">
                        {r.risk_type.replace("_", " ")}
                      </p>
                      <p className="text-xs text-neutral-500 line-clamp-2">
                        {r.description}
                      </p>
                    </div>
                  </div>
                ))}
                {data.auto_identified.map((r, i) => (
                  <div
                    key={`auto-${i}`}
                    className="flex items-start gap-2 p-2 rounded-lg bg-amber-50 border border-amber-100"
                  >
                    <Badge variant="warning" className="mt-0.5 flex-shrink-0 capitalize">
                      Auto
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-neutral-700 capitalize">
                        {r.risk_type.replace("_", " ")}
                      </p>
                      <p className="text-xs text-neutral-500 line-clamp-2">
                        {r.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Concentration */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-neutral-700">
              Concentration Analysis
            </p>
            {data.concentration.concentration_flags.length > 0 && (
              <Badge variant="error">
                {data.concentration.concentration_flags.length} flag
                {data.concentration.concentration_flags.length > 1 ? "s" : ""}
              </Badge>
            )}
          </div>
          {data.concentration.concentration_flags.length > 0 && (
            <div className="bg-red-50 border border-red-100 rounded-lg p-3 mb-4">
              {data.concentration.concentration_flags.map((f, i) => (
                <p key={i} className="text-xs text-red-700 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                  {f}
                </p>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {(
              [
                ["By Sector", data.concentration.by_sector],
                ["By Geography", data.concentration.by_geography],
                ["By Counterparty", data.concentration.by_counterparty],
                ["By Currency", data.concentration.by_currency],
              ] as [string, ConcentrationItem[]][]
            ).map(([label, items]) => (
              <div key={label}>
                <p className="text-xs font-medium text-neutral-500 mb-2">{label}</p>
                {items.slice(0, 5).map((item) => (
                  <ConcentrationBar key={item.label} item={item} />
                ))}
                {items.length === 0 && (
                  <p className="text-xs text-neutral-400">No data</p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Scenario Analysis Tab ─────────────────────────────────────────────────────

function ScenarioTab({ portfolioId }: { portfolioId: string }) {
  const [selectedType, setSelectedType] = useState<ScenarioType>(SCENARIO_TYPES[0]);
  const [params, setParams] = useState<Record<string, number>>(() =>
    Object.fromEntries(
      SCENARIO_TYPES[0].params.map((p) => [p.key, p.default])
    )
  );
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const runScenario = useRunScenario(portfolioId);

  const handleSelectScenario = (type: (typeof SCENARIO_TYPES)[number]) => {
    setSelectedType(type);
    setParams(Object.fromEntries(type.params.map((p) => [p.key, p.default])));
    setResult(null);
  };

  const handleRun = async () => {
    const res = await runScenario.mutateAsync({
      scenario_type: selectedType.value,
      parameters: params,
    });
    setResult(res);
  };

  return (
    <div className="space-y-6">
      {/* Scenario selector */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-neutral-700 mb-3">
            Select Scenario
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
            {SCENARIO_TYPES.map((st) => (
              <button
                key={st.value}
                onClick={() => handleSelectScenario(st)}
                className={`text-left p-3 rounded-lg border text-xs transition-colors ${
                  selectedType.value === st.value
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-neutral-200 hover:border-neutral-300 text-neutral-600"
                }`}
              >
                <p className="font-semibold">{st.label}</p>
                <p className="mt-0.5 text-neutral-500 leading-tight">
                  {st.description}
                </p>
              </button>
            ))}
          </div>

          {/* Parameter sliders */}
          <div className="space-y-4">
            {selectedType.params.map((p) => (
              <div key={p.key}>
                <div className="flex justify-between text-xs mb-1">
                  <label className="font-medium text-neutral-700">
                    {p.label}
                  </label>
                  <span className="font-semibold text-primary-700">
                    {params[p.key] ?? p.default}
                  </span>
                </div>
                <input
                  type="range"
                  min={p.min}
                  max={p.max}
                  step={p.max - p.min > 100 ? 10 : 1}
                  value={params[p.key] ?? p.default}
                  onChange={(e) =>
                    setParams((prev) => ({
                      ...prev,
                      [p.key]: Number(e.target.value),
                    }))
                  }
                  className="w-full accent-primary-600"
                />
                <div className="flex justify-between text-xs text-neutral-400">
                  <span>{p.min}</span>
                  <span>{p.max}</span>
                </div>
              </div>
            ))}
          </div>

          <Button
            className="mt-4"
            onClick={handleRun}
            disabled={!portfolioId || runScenario.isPending}
          >
            {runScenario.isPending ? "Running…" : "Run Scenario"}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Narrative */}
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-neutral-600 italic">{result.narrative}</p>
            </CardContent>
          </Card>

          {/* Before / After summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: "NAV Before",
                value: fmt(result.nav_before),
                sub: null,
                color: "text-neutral-800",
              },
              {
                label: "NAV After",
                value: fmt(result.nav_after),
                sub: null,
                color: result.nav_delta < 0 ? "text-red-600" : "text-green-600",
              },
              {
                label: "NAV Δ",
                value: `${result.nav_delta_pct.toFixed(1)}%`,
                sub: fmt(result.nav_delta),
                color: result.nav_delta < 0 ? "text-red-600" : "text-green-600",
              },
              {
                label: "Net IRR",
                value:
                  result.irr_before != null
                    ? `${(result.irr_before * 100).toFixed(1)}% → ${result.irr_after != null ? (result.irr_after * 100).toFixed(1) : "N/A"}%`
                    : "N/A",
                sub: null,
                color: "text-neutral-700",
              },
            ].map((m) => (
              <Card key={m.label}>
                <CardContent className="p-4">
                  <p className="text-xs text-neutral-500 mb-1">{m.label}</p>
                  <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
                  {m.sub && (
                    <p className={`text-xs mt-0.5 ${m.color}`}>{m.sub}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Waterfall */}
          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-neutral-700 mb-4">
                Impact Waterfall
              </p>
              <div className="space-y-1.5">
                {result.waterfall.map((w, i) => {
                  const isBase =
                    w.label === "Baseline NAV" || w.label === "Stressed NAV";
                  const barPct = isBase
                    ? 100
                    : Math.min(
                        Math.abs(w.value) /
                          Math.max(result.nav_before, 1) *
                          100,
                        100
                      );
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-neutral-500 w-32 truncate flex-shrink-0">
                        {w.label}
                      </span>
                      <div className="flex-1 h-5 bg-neutral-100 rounded overflow-hidden">
                        <div
                          className={`h-full rounded transition-all ${
                            isBase
                              ? "bg-neutral-400"
                              : w.value < 0
                                ? "bg-red-400"
                                : "bg-green-400"
                          }`}
                          style={{ width: `${barPct}%` }}
                        />
                      </div>
                      <span
                        className={`text-xs font-semibold w-20 text-right flex-shrink-0 ${
                          isBase
                            ? "text-neutral-600"
                            : w.value < 0
                              ? "text-red-600"
                              : "text-green-600"
                        }`}
                      >
                        {isBase ? fmt(w.value) : `${w.value > 0 ? "+" : ""}${fmt(w.value)}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Per-holding impact table */}
          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-neutral-700 mb-3">
                Per-Holding Impact
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      {["Asset", "Current Value", "Stressed Value", "Δ Value", "Δ %"].map(
                        (h) => (
                          <th
                            key={h}
                            className="text-left py-2 px-2 text-xs font-semibold text-neutral-500"
                          >
                            {h}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {result.holding_impacts.map((hi) => (
                      <tr
                        key={hi.holding_id}
                        className="border-b border-neutral-100 hover:bg-neutral-50"
                      >
                        <td className="py-2 px-2 font-medium text-neutral-700">
                          {hi.asset_name}
                        </td>
                        <td className="py-2 px-2 text-neutral-600">
                          {fmt(hi.current_value)}
                        </td>
                        <td className="py-2 px-2 text-neutral-600">
                          {fmt(hi.stressed_value)}
                        </td>
                        <td
                          className={`py-2 px-2 font-medium ${hi.delta_value < 0 ? "text-red-600" : "text-green-600"}`}
                        >
                          {hi.delta_value > 0 ? "+" : ""}
                          {fmt(hi.delta_value)}
                        </td>
                        <td
                          className={`py-2 px-2 font-semibold ${hi.delta_pct < 0 ? "text-red-600" : "text-green-600"}`}
                        >
                          {hi.delta_pct > 0 ? "+" : ""}
                          {hi.delta_pct.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// ── Compliance Tab ────────────────────────────────────────────────────────────

function ProgressBar({
  value,
  threshold,
}: {
  value: number;
  threshold?: number;
}) {
  const color =
    threshold && value < threshold
      ? "bg-amber-400"
      : "bg-green-500";
  return (
    <div className="h-3 bg-neutral-100 rounded-full overflow-hidden relative">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(value, 100)}%` }}
      />
      {threshold && (
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-neutral-400"
          style={{ left: `${threshold}%` }}
        />
      )}
    </div>
  );
}

function ComplianceTab({ portfolioId }: { portfolioId: string }) {
  const { data, isLoading } = useComplianceStatus(portfolioId);
  const [expandedHolding, setExpandedHolding] = useState<string | null>(null);

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <NoPortfolio />;

  const sfdrThreshold =
    data.sfdr_classification === "article_9"
      ? 80
      : data.sfdr_classification === "article_8"
        ? 50
        : undefined;

  return (
    <div className="space-y-6">
      {/* SFDR classification */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-1">
          <CardContent className="p-6 flex flex-col items-center justify-center text-center">
            <ShieldCheck className="h-8 w-8 text-neutral-400 mb-3" />
            <p className="text-xs text-neutral-500 mb-2 font-medium uppercase tracking-wide">
              SFDR Classification
            </p>
            <span
              className={`text-lg font-bold px-4 py-2 rounded-full border ${sfdrColor(data.sfdr_classification)}`}
            >
              {sfdrLabel(data.sfdr_classification)}
            </span>
            <p
              className={`text-sm font-semibold mt-3 ${complianceStatusColor(data.overall_status)}`}
            >
              {data.overall_status === "compliant"
                ? "✓ Compliant"
                : data.overall_status === "needs_attention"
                  ? "⚠ Needs Attention"
                  : "✗ Non-Compliant"}
            </p>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardContent className="p-5 space-y-5">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-neutral-700">
                  Sustainable Investment
                </span>
                <span className="font-bold text-neutral-800">
                  {data.sustainable_investment_pct.toFixed(1)}%
                </span>
              </div>
              <ProgressBar value={data.sustainable_investment_pct} threshold={sfdrThreshold} />
              {sfdrThreshold && (
                <p className="text-xs text-neutral-400 mt-1">
                  Target: {sfdrThreshold}% for {sfdrLabel(data.sfdr_classification)}
                </p>
              )}
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-neutral-700">
                  Taxonomy Eligible
                </span>
                <span className="font-bold text-neutral-800">
                  {data.taxonomy_eligible_pct.toFixed(1)}%
                </span>
              </div>
              <ProgressBar value={data.taxonomy_eligible_pct} />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-neutral-700">
                  Taxonomy Aligned
                </span>
                <span className="font-bold text-neutral-800">
                  {data.taxonomy_aligned_pct.toFixed(1)}%
                </span>
              </div>
              <ProgressBar value={data.taxonomy_aligned_pct} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* PAI Indicators */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-neutral-700 mb-3">
            Principal Adverse Impact (PAI) Indicators — 14 Mandatory
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200">
                  {["#", "Indicator", "Category", "Value", "Unit", "Status"].map(
                    (h) => (
                      <th
                        key={h}
                        className="text-left py-2 px-2 text-xs font-semibold text-neutral-500"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {data.pai_indicators.map((pai) => (
                  <tr
                    key={pai.id}
                    className="border-b border-neutral-100 hover:bg-neutral-50"
                  >
                    <td className="py-2 px-2 text-neutral-400 text-xs">
                      {pai.id}
                    </td>
                    <td className="py-2 px-2 font-medium text-neutral-700">
                      {pai.name}
                    </td>
                    <td className="py-2 px-2 text-neutral-500">{pai.category}</td>
                    <td className="py-2 px-2 text-neutral-600">
                      {pai.value ?? "—"}
                    </td>
                    <td className="py-2 px-2 text-neutral-400 text-xs">
                      {pai.unit}
                    </td>
                    <td className={`py-2 px-2 text-xs font-semibold capitalize ${paiStatusColor(pai.status)}`}>
                      {pai.status.replace("_", " ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Taxonomy / DNSH per holding */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-neutral-700 mb-3">
            EU Taxonomy — DNSH Assessment by Holding
          </p>
          <div className="space-y-2">
            {data.taxonomy_results.map((tr) => (
              <div key={tr.holding_id} className="border border-neutral-200 rounded-lg">
                <button
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-neutral-50"
                  onClick={() =>
                    setExpandedHolding(
                      expandedHolding === tr.holding_id ? null : tr.holding_id
                    )
                  }
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={tr.aligned ? "success" : tr.eligible ? "warning" : "neutral"}
                    >
                      {tr.aligned ? "Aligned" : tr.eligible ? "Eligible" : "Not Eligible"}
                    </Badge>
                    <span className="text-sm font-medium text-neutral-700">
                      {tr.asset_name}
                    </span>
                    <span className="text-xs text-neutral-400 hidden sm:block">
                      {tr.economic_activity}
                    </span>
                  </div>
                  {expandedHolding === tr.holding_id ? (
                    <ChevronDown className="h-4 w-4 text-neutral-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-neutral-400" />
                  )}
                </button>
                {expandedHolding === tr.holding_id && (
                  <div className="border-t border-neutral-200 p-3 space-y-1.5">
                    {tr.dnsh_checks.map((c) => (
                      <div key={c.objective} className="flex items-start gap-2 text-xs">
                        <span
                          className={`font-bold flex-shrink-0 ${
                            c.status === "compliant"
                              ? "text-green-600"
                              : c.status === "non_compliant"
                                ? "text-red-600"
                                : "text-amber-600"
                          }`}
                        >
                          {c.status === "compliant" ? "✓" : c.status === "non_compliant" ? "✗" : "?"}
                        </span>
                        <span className="font-semibold text-neutral-600 w-52 flex-shrink-0">
                          {c.objective}
                        </span>
                        <span className="text-neutral-500">{c.notes}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Audit Trail Tab ───────────────────────────────────────────────────────────

function AuditTab() {
  const [entityType, setEntityType] = useState("");
  const [entityIdInput, setEntityIdInput] = useState("");
  const [appliedType, setAppliedType] = useState<string | undefined>();
  const [appliedId, setAppliedId] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useAuditTrail(appliedType, appliedId, page);

  const handleFilter = () => {
    setAppliedType(entityType || undefined);
    setAppliedId(entityIdInput || undefined);
    setPage(1);
  };

  const handleExportCsv = () => {
    if (!data) return;
    const rows = [
      ["Timestamp", "User ID", "Action", "Entity Type", "Entity ID", "IP"],
      ...data.items.map((e) => [
        e.timestamp,
        e.user_id ?? "",
        e.action,
        e.entity_type,
        e.entity_id ?? "",
        e.ip_address ?? "",
      ]),
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audit-trail.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalPages = data ? Math.ceil(data.total / 50) : 1;

  return (
    <div className="space-y-4">
      {/* Filter row */}
      <div className="flex flex-wrap gap-3 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-neutral-500" />
          <span className="text-sm font-medium text-neutral-600">Filter</span>
        </div>
        <select
          className="text-sm border border-neutral-200 rounded px-2 py-1 bg-white"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
        >
          <option value="">All Entity Types</option>
          <option value="portfolio">Portfolio</option>
          <option value="holding">Holding</option>
          <option value="project">Project</option>
          <option value="risk_assessment">Risk Assessment</option>
          <option value="document">Document</option>
        </select>
        <input
          type="text"
          placeholder="Entity UUID…"
          className="text-sm border border-neutral-200 rounded px-2 py-1 w-52 font-mono"
          value={entityIdInput}
          onChange={(e) => setEntityIdInput(e.target.value)}
        />
        <Button size="sm" onClick={handleFilter}>
          <Search className="h-3.5 w-3.5 mr-1" />
          Apply
        </Button>
        <Button size="sm" variant="outline" onClick={handleExportCsv}>
          <Download className="h-3.5 w-3.5 mr-1" />
          Export CSV
        </Button>
      </div>

      {/* Timeline */}
      {isLoading ? (
        <LoadingSpinner />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Search className="h-12 w-12 text-neutral-400" />}
          title="No audit entries"
          description="No audit log entries match your filters."
        />
      ) : (
        <>
          <div className="space-y-1">
            {data.items.map((entry) => (
              <AuditEntryRow
                key={entry.id}
                entry={entry}
                expanded={expandedId === entry.id}
                onToggle={() =>
                  setExpandedId(expandedId === entry.id ? null : entry.id)
                }
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-neutral-500 py-1.5 px-2">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AuditEntryRow({
  entry,
  expanded,
  onToggle,
}: {
  entry: AuditEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const actionColor =
    entry.action.startsWith("create")
      ? "text-green-700 bg-green-50"
      : entry.action.startsWith("delete")
        ? "text-red-700 bg-red-50"
        : "text-blue-700 bg-blue-50";

  return (
    <div className="border border-neutral-200 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-neutral-50 text-sm"
      >
        <span className="text-xs text-neutral-400 font-mono w-36 flex-shrink-0">
          {new Date(entry.timestamp).toLocaleString()}
        </span>
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded capitalize flex-shrink-0 ${actionColor}`}
        >
          {entry.action.replace("_", " ")}
        </span>
        <span className="text-xs text-neutral-500 flex-shrink-0 capitalize">
          {entry.entity_type.replace("_", " ")}
        </span>
        <span className="text-xs text-neutral-400 font-mono truncate flex-1">
          {entry.entity_id ?? "—"}
        </span>
        {entry.user_id && (
          <span className="text-xs text-neutral-400 font-mono hidden sm:block w-32 truncate">
            user: {entry.user_id.slice(0, 8)}…
          </span>
        )}
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-neutral-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
        )}
      </button>
      {expanded && entry.changes && (
        <div className="border-t border-neutral-200 bg-neutral-50 p-3">
          <pre className="text-xs font-mono text-neutral-600 whitespace-pre-wrap">
            {JSON.stringify(entry.changes, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── 5-Domain Risk Tab ─────────────────────────────────────────────────────────

function DomainRadar({ domains }: { domains: FiveDomainRisk["domains"] }) {
  const data = domains.map((d) => ({
    domain: DOMAIN_LABELS[d.domain] ?? d.domain,
    score: d.score ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis
          dataKey="domain"
          tick={{ fontSize: 11, fill: "#6b7280" }}
        />
        <Radar
          name="Risk"
          dataKey="score"
          stroke="#ef4444"
          fill="#ef4444"
          fillOpacity={0.18}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function AlertCard({
  alert,
  onResolve,
}: {
  alert: MonitoringAlert;
  onResolve: (id: string, action: string) => void;
}) {
  const [action, setAction] = useState("");
  const [resolving, setResolving] = useState(false);

  const handleResolve = () => {
    if (!action.trim()) return;
    onResolve(alert.id, action);
    setResolving(false);
  };

  return (
    <div
      className={`border rounded-lg p-4 ${
        alert.is_actioned ? "border-neutral-200 opacity-60" : "border-orange-200 bg-orange-50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={alertSeverityBadge(alert.severity)} className="capitalize">
              {alert.severity}
            </Badge>
            <span className="text-xs text-neutral-500 capitalize">
              {DOMAIN_LABELS[alert.domain] ?? alert.domain}
            </span>
            {alert.source_name && (
              <span className="text-xs text-neutral-400">{alert.source_name}</span>
            )}
          </div>
          <p className="mt-1 text-sm font-semibold text-neutral-800">{alert.title}</p>
          <p className="text-xs text-neutral-500 mt-0.5">{alert.description}</p>
          {alert.is_actioned && alert.action_taken && (
            <p className="text-xs text-green-700 mt-1">
              ✓ Resolved: {alert.action_taken}
            </p>
          )}
        </div>
        {!alert.is_actioned && (
          <button
            onClick={() => setResolving(!resolving)}
            className="text-xs text-primary-600 hover:text-primary-700 flex-shrink-0"
          >
            {resolving ? <X className="h-4 w-4" /> : "Resolve"}
          </button>
        )}
      </div>
      {resolving && (
        <div className="mt-3 flex gap-2">
          <input
            className="flex-1 text-sm border border-neutral-200 rounded px-2 py-1"
            placeholder="Describe action taken…"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
          <Button size="sm" onClick={handleResolve} disabled={!action.trim()}>
            Save
          </Button>
        </div>
      )}
    </div>
  );
}

function MitigationPanel({
  portfolioId,
  domain,
}: {
  portfolioId: string;
  domain: string;
}) {
  const [result, setResult] = useState<MitigationResponse | null>(null);
  const generate = useGenerateMitigation(portfolioId);

  const handleGenerate = async () => {
    const res = await generate.mutateAsync(domain);
    setResult(res);
  };

  return (
    <div className="mt-3 border-t pt-3">
      {!result ? (
        <Button
          size="sm"
          variant="outline"
          onClick={handleGenerate}
          disabled={generate.isPending}
        >
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          {generate.isPending ? "Generating…" : "AI Mitigation Strategies"}
        </Button>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-primary-500" />
            <p className="text-xs font-medium text-neutral-700">
              AI Mitigation ({result.model_used})
            </p>
            <button
              onClick={() => setResult(null)}
              className="ml-auto text-neutral-400 hover:text-neutral-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="flex items-start gap-1.5">
            <p className="text-xs text-neutral-600 flex-1">{result.mitigation_text}</p>
            {/* Add aiTaskLogId from AI task log when available */}
            <CitationBadges aiTaskLogId={undefined} className="flex-shrink-0" />
          </div>
          {result.key_actions.length > 0 && (
            <ul className="space-y-1">
              {result.key_actions.map((a, i) => (
                <li key={i} className="text-xs text-neutral-600 flex items-start gap-1">
                  <span className="text-primary-500 font-bold flex-shrink-0">{i + 1}.</span>
                  {a}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function DomainsTab({ portfolioId }: { portfolioId: string }) {
  const { data, isLoading } = useDomainScores(portfolioId);
  const { data: alerts } = useMonitoringAlerts(portfolioId);
  const resolveAlert = useResolveAlert();
  const triggerCheck = useTriggerMonitoringCheck(portfolioId);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [showResolved, setShowResolved] = useState(false);

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <NoPortfolio />;

  const openAlerts = alerts?.items.filter((a) => !a.is_actioned) ?? [];
  const resolvedAlerts = alerts?.items.filter((a) => a.is_actioned) ?? [];
  const displayedAlerts = showResolved ? alerts?.items ?? [] : openAlerts;

  const handleResolve = (alertId: string, actionTaken: string) => {
    resolveAlert.mutate({ alertId, actionTaken });
  };

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-neutral-500">
            {data.source === "stored" ? "Stored domain scores" : "Computed from assessments"} ·{" "}
            {data.active_alerts_count} active alert{data.active_alerts_count !== 1 ? "s" : ""}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => triggerCheck.mutate()}
          disabled={triggerCheck.isPending}
        >
          <Bell className={`mr-1.5 h-3.5 w-3.5 ${triggerCheck.isPending ? "animate-pulse" : ""}`} />
          {triggerCheck.isPending ? "Checking…" : "Run Check"}
        </Button>
      </div>

      {/* Overall score + radar */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="md:col-span-2">
          <CardContent className="p-5 flex flex-col items-center justify-center">
            <ScoreGauge
              score={data.overall_risk_score ?? 0}
              size={110}
              strokeWidth={10}
            />
            <p className="text-xs text-neutral-400 mt-2">Overall Risk Score</p>
            <p className="text-xs text-neutral-400">(higher = more risk)</p>
          </CardContent>
        </Card>
        <Card className="md:col-span-3">
          <CardContent className="p-4">
            <p className="text-xs font-medium text-neutral-500 mb-2">
              Domain Risk Radar
            </p>
            <DomainRadar domains={data.domains} />
          </CardContent>
        </Card>
      </div>

      {/* Domain cards */}
      <div className="space-y-3">
        {data.domains.map((d) => (
          <Card key={d.domain}>
            <button
              onClick={() =>
                setExpandedDomain(expandedDomain === d.domain ? null : d.domain)
              }
              className="w-full flex items-center justify-between p-4 text-left hover:bg-neutral-50"
            >
              <div className="flex items-center gap-4">
                <div
                  className="h-3 w-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: DOMAIN_COLORS[d.domain] ?? "#6b7280" }}
                />
                <div>
                  <p className="font-semibold text-neutral-800">
                    {DOMAIN_LABELS[d.domain] ?? d.domain}
                  </p>
                  <p className={`text-xs font-medium ${domainRiskColor(d.score)}`}>
                    {domainRiskLabel(d.score)}
                    {d.score !== null && ` · ${d.score.toFixed(0)}/100`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {d.score !== null && (
                  <div className="w-24 h-2 bg-neutral-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${d.score}%`,
                        backgroundColor: DOMAIN_COLORS[d.domain] ?? "#6b7280",
                      }}
                    />
                  </div>
                )}
                {expandedDomain === d.domain ? (
                  <ChevronDown className="h-4 w-4 text-neutral-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-neutral-400" />
                )}
              </div>
            </button>
            {expandedDomain === d.domain && (
              <div className="border-t px-4 pb-4">
                {d.details && Object.keys(d.details).length > 0 && (
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {Object.entries(d.details).map(([k, v]) => (
                      <div key={k} className="text-xs">
                        <span className="text-neutral-500 capitalize">
                          {k.replace(/_/g, " ")}:{" "}
                        </span>
                        <span className="font-medium text-neutral-700">
                          {typeof v === "number" ? v.toFixed(1) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <MitigationPanel portfolioId={portfolioId} domain={d.domain} />
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* Alerts section */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-neutral-700">
              Monitoring Alerts
              {openAlerts.length > 0 && (
                <span className="ml-2 bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">
                  {openAlerts.length}
                </span>
              )}
            </p>
            <button
              onClick={() => setShowResolved(!showResolved)}
              className="text-xs text-neutral-500 flex items-center gap-1 hover:text-neutral-700"
            >
              {showResolved ? (
                <BellOff className="h-3.5 w-3.5" />
              ) : (
                <Bell className="h-3.5 w-3.5" />
              )}
              {showResolved ? "Hide resolved" : `Show resolved (${resolvedAlerts.length})`}
            </button>
          </div>

          {displayedAlerts.length === 0 ? (
            <EmptyState
              icon={<ShieldCheck className="h-10 w-10 text-neutral-400" />}
              title="No active alerts"
              description="All monitoring checks are clear. Run a check to refresh."
            />
          ) : (
            <div className="space-y-3">
              {displayedAlerts.map((alert) => (
                <AlertCard key={alert.id} alert={alert} onResolve={handleResolve} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Shared components ─────────────────────────────────────────────────────────

function LoadingSpinner() {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
    </div>
  );
}

function NoPortfolio() {
  return (
    <EmptyState
      icon={<AlertTriangle className="h-12 w-12 text-neutral-400" />}
      title="Select a portfolio"
      description="Choose a portfolio from the dropdown above to view risk data."
    />
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RiskPage() {
  const [portfolioId, setPortfolioId] = useState("");

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Risk Analysis & Compliance
          </h1>
          <p className="text-neutral-500 mt-1">
            Portfolio risk monitoring, stress testing, and SFDR compliance
          </p>
        </div>
        <PortfolioSelector value={portfolioId} onChange={setPortfolioId} />
      </div>

      <Tabs defaultValue="dashboard">
        <TabsList>
          <TabsTrigger value="dashboard">Risk Dashboard</TabsTrigger>
          <TabsTrigger value="domains">5-Domain Risk</TabsTrigger>
          <TabsTrigger value="scenarios">Scenario Analysis</TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="mt-6">
          {portfolioId ? (
            <DashboardTab portfolioId={portfolioId} />
          ) : (
            <NoPortfolio />
          )}
        </TabsContent>

        <TabsContent value="domains" className="mt-6">
          {portfolioId ? (
            <DomainsTab portfolioId={portfolioId} />
          ) : (
            <NoPortfolio />
          )}
        </TabsContent>

        <TabsContent value="scenarios" className="mt-6">
          {portfolioId ? (
            <ScenarioTab portfolioId={portfolioId} />
          ) : (
            <NoPortfolio />
          )}
        </TabsContent>

        <TabsContent value="compliance" className="mt-6">
          {portfolioId ? (
            <ComplianceTab portfolioId={portfolioId} />
          ) : (
            <NoPortfolio />
          )}
        </TabsContent>

        <TabsContent value="audit" className="mt-6">
          <AuditTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
