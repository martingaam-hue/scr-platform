"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Info,
  ArrowRight,
  Sparkles,
  DollarSign,
  Landmark,
  Shield,
  Users,
  Globe,
  Leaf,
  BarChart3,
  RefreshCw,
  FileText,
  Target,
  Download,
  Zap,
} from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  cn,
} from "@scr/ui";
import { AIFeedback } from "@/components/ai-feedback";

// ── Mock data ────────────────────────────────────────────────────────────────

const HERO_STATS = {
  avg_score: 75,
  projects_evaluated: 10,
  investment_ready: 4,
  portfolio_avg: 78,
  pipeline_avg: 66,
};

type ProjectEntry = {
  id: string;
  name: string;
  sector: string;
  geo: string;
  stage: string;
  score: number;
  group: "portfolio" | "pipeline";
  mandate_fit: number;
  status: "performing" | "watch_list" | "screening" | "passed";
  evaluated_at: string;
  trend: "up" | "down" | "flat";
  dims: {
    financial_robustness: number;
    investment_structure: number;
    risk_adjusted_returns: number;
    team_execution: number;
    market_position: number;
    esg_impact: number;
  };
  indicators: { text: string; met: boolean }[];
  dd_gaps: { gap: string; dimension: string; priority: "High" | "Medium" | "Low"; score_impact: number }[];
  history: { date: string; score: number; note: string }[];
};

const PROJECTS: ProjectEntry[] = [
  {
    id: "h1",
    name: "Helios Solar Portfolio Iberia",
    sector: "Solar",
    geo: "Spain",
    stage: "Operational",
    score: 87,
    group: "portfolio",
    mandate_fit: 94,
    status: "performing",
    evaluated_at: "Mar 10, 2026",
    trend: "up",
    dims: {
      financial_robustness: 92,
      investment_structure: 85,
      risk_adjusted_returns: 88,
      team_execution: 81,
      market_position: 90,
      esg_impact: 86,
    },
    indicators: [
      { text: "Strong risk-adjusted return profile with 16.1% projected net IRR", met: true },
      { text: "Clean cap table with standard investor protections and tag-along rights", met: true },
      { text: "Experienced developer with 450MW+ of operational solar assets in Iberia", met: true },
      { text: "Full EU Taxonomy alignment with verified 89K tCO₂e annual avoidance", met: true },
    ],
    dd_gaps: [
      { gap: "Independent technical report for year 3+ performance", dimension: "Financial Robustness", priority: "Medium", score_impact: 2 },
      { gap: "Offtaker credit rating documentation", dimension: "Risk-Adjusted Returns", priority: "Low", score_impact: 1 },
    ],
    history: [
      { date: "Dec 2025", score: 79, note: "Initial screening" },
      { date: "Jan 2026", score: 83, note: "DD phase 1 complete" },
      { date: "Feb 2026", score: 85, note: "Financial model updated" },
      { date: "Mar 2026", score: 87, note: "Full IC review" },
    ],
  },
  {
    id: "h2",
    name: "Nordvik Wind Farm II",
    sector: "Wind",
    geo: "Norway",
    stage: "Construction",
    score: 74,
    group: "portfolio",
    mandate_fit: 88,
    status: "performing",
    evaluated_at: "Mar 8, 2026",
    trend: "flat",
    dims: {
      financial_robustness: 71,
      investment_structure: 78,
      risk_adjusted_returns: 72,
      team_execution: 80,
      market_position: 74,
      esg_impact: 68,
    },
    indicators: [
      { text: "Strong team track record — 3 completed onshore wind projects", met: true },
      { text: "Favorable Norwegian regulatory environment with grid connection secured", met: true },
      { text: "Base case IRR 11.8% below fund target of 13%", met: false },
      { text: "ESG impact measurement framework partially completed", met: false },
    ],
    dd_gaps: [
      { gap: "P90 energy yield assessment from independent wind resource expert", dimension: "Financial Robustness", priority: "High", score_impact: 4 },
      { gap: "Construction contractor performance bond details", dimension: "Risk-Adjusted Returns", priority: "High", score_impact: 3 },
      { gap: "Carbon impact quantification methodology", dimension: "ESG & Impact", priority: "Medium", score_impact: 2 },
    ],
    history: [
      { date: "Nov 2025", score: 68, note: "Initial screening" },
      { date: "Jan 2026", score: 72, note: "Site visit completed" },
      { date: "Mar 2026", score: 74, note: "Grid connection confirmed" },
    ],
  },
  {
    id: "h3",
    name: "Adriatic Infrastructure Holdings",
    sector: "Infrastructure",
    geo: "Italy",
    stage: "Operational",
    score: 82,
    group: "portfolio",
    mandate_fit: 79,
    status: "performing",
    evaluated_at: "Feb 28, 2026",
    trend: "up",
    dims: { financial_robustness: 84, investment_structure: 81, risk_adjusted_returns: 80, team_execution: 86, market_position: 79, esg_impact: 82 },
    indicators: [
      { text: "Proven management team with €2B+ infrastructure delivery record", met: true },
      { text: "Government concession secured — 25-year revenue visibility", met: true },
      { text: "Valuation at market comparables with reasonable terminal assumptions", met: true },
      { text: "Minor governance gap — independent director seat pending appointment", met: false },
    ],
    dd_gaps: [
      { gap: "Independent board director appointment confirmation", dimension: "Investment Structure", priority: "Medium", score_impact: 2 },
    ],
    history: [
      { date: "Jan 2026", score: 79, note: "First evaluation" },
      { date: "Feb 2026", score: 82, note: "Governance review" },
    ],
  },
  {
    id: "h4",
    name: "Baltic BESS Grid Storage",
    sector: "BESS",
    geo: "Lithuania",
    stage: "Development",
    score: 65,
    group: "portfolio",
    mandate_fit: 72,
    status: "watch_list",
    evaluated_at: "Mar 5, 2026",
    trend: "down",
    dims: { financial_robustness: 60, investment_structure: 67, risk_adjusted_returns: 58, team_execution: 72, market_position: 70, esg_impact: 64 },
    indicators: [
      { text: "Grid connection permit delayed — regulatory timeline uncertain", met: false },
      { text: "Revenue contract (CfD) not yet executed with national grid operator", met: false },
      { text: "Technology supplier has strong BESS installation track record", met: true },
      { text: "ESG credentials documented but carbon quantification pending", met: false },
    ],
    dd_gaps: [
      { gap: "Regulatory permit for grid connection", dimension: "Risk-Adjusted Returns", priority: "High", score_impact: 6 },
      { gap: "Executed capacity revenue contract (CfD)", dimension: "Financial Robustness", priority: "High", score_impact: 5 },
      { gap: "Independent battery technology assessment", dimension: "Market & Position", priority: "Medium", score_impact: 3 },
    ],
    history: [
      { date: "Dec 2025", score: 70, note: "IC approved" },
      { date: "Feb 2026", score: 67, note: "Permit delay flagged" },
      { date: "Mar 2026", score: 65, note: "Watch list trigger" },
    ],
  },
  {
    id: "h5",
    name: "Alpine Hydro Partners",
    sector: "Hydro",
    geo: "Switzerland",
    stage: "Operational",
    score: 91,
    group: "portfolio",
    mandate_fit: 96,
    status: "performing",
    evaluated_at: "Mar 1, 2026",
    trend: "up",
    dims: { financial_robustness: 94, investment_structure: 90, risk_adjusted_returns: 93, team_execution: 89, market_position: 88, esg_impact: 92 },
    indicators: [
      { text: "Top-quartile IRR of 17.6% with robust downside protection", met: true },
      { text: "60-year operational track record — zero capital impairment events", met: true },
      { text: "Strong governance structure with independent oversight board", met: true },
      { text: "Certified carbon-neutral operations — EU Taxonomy Article 9 compliant", met: true },
    ],
    dd_gaps: [],
    history: [
      { date: "Oct 2025", score: 86, note: "Initial scoring" },
      { date: "Dec 2025", score: 89, note: "Updated financials" },
      { date: "Mar 2026", score: 91, note: "Full IC package" },
    ],
  },
  {
    id: "h6",
    name: "Nordic Biomass Energy",
    sector: "Biomass",
    geo: "Sweden",
    stage: "Operational",
    score: 71,
    group: "portfolio",
    mandate_fit: 81,
    status: "performing",
    evaluated_at: "Feb 20, 2026",
    trend: "flat",
    dims: { financial_robustness: 73, investment_structure: 70, risk_adjusted_returns: 68, team_execution: 74, market_position: 72, esg_impact: 70 },
    indicators: [
      { text: "Biomass feedstock supply contracts in place for 5 years", met: true },
      { text: "IRR at 10.5% — within but at lower end of mandate target range", met: true },
      { text: "Emissions controversy risk — sustainability certification pending renewal", met: false },
      { text: "Limited co-investor base — no institutional co-investors confirmed", met: false },
    ],
    dd_gaps: [
      { gap: "Sustainability certification renewal documentation", dimension: "ESG & Impact", priority: "High", score_impact: 5 },
      { gap: "Additional co-investor term sheet", dimension: "Investment Structure", priority: "Medium", score_impact: 2 },
    ],
    history: [
      { date: "Nov 2025", score: 69, note: "Initial" },
      { date: "Feb 2026", score: 71, note: "Cert renewal started" },
    ],
  },
  {
    id: "h7",
    name: "Thames Clean Energy Hub",
    sector: "Wind",
    geo: "UK",
    stage: "Construction",
    score: 78,
    group: "portfolio",
    mandate_fit: 85,
    status: "performing",
    evaluated_at: "Mar 3, 2026",
    trend: "up",
    dims: { financial_robustness: 76, investment_structure: 80, risk_adjusted_returns: 78, team_execution: 82, market_position: 77, esg_impact: 75 },
    indicators: [
      { text: "CfD contract secured — fixed revenue for 15 years post-completion", met: true },
      { text: "Construction on schedule — milestone 2 completed Feb 2026", met: true },
      { text: "FX exposure (GBP/USD) partially unhedged — 15% variance risk", met: false },
      { text: "Community benefit fund established — positive local stakeholder relations", met: true },
    ],
    dd_gaps: [
      { gap: "FX hedging strategy documentation", dimension: "Risk-Adjusted Returns", priority: "High", score_impact: 3 },
      { gap: "Construction insurance certificate (remaining phases)", dimension: "Investment Structure", priority: "Medium", score_impact: 2 },
    ],
    history: [
      { date: "Dec 2025", score: 74, note: "Pre-construction" },
      { date: "Feb 2026", score: 76, note: "Milestone 1" },
      { date: "Mar 2026", score: 78, note: "Milestone 2" },
    ],
  },
  {
    id: "p1",
    name: "Sahara CSP Development",
    sector: "Solar",
    geo: "Morocco",
    stage: "Development",
    score: 58,
    group: "pipeline",
    mandate_fit: 67,
    status: "passed",
    evaluated_at: "Mar 12, 2026",
    trend: "flat",
    dims: { financial_robustness: 52, investment_structure: 60, risk_adjusted_returns: 55, team_execution: 62, market_position: 65, esg_impact: 58 },
    indicators: [
      { text: "Novel technology (CSP) — limited bankability track record in region", met: false },
      { text: "Off-take agreement in early negotiation only — not yet signed", met: false },
      { text: "Experienced developer with 2 prior solar projects in MENA", met: true },
      { text: "Strong ESG and SDG impact case for energy access in Morocco", met: true },
    ],
    dd_gaps: [
      { gap: "Signed PPA or off-take term sheet", dimension: "Financial Robustness", priority: "High", score_impact: 8 },
      { gap: "Independent technology feasibility study for CSP design", dimension: "Market & Position", priority: "High", score_impact: 6 },
      { gap: "Political risk insurance confirmation", dimension: "Risk-Adjusted Returns", priority: "High", score_impact: 5 },
    ],
    history: [
      { date: "Mar 2026", score: 58, note: "First screening" },
    ],
  },
  {
    id: "p2",
    name: "Danube Hydro Expansion",
    sector: "Hydro",
    geo: "Romania",
    stage: "Development",
    score: 72,
    group: "pipeline",
    mandate_fit: 83,
    status: "screening",
    evaluated_at: "Mar 7, 2026",
    trend: "up",
    dims: { financial_robustness: 74, investment_structure: 70, risk_adjusted_returns: 73, team_execution: 76, market_position: 71, esg_impact: 68 },
    indicators: [
      { text: "Strong hydro resource data with 30-year flow records", met: true },
      { text: "Environmental permits secured — construction-ready", met: true },
      { text: "Romanian energy market regulations evolving — some policy risk", met: false },
      { text: "ESG certification in progress — expected completion Q3 2026", met: false },
    ],
    dd_gaps: [
      { gap: "Regulatory update analysis for Romanian electricity market reforms", dimension: "Market & Position", priority: "Medium", score_impact: 3 },
      { gap: "ESG certification completion", dimension: "ESG & Impact", priority: "Medium", score_impact: 3 },
    ],
    history: [
      { date: "Feb 2026", score: 68, note: "Initial contact" },
      { date: "Mar 2026", score: 72, note: "Screening score" },
    ],
  },
  {
    id: "p3",
    name: "Aegean Wind Cluster",
    sector: "Wind",
    geo: "Greece",
    stage: "Development",
    score: 69,
    group: "pipeline",
    mandate_fit: 91,
    status: "screening",
    evaluated_at: "Mar 9, 2026",
    trend: "up",
    dims: { financial_robustness: 65, investment_structure: 72, risk_adjusted_returns: 67, team_execution: 70, market_position: 74, esg_impact: 66 },
    indicators: [
      { text: "Excellent wind resource — P50 capacity factor >35%", met: true },
      { text: "Strong mandate fit — EU taxonomy aligned offshore wind cluster", met: true },
      { text: "Greek grid connection process has historical delays", met: false },
      { text: "Financial model requires update — based on 2024 CAPEX estimates", met: false },
    ],
    dd_gaps: [
      { gap: "Updated CAPEX model with 2026 equipment pricing", dimension: "Financial Robustness", priority: "High", score_impact: 5 },
      { gap: "Grid connection timeline confirmation from ADMIE", dimension: "Risk-Adjusted Returns", priority: "High", score_impact: 4 },
    ],
    history: [
      { date: "Feb 2026", score: 63, note: "Sourcing" },
      { date: "Mar 2026", score: 69, note: "Screening" },
    ],
  },
];

const PORTFOLIO_FIT = {
  sector_diversification: [
    { sector: "Solar",  before: 28, after: 28 },
    { sector: "Wind",   before: 34, after: 34 },
    { sector: "Hydro",  before: 19, after: 19 },
    { sector: "Infra",  before: 10, after: 10 },
    { sector: "BESS",   before: 6, after: 6 },
    { sector: "Other",  before: 3, after: 3 },
  ],
  geo_diversification: [
    { geo: "Norway",      pct: 14 },
    { geo: "Spain",       pct: 19 },
    { geo: "Switzerland", pct: 22 },
    { geo: "Italy",       pct: 16 },
    { geo: "UK",          pct: 17 },
    { geo: "Lithuania",   pct: 8 },
    { geo: "Sweden",      pct: 4 },
  ],
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function scoreColor(s: number) {
  if (s >= 80) return "text-green-600";
  if (s >= 70) return "text-blue-600";
  if (s >= 60) return "text-amber-600";
  if (s >= 50) return "text-yellow-600";
  return "text-red-600";
}

function scoreBarColor(s: number) {
  if (s >= 80) return "bg-green-500";
  if (s >= 70) return "bg-blue-500";
  if (s >= 60) return "bg-amber-500";
  if (s >= 50) return "bg-yellow-400";
  return "bg-red-400";
}

function scoreBadgeLabel(s: number) {
  if (s >= 90) return { label: "Excellent", variant: "success" as const };
  if (s >= 80) return { label: "Strong",    variant: "success" as const };
  if (s >= 70) return { label: "Good",      variant: "info"    as const };
  if (s >= 60) return { label: "Fair",      variant: "warning" as const };
  return             { label: "Review",     variant: "error"   as const };
}

function ringPath(score: number, r: number) {
  const circ = 2 * Math.PI * r;
  return { circ, offset: circ - (score / 100) * circ };
}

function ringColor(s: number) {
  if (s >= 80) return "#22c55e";
  if (s >= 70) return "#3b82f6";
  if (s >= 60) return "#f59e0b";
  if (s >= 50) return "#eab308";
  return "#ef4444";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function InfoBanner() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-800">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary-500" />
      <span>
        <strong>Investment Signal Score</strong> evaluates projects from an investor perspective — analyzing
        investment readiness, financial robustness, risk-adjusted return potential, team credibility,
        market positioning, and ESG compliance. Use it to screen new opportunities, benchmark portfolio
        holdings, and identify where to focus due diligence.
      </span>
    </div>
  );
}

function ScoreRing({ score, size = 140 }: { score: number; size?: number }) {
  const r = (size - 16) / 2;
  const { circ, offset } = ringPath(score, r);
  const cx = size / 2;
  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e5e7eb" strokeWidth={10} />
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke={ringColor(score)}
          strokeWidth={10}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-4xl font-bold tabular-nums leading-none", scoreColor(score))}>
          {Math.ceil(score)}
        </span>
        <span className="text-xs text-neutral-400">/100</span>
      </div>
    </div>
  );
}

const DIMS = [
  { key: "financial_robustness",    label: "Financial Robustness",      weight: 20, icon: DollarSign, sub: ["Revenue model clarity and defensibility", "Quality of financial projections and assumptions", "Unit economics and margins", "Capital efficiency metrics", "Working capital management", "Debt service coverage ratio"] },
  { key: "investment_structure",    label: "Investment Structure",       weight: 20, icon: Landmark,   sub: ["Valuation methodology and reasonableness", "Deal terms (liquidation preferences, anti-dilution)", "Cap table analysis", "Board composition and governance", "Exit pathway clarity", "Co-investor and syndicate quality"] },
  { key: "risk_adjusted_returns",   label: "Risk-Adjusted Returns",      weight: 15, icon: Shield,     sub: ["Base case IRR vs target", "Downside case IRR", "Key risk factors and mitigants", "Sensitivity analysis quality", "Insurance and hedging provisions", "Comparable transaction benchmarks"] },
  { key: "team_execution",          label: "Team & Execution",           weight: 15, icon: Users,      sub: ["CEO/founder track record", "Team completeness (key roles filled)", "Advisory board relevance", "Key person risk assessment", "Operational execution evidence", "Reference quality"] },
  { key: "market_position",         label: "Market & Competitive Position", weight: 15, icon: Globe,   sub: ["Total addressable market sizing", "Competitive landscape analysis", "Regulatory environment assessment", "Technology risk evaluation", "Customer/offtaker creditworthiness", "Contract duration and terms"] },
  { key: "esg_impact",              label: "ESG & Impact Alignment",     weight: 15, icon: Leaf,       sub: ["EU Taxonomy alignment percentage", "SDG mapping and measurement", "Carbon impact quantification", "Governance standards compliance", "Social impact assessment", "LP mandate compatibility"] },
];

function DimensionCard({ dimKey, score }: { dimKey: string; score: number }) {
  const [expanded, setExpanded] = useState(false);
  const dim = DIMS.find((d) => d.key === dimKey)!;
  const Icon = dim.icon;
  const iconBg = score >= 80 ? "bg-green-100 text-green-600" : score >= 60 ? "bg-amber-100 text-amber-600" : "bg-red-100 text-red-600";
  const cardBorder = score >= 80 ? "border-green-200" : score >= 60 ? "border-neutral-200" : "border-amber-200";
  const cardBg = score >= 80 ? "bg-green-50/30" : "bg-white";

  return (
    <Card className={cn("border", cardBorder, cardBg, "transition-all duration-200")}>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <div className={cn("p-1.5 rounded-lg", iconBg)}>
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-800">{dim.label}</p>
              <p className="text-xs text-neutral-400">{dim.weight}% weight</p>
            </div>
          </div>
          <span className={cn("text-2xl font-bold", scoreColor(score))}>{Math.ceil(score)}</span>
        </div>

        <div className="h-1.5 rounded-full bg-neutral-100 mb-3">
          <div
            className={cn("h-1.5 rounded-full transition-all duration-500", scoreBarColor(score))}
            style={{ width: `${score}%` }}
          />
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs font-medium text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {expanded ? "Hide details" : "Show sub-criteria"}
        </button>

        {expanded && (
          <ul className="mt-3 space-y-1.5 border-t border-neutral-100 pt-3">
            {dim.sub.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-neutral-500">
                <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-neutral-300" />
                {s}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function ScoreChangeBadge({ prev, curr }: { prev: number; curr: number }) {
  const diff = curr - prev;
  if (diff > 0) return (
    <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-sm font-semibold text-green-700">
      <TrendingUp className="h-3.5 w-3.5" />+{diff}
    </span>
  );
  if (diff < 0) return (
    <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-sm font-semibold text-red-700">
      <TrendingDown className="h-3.5 w-3.5" />{diff}
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-sm text-neutral-500">
      <Minus className="h-3.5 w-3.5" /> No change
    </span>
  );
}

type TabKey = "details" | "gaps" | "comparison" | "history";

function ProjectScoreDetail({ project }: { project: ProjectEntry }) {
  const [tab, setTab] = useState<TabKey>("details");
  const prev = project.history[project.history.length - 2]?.score ?? project.score;
  const { label: badgeLabel, variant: badgeVariant } = scoreBadgeLabel(project.score);

  const PORTFOLIO_AVGS = {
    financial_robustness: 78, investment_structure: 79, risk_adjusted_returns: 76,
    team_execution: 80, market_position: 78, esg_impact: 77,
  };

  const historyMax = Math.max(...project.history.map((h) => h.score));
  const historyMin = Math.min(...project.history.map((h) => h.score));
  const historyRange = historyMax - historyMin || 10;

  return (
    <div className="space-y-4">

      {/* Score Hero Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center gap-6">
            <ScoreRing score={project.score} size={148} />
            <div className="flex-1 text-center md:text-left">
              <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400 mb-1">
                Investment Readiness Score
              </p>
              <p className="text-lg font-semibold text-neutral-800">{project.name}</p>
              <p className="text-sm text-neutral-400">{project.sector} · {project.geo} · {project.stage}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2 justify-center md:justify-start">
                <Badge variant={badgeVariant}>{badgeLabel}</Badge>
                <ScoreChangeBadge prev={prev} curr={project.score} />
                <span className="text-xs text-neutral-400">Previous: {prev}</span>
              </div>
              <p className="text-xs text-neutral-400 mt-2">Latest evaluation: {project.evaluated_at}</p>
            </div>
            {/* Dimension mini bars */}
            <div className="hidden lg:block flex-shrink-0 w-52">
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">Dimensions</p>
              <div className="space-y-2">
                {DIMS.map((d) => {
                  const s = project.dims[d.key as keyof typeof project.dims];
                  return (
                    <div key={d.key} className="flex items-center gap-2">
                      <span className="text-xs text-neutral-400 w-24 truncate">{d.label.split(" ")[0]}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-neutral-100">
                        <div className={cn("h-1.5 rounded-full", scoreBarColor(s))} style={{ width: `${s}%` }} />
                      </div>
                      <span className="text-xs text-neutral-500 w-6 text-right">{s}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Investment Indicators */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-indigo-500" />
            Key Investment Indicators
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {project.indicators.map((ind, i) => (
            <div key={i} className="flex items-start gap-3">
              {ind.met
                ? <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                : <XCircle className="h-4 w-4 text-neutral-300 mt-0.5 shrink-0" />
              }
              <p className={cn("text-sm", ind.met ? "text-neutral-800" : "text-neutral-400")}>
                {ind.text}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Generate Memo button */}
      <button
        className="w-full rounded-xl bg-gradient-to-r from-[#1B2A4A] to-[#243660] py-3.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
        onClick={() => {}}
      >
        <FileText className="h-4 w-4" />
        Generate Investment Memo
      </button>

      {/* Tabs */}
      <Card>
        <CardContent className="p-0">
          <div className="flex border-b border-neutral-100">
            {([
              { key: "details",    label: "Details" },
              { key: "gaps",       label: `DD Gaps${project.dd_gaps.length > 0 ? ` (${project.dd_gaps.length})` : ""}` },
              { key: "comparison", label: "Comparison" },
              { key: "history",    label: "History" },
            ] as { key: TabKey; label: string }[]).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={cn(
                  "px-5 py-3 text-sm font-medium transition-colors",
                  tab === key
                    ? "border-b-2 border-[#1B2A4A] text-[#1B2A4A]"
                    : "text-neutral-500 hover:text-neutral-700"
                )}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="p-5">
            {/* Details tab */}
            {tab === "details" && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {DIMS.map((d) => (
                  <DimensionCard
                    key={d.key}
                    dimKey={d.key}
                    score={project.dims[d.key as keyof typeof project.dims]}
                  />
                ))}
              </div>
            )}

            {/* DD Gaps tab */}
            {tab === "gaps" && (
              <div>
                {project.dd_gaps.length === 0 ? (
                  <div className="flex flex-col items-center py-10 text-center">
                    <CheckCircle2 className="h-10 w-10 text-green-400 mb-3" />
                    <p className="font-semibold text-neutral-700">No critical gaps identified</p>
                    <p className="text-xs text-neutral-400 mt-1">This project has provided sufficient information for a complete evaluation.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {project.dd_gaps.map((g, i) => (
                      <div
                        key={i}
                        className={cn(
                          "flex items-start justify-between gap-4 rounded-xl border p-4",
                          g.priority === "High" ? "border-red-200 bg-red-50" : g.priority === "Medium" ? "border-amber-200 bg-amber-50" : "border-neutral-200 bg-neutral-50"
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <AlertCircle className={cn("h-4 w-4 mt-0.5 shrink-0", g.priority === "High" ? "text-red-500" : g.priority === "Medium" ? "text-amber-500" : "text-neutral-400")} />
                          <div>
                            <p className="text-sm font-medium text-neutral-800">{g.gap}</p>
                            <p className="text-xs text-neutral-500 mt-0.5">{g.dimension} · estimated +{g.score_impact} pts if resolved</p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2 shrink-0">
                          <Badge variant={g.priority === "High" ? "error" : g.priority === "Medium" ? "warning" : "neutral"}>{g.priority}</Badge>
                          <button className="text-xs font-medium text-primary-600 hover:underline whitespace-nowrap">
                            Request Info <ArrowRight className="inline h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                    <div className="mt-2 flex justify-end">
                      <Button size="sm" variant="outline">
                        <Download className="mr-1.5 h-3.5 w-3.5" />
                        Export DD Checklist
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Comparison tab */}
            {tab === "comparison" && (
              <div className="space-y-4">
                <p className="text-xs text-neutral-500">Comparing {project.name} against portfolio averages and sector benchmarks.</p>
                {DIMS.map((d) => {
                  const projectScore = project.dims[d.key as keyof typeof project.dims];
                  const portfolioAvg = PORTFOLIO_AVGS[d.key as keyof typeof PORTFOLIO_AVGS];
                  return (
                    <div key={d.key}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-neutral-700">{d.label}</span>
                        <div className="flex items-center gap-4 text-xs">
                          <span className={cn("font-bold", scoreColor(projectScore))}>This: {projectScore}</span>
                          <span className="text-neutral-400">Avg: {portfolioAvg}</span>
                        </div>
                      </div>
                      <div className="relative h-3 rounded-full bg-neutral-100">
                        <div
                          className="h-3 rounded-full bg-neutral-300 opacity-60"
                          style={{ width: `${portfolioAvg}%` }}
                        />
                        <div
                          className={cn("absolute top-0 h-3 rounded-full", scoreBarColor(projectScore))}
                          style={{ width: `${projectScore}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
                <div className="flex items-center gap-4 text-xs text-neutral-400 pt-2">
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-6 rounded-full bg-blue-400" /> This project</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-6 rounded-full bg-neutral-300" /> Portfolio avg</span>
                </div>
              </div>
            )}

            {/* History tab */}
            {tab === "history" && (
              <div>
                <div className="flex items-end gap-2 h-20 mb-3">
                  {project.history.map((h, i) => {
                    const ht = Math.max(8, Math.round(((h.score - historyMin) / historyRange) * 56 + 16));
                    const prev2 = project.history[i - 1]?.score;
                    return (
                      <div key={i} className="flex flex-col items-center gap-1 flex-1">
                        <div
                          className={cn("w-full rounded-t-sm transition-all", scoreBarColor(h.score))}
                          style={{ height: `${ht}px` }}
                          title={`${h.score} — ${h.date}`}
                        />
                        {prev2 !== undefined && (
                          <span className={cn("text-[9px] font-semibold", h.score > prev2 ? "text-green-500" : h.score < prev2 ? "text-red-500" : "text-neutral-400")}>
                            {h.score > prev2 ? `+${h.score - prev2}` : h.score < prev2 ? `${h.score - prev2}` : "—"}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="space-y-2">
                  {[...project.history].reverse().map((h, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-neutral-400 w-20 text-xs">{h.date}</span>
                        <span className={cn("font-bold text-base", scoreColor(h.score))}>{h.score}</span>
                      </div>
                      <span className="text-xs text-neutral-400">{h.note}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Portfolio Fit */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="h-4 w-4 text-indigo-500" />
            Portfolio Fit Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="mb-3 text-xs font-semibold text-neutral-500 uppercase tracking-wide">Sector Exposure</p>
              <div className="space-y-2">
                {PORTFOLIO_FIT.sector_diversification.map((s) => (
                  <div key={s.sector} className="flex items-center gap-2 text-xs">
                    <span className="w-12 text-neutral-500">{s.sector}</span>
                    <div className="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                      <div className="h-2 rounded-full bg-indigo-400" style={{ width: `${s.before}%` }} />
                    </div>
                    <span className="w-8 text-right text-neutral-600">{s.before}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-3 text-xs font-semibold text-neutral-500 uppercase tracking-wide">Geographic Exposure</p>
              <div className="space-y-2">
                {PORTFOLIO_FIT.geo_diversification.map((g) => (
                  <div key={g.geo} className="flex items-center gap-2 text-xs">
                    <span className="w-20 text-neutral-500">{g.geo}</span>
                    <div className="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                      <div className="h-2 rounded-full bg-teal-400" style={{ width: `${g.pct * 4}%` }} />
                    </div>
                    <span className="w-8 text-right text-neutral-600">{g.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3">
            {[
              { label: "Mandate Fit",           value: `${project.mandate_fit}%`,  color: project.mandate_fit >= 80 ? "text-green-600" : "text-amber-600" },
              { label: "Sector Diversification", value: "Balanced",                 color: "text-blue-600" },
              { label: "Geographic Overlap",     value: "Low Risk",                  color: "text-green-600" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-lg bg-neutral-50 p-3 text-center">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{label}</p>
                <p className={cn("mt-1 text-lg font-bold", color)}>{value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Investment Action Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Zap className="h-4 w-4 text-amber-500" />
            Investment Action Plan
            <span className="ml-auto text-xs font-normal text-neutral-400">prioritised by urgency</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {(project.dd_gaps.length > 0
              ? project.dd_gaps.map((g, i) => ({
                  action: `Request: ${g.gap}`,
                  urgency: g.priority,
                  responsible: "Investor Team",
                  note: `+${g.score_impact} pts potential`,
                  index: i,
                }))
              : [
                  { action: "Schedule IC presentation with management team", urgency: "High", responsible: "Deal Lead", note: "2 weeks", index: 0 },
                  { action: "Commission independent technical report", urgency: "Medium", responsible: "Technical Advisor", note: "4 weeks", index: 1 },
                  { action: "Complete legal structure and term sheet review", urgency: "Medium", responsible: "Legal", note: "3 weeks", index: 2 },
                ]
            ).map(({ action, urgency, responsible, note, index }) => (
              <div
                key={index}
                className="flex items-start gap-3 rounded-xl border border-neutral-100 bg-neutral-50 px-3 py-2.5"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-amber-600 text-xs font-bold">
                  {index + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-800">{action}</p>
                  <p className="text-xs text-neutral-400 mt-0.5">{responsible} · {note}</p>
                </div>
                <Badge variant={urgency === "High" ? "error" : urgency === "Medium" ? "warning" : "neutral"}>
                  {urgency}
                </Badge>
              </div>
            ))}
          </div>
          <div className="mt-3 flex justify-end">
            <Button size="sm" variant="outline">
              <FileText className="mr-1.5 h-3.5 w-3.5" />
              Generate Full DD Plan
            </Button>
          </div>
        </CardContent>
      </Card>

      <AIFeedback taskType="score_quality" entityType="investor_signal_score" entityId={project.id} compact />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvestorSignalScorePage() {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState<string>("");
  const [isRecalculating, setIsRecalculating] = useState(false);

  const selectedProject = PROJECTS.find((p) => p.id === selectedId) ?? null;

  const portfolio = PROJECTS.filter((p) => p.group === "portfolio");
  const pipeline  = PROJECTS.filter((p) => p.group === "pipeline");

  function handleRecalculate() {
    setIsRecalculating(true);
    setTimeout(() => setIsRecalculating(false), 1800);
  }

  return (
    <div className="space-y-6">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-100">
            <TrendingUp className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Investment Signal Score</h1>
            <p className="mt-1 text-sm text-neutral-500">
              AI-powered investment readiness and portfolio fit analysis across your deal flow and portfolio holdings
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {selectedProject && (
            <Button variant="outline" size="sm" onClick={handleRecalculate} disabled={isRecalculating}>
              <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isRecalculating && "animate-spin")} />
              {isRecalculating ? "Re-evaluating…" : "Re-evaluate"}
            </Button>
          )}
          {/* Project selector */}
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="cursor-pointer rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/30"
          >
            <option value="">Select project to analyse…</option>
            <optgroup label="Portfolio Holdings">
              {portfolio.map((p) => <option key={p.id} value={p.id}>{p.name} — {p.score}</option>)}
            </optgroup>
            <optgroup label="Pipeline / Screening">
              {pipeline.map((p) => <option key={p.id} value={p.id}>{p.name} — {p.score}</option>)}
            </optgroup>
          </select>
        </div>
      </div>

      <InfoBanner />

      {/* ── Hero Stats (dark navy) ─────────────────────────────────────── */}
      <div className="rounded-2xl border border-neutral-200 bg-white px-8 py-10 shadow-sm">
        <p className="mb-8 text-xs font-semibold uppercase tracking-widest text-primary-600">
          Portfolio Signal Score Overview
        </p>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-5">
          {[
            { label: "Average Investment Score", value: HERO_STATS.avg_score,          color: "text-neutral-900", sub: "across all evaluated" },
            { label: "Projects Evaluated",       value: HERO_STATS.projects_evaluated,  color: "text-neutral-900", sub: "total scored" },
            { label: "Investment Ready",         value: HERO_STATS.investment_ready,    color: "text-green-600",   sub: "score ≥ 80" },
            { label: "Portfolio Avg",            value: HERO_STATS.portfolio_avg,        color: "text-blue-600",    sub: "current holdings" },
            { label: "Pipeline Avg",             value: HERO_STATS.pipeline_avg,         color: "text-indigo-600",  sub: "screening deals" },
          ].map(({ label, value, color, sub }) => (
            <div key={label} className={HERO_STATS.avg_score === value ? "col-span-2 sm:col-span-1" : ""}>
              <p className={cn(
                "font-bold tabular-nums leading-none",
                HERO_STATS.avg_score === value ? "text-[80px]" : "text-[80px] sm:text-[56px]",
                color
              )}>
                {value}
              </p>
              <p className="mt-2 text-sm font-medium text-neutral-600">{label}</p>
              <p className="mt-0.5 text-xs text-neutral-400">{sub}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Selected project detail ────────────────────────────────────── */}
      {selectedProject ? (
        <ProjectScoreDetail project={selectedProject} />
      ) : (
        <div className="rounded-xl border border-dashed border-neutral-300 py-12 text-center">
          <Target className="mx-auto h-10 w-10 text-neutral-300 mb-3" />
          <p className="text-sm font-semibold text-neutral-600">Select a project to view its investment analysis</p>
          <p className="text-xs text-neutral-400 mt-1">Choose from portfolio holdings or pipeline deals in the dropdown above</p>
        </div>
      )}

      {/* ── Individual Project Scores Table ───────────────────────────── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-neutral-500" />
            Individual Project Scores
          </CardTitle>
          <Button
            size="sm"
            className="bg-[#1B2A4A] text-white hover:bg-[#243660]"
            onClick={() => router.push("/deals")}
          >
            <Target className="mr-1.5 h-3.5 w-3.5" />
            Evaluate New Project
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-neutral-200 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                  <th className="px-6 py-3">Project Name</th>
                  <th className="px-3 py-3">Sector · Geo</th>
                  <th className="px-3 py-3">Stage</th>
                  <th className="px-3 py-3">Score</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Mandate Fit</th>
                  <th className="px-3 py-3">Last Evaluated</th>
                  <th className="px-3 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {/* Portfolio group */}
                <tr>
                  <td colSpan={8} className="px-6 py-2 bg-neutral-50 border-b border-neutral-100">
                    <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Portfolio Holdings</span>
                  </td>
                </tr>
                {portfolio.map((p) => {
                  const { label: bl, variant: bv } = scoreBadgeLabel(p.score);
                  return (
                    <tr key={p.id} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-3 font-medium text-neutral-900">{p.name}</td>
                      <td className="px-3 py-3 text-xs text-neutral-500">{p.sector} · {p.geo}</td>
                      <td className="px-3 py-3 text-xs text-neutral-500">{p.stage}</td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <span className={cn("text-xl font-bold tabular-nums", scoreColor(p.score))}>{p.score}</span>
                          <Badge variant={bv}>{bl}</Badge>
                          {p.trend === "up" && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {p.trend === "down" && <TrendingDown className="h-3 w-3 text-red-500" />}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={p.status === "performing" ? "success" : p.status === "watch_list" ? "warning" : "neutral"}>
                          {p.status === "performing" ? "Investment Ready" : p.status === "watch_list" ? "Watch List" : "Active"}
                        </Badge>
                      </td>
                      <td className="px-3 py-3">
                        <span className={cn("text-sm font-semibold", p.mandate_fit >= 85 ? "text-green-600" : p.mandate_fit >= 70 ? "text-blue-600" : "text-amber-600")}>
                          {p.mandate_fit}%
                        </span>
                      </td>
                      <td className="px-3 py-3 text-xs text-neutral-400">{p.evaluated_at}</td>
                      <td className="px-3 py-3 text-right">
                        <button
                          onClick={() => setSelectedId(p.id)}
                          className="text-sm font-medium text-[#1B2A4A] hover:underline"
                        >
                          View Analysis
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {/* Pipeline group */}
                <tr>
                  <td colSpan={8} className="px-6 py-2 bg-neutral-50 border-b border-neutral-100 border-t-2 border-t-neutral-200">
                    <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Pipeline / Screening</span>
                  </td>
                </tr>
                {pipeline.map((p) => {
                  const { label: bl, variant: bv } = scoreBadgeLabel(p.score);
                  return (
                    <tr key={p.id} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-3 font-medium text-neutral-900">{p.name}</td>
                      <td className="px-3 py-3 text-xs text-neutral-500">{p.sector} · {p.geo}</td>
                      <td className="px-3 py-3 text-xs text-neutral-500">{p.stage}</td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <span className={cn("text-xl font-bold tabular-nums", scoreColor(p.score))}>{p.score}</span>
                          <Badge variant={bv}>{bl}</Badge>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={p.status === "screening" ? "info" : "neutral"}>
                          {p.status === "screening" ? "Screening" : p.status === "passed" ? "Passed" : "Active"}
                        </Badge>
                      </td>
                      <td className="px-3 py-3">
                        <span className={cn("text-sm font-semibold", p.mandate_fit >= 85 ? "text-green-600" : p.mandate_fit >= 70 ? "text-blue-600" : "text-amber-600")}>
                          {p.mandate_fit}%
                        </span>
                      </td>
                      <td className="px-3 py-3 text-xs text-neutral-400">{p.evaluated_at}</td>
                      <td className="px-3 py-3 text-right">
                        <button
                          onClick={() => setSelectedId(p.id)}
                          className="text-sm font-medium text-[#1B2A4A] hover:underline"
                        >
                          View Analysis
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-neutral-200 bg-neutral-50">
                  <td colSpan={8} className="px-6 py-2.5 text-xs text-neutral-400">
                    Each project is evaluated using 6 investor-specific dimensions. Scores update as new information is provided by project developers.
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="space-y-3 p-4 sm:hidden">
            {PROJECTS.map((p) => {
              const { label: bl, variant: bv } = scoreBadgeLabel(p.score);
              return (
                <div
                  key={p.id}
                  className="rounded-lg border border-neutral-200 bg-white px-4 py-3 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-neutral-900">{p.name}</p>
                      <p className="text-xs text-neutral-400">{p.sector} · {p.geo}</p>
                    </div>
                    <div className="text-right">
                      <p className={cn("text-2xl font-bold tabular-nums", scoreColor(p.score))}>{p.score}</p>
                      <Badge variant={bv}>{bl}</Badge>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-xs text-neutral-400">Mandate fit: {p.mandate_fit}%</span>
                    <button
                      onClick={() => setSelectedId(p.id)}
                      className="text-sm font-medium text-[#1B2A4A] hover:underline"
                    >
                      View Analysis →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
