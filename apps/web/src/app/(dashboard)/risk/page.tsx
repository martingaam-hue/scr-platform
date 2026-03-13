"use client";

import { useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Clock,
  DollarSign,
  FileText,
  Globe,
  Leaf,
  Lightbulb,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Zap,
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
  cn,
} from "@scr/ui";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { AIFeedback } from "@/components/ai-feedback";
import { InfoBanner } from "@/components/info-banner";

// ── Color helpers ─────────────────────────────────────────────────────────────

function healthColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 70) return "#3b82f6";
  if (score >= 60) return "#f59e0b";
  if (score >= 50) return "#eab308";
  return "#ef4444";
}

// ── Domain config ─────────────────────────────────────────────────────────────

const DOMAIN_LABELS: Record<string, string> = {
  technical: "Technical Risk",
  financial: "Financial Risk",
  regulatory: "Regulatory Risk",
  esg: "ESG Risk",
  market: "Market Risk",
};

const DOMAIN_ICON: Record<string, React.ComponentType<{ className?: string }>> =
  {
    technical: Settings,
    financial: DollarSign,
    regulatory: FileText,
    esg: Leaf,
    market: Globe,
  };

const DOMAIN_DESC: Record<string, string> = {
  technical:
    "Technology maturity, execution risk, construction timeline, performance guarantees",
  financial:
    "Revenue concentration, currency exposure, refinancing risk, counterparty creditworthiness, debt covenants",
  regulatory:
    "Permit status, policy change exposure, subsidy dependency, cross-border regulatory complexity",
  esg:
    "Greenwashing risk, taxonomy misalignment, social license issues, governance gaps, reporting compliance",
  market:
    "Commodity price exposure, demand risk, competitive pressure, macroeconomic sensitivity, exit market risk",
};

// ── Mock data — types ─────────────────────────────────────────────────────────

type HoldingEntry = {
  id: string;
  name: string;
  sector: string;
  geo: string;
  score: number;
  exposure_m: number;
  trend: "up" | "down" | "flat";
  domains: Record<string, number>;
  alert_counts: { high: number; medium: number; low: number };
};

type AlertEntry = {
  id: string;
  severity: "high" | "medium" | "low";
  domain: keyof typeof DOMAIN_LABELS;
  holding_id: string;
  holding_name: string;
  title: string;
  description: string;
  portfolio_impact: string;
  action: string;
};

type AuditEntry = {
  id: string;
  ts: string;
  action: string;
  entity: string;
  entity_id: string;
  user: string;
  detail: string;
};

// ── Holdings ──────────────────────────────────────────────────────────────────

const HOLDINGS: HoldingEntry[] = [
  {
    id: "h1",
    name: "Helios Solar",
    sector: "Solar PV",
    geo: "Spain",
    score: 82,
    exposure_m: 45,
    trend: "up",
    domains: { technical: 84, financial: 78, regulatory: 85, esg: 88, market: 76 },
    alert_counts: { high: 0, medium: 2, low: 0 },
  },
  {
    id: "h2",
    name: "Nordvik Wind",
    sector: "Wind",
    geo: "Norway",
    score: 68,
    exposure_m: 62,
    trend: "down",
    domains: { technical: 71, financial: 65, regulatory: 72, esg: 74, market: 58 },
    alert_counts: { high: 1, medium: 3, low: 0 },
  },
  {
    id: "h3",
    name: "Adriatic Infrastructure",
    sector: "Infra",
    geo: "Croatia",
    score: 85,
    exposure_m: 38,
    trend: "flat",
    domains: { technical: 88, financial: 82, regulatory: 86, esg: 84, market: 85 },
    alert_counts: { high: 0, medium: 0, low: 1 },
  },
  {
    id: "h4",
    name: "Baltic BESS",
    sector: "Storage",
    geo: "Lithuania",
    score: 54,
    exposure_m: 28,
    trend: "down",
    domains: { technical: 60, financial: 48, regulatory: 55, esg: 62, market: 45 },
    alert_counts: { high: 2, medium: 2, low: 0 },
  },
  {
    id: "h5",
    name: "Alpine Hydro",
    sector: "Hydro",
    geo: "Austria",
    score: 91,
    exposure_m: 52,
    trend: "up",
    domains: { technical: 93, financial: 90, regulatory: 88, esg: 95, market: 89 },
    alert_counts: { high: 0, medium: 0, low: 0 },
  },
  {
    id: "h6",
    name: "Nordic Biomass",
    sector: "Biomass",
    geo: "Sweden",
    score: 73,
    exposure_m: 31,
    trend: "flat",
    domains: { technical: 76, financial: 70, regulatory: 68, esg: 72, market: 79 },
    alert_counts: { high: 0, medium: 1, low: 0 },
  },
  {
    id: "h7",
    name: "Thames Clean Energy",
    sector: "Multi",
    geo: "UK",
    score: 77,
    exposure_m: 44,
    trend: "up",
    domains: { technical: 80, financial: 75, regulatory: 74, esg: 82, market: 74 },
    alert_counts: { high: 0, medium: 1, low: 2 },
  },
];

const PORTFOLIO_SCORE = 76;
const TOTAL_EXPOSURE_M = HOLDINGS.reduce((s, h) => s + h.exposure_m, 0);

// ── Alerts ────────────────────────────────────────────────────────────────────

const ALERTS: AlertEntry[] = [
  {
    id: "a1",
    severity: "high",
    domain: "financial",
    holding_id: "h2",
    holding_name: "Nordvik Wind",
    title: "Refinancing Risk — 2026 Debt Maturity",
    description:
      "€38M senior debt matures in Q3 2026. Current market rates 180bps above original terms. Refinancing risk elevated given rate environment.",
    portfolio_impact: "Could affect €62M exposure if terms materially worsen",
    action:
      "Engage existing lenders for early refinancing conversation; model 3 rate scenarios",
  },
  {
    id: "a2",
    severity: "high",
    domain: "market",
    holding_id: "h4",
    holding_name: "Baltic BESS",
    title: "Merchant Price Exposure — No PPA in Place",
    description:
      "Project operating fully merchant with no long-term offtake agreement. Intraday battery margins compressed 40% vs underwriting case.",
    portfolio_impact: "Revenue shortfall risk of €4–7M annually vs base case",
    action:
      "Accelerate PPA procurement; consider capacity market participation as floor revenue",
  },
  {
    id: "a3",
    severity: "high",
    domain: "financial",
    holding_id: "h4",
    holding_name: "Baltic BESS",
    title: "DSCR Covenant Breach Risk",
    description:
      "Projected DSCR of 1.08x for H1 2026 vs covenant floor of 1.15x. Cash reserve account being drawn. Lender waiver may be required.",
    portfolio_impact:
      "€28M exposure; potential acceleration clause if covenant breach not waived",
    action:
      "Obtain Q1 actuals immediately; engage lender for waiver or equity cure mechanism",
  },
  {
    id: "a4",
    severity: "medium",
    domain: "technical",
    holding_id: "h1",
    holding_name: "Helios Solar",
    title: "Inverter Degradation Rate Above P50",
    description:
      "Yr 4 performance data shows 0.8%/yr degradation vs 0.5%/yr in PPA model. Technical advisor findings pending.",
    portfolio_impact: "~€600K NPV impact over remaining PPA term if rate persists",
    action: "Review O&M warranty provisions; consider performance bond claim",
  },
  {
    id: "a5",
    severity: "medium",
    domain: "regulatory",
    holding_id: "h1",
    holding_name: "Helios Solar",
    title: "Spanish Clawback Regulation — Exposure Pending Ruling",
    description:
      "Proposed extension of windfall tax to solar PV projects beyond 2025. Legal opinion: 60% likelihood of expansion. Final ruling Q2 2026.",
    portfolio_impact: "€2.1M annual tax exposure if regulation extended",
    action: "Track legislative calendar; model downside into cash flow projections",
  },
  {
    id: "a6",
    severity: "medium",
    domain: "market",
    holding_id: "h2",
    holding_name: "Nordvik Wind",
    title: "Curtailment Rate Increasing — Grid Constraint",
    description:
      "Curtailment rose from 3.2% to 6.8% in 12 months as Norwegian grid operator manages north-south congestion.",
    portfolio_impact: "~€1.8M annual revenue loss at current curtailment rate",
    action:
      "Engage Statnett on grid upgrade timeline; consider curtailment compensation mechanism",
  },
  {
    id: "a7",
    severity: "medium",
    domain: "financial",
    holding_id: "h2",
    holding_name: "Nordvik Wind",
    title: "FX Exposure — NOK/EUR Mismatch",
    description:
      "Revenue in NOK, fund reporting in EUR. No hedging in place. 10% NOK depreciation would reduce fund returns by ~0.3% IRR.",
    portfolio_impact: "Unhedged currency exposure of ~€12M on €62M investment",
    action: "Evaluate FX hedging cost vs unhedged exposure; present options to IC",
  },
  {
    id: "a8",
    severity: "medium",
    domain: "regulatory",
    holding_id: "h2",
    holding_name: "Nordvik Wind",
    title: "Norwegian Resource Rent Tax — Expanded Scope Risk",
    description:
      "Government consulting on expanding resource rent tax to onshore wind. Current proposal: 35% levy on excess returns.",
    portfolio_impact: "Up to €2.8M annual tax impact if applied in full",
    action: "Monitor legislative developments; model three tax scenarios",
  },
  {
    id: "a9",
    severity: "medium",
    domain: "financial",
    holding_id: "h4",
    holding_name: "Baltic BESS",
    title: "Capex Overrun — Phase 2 Expansion",
    description:
      "Phase 2 BESS expansion capex tracking 18% above budget due to elevated battery pack costs and logistics delays.",
    portfolio_impact: "€2.1M additional equity requirement vs plan",
    action: "Hold Phase 2 decision pending cost normalisation; review vendor contracts",
  },
  {
    id: "a10",
    severity: "medium",
    domain: "esg",
    holding_id: "h4",
    holding_name: "Baltic BESS",
    title: "Battery End-of-Life Disposal Plan Missing",
    description:
      "No formal battery EOL management plan in place. EU Battery Regulation 2027 will require documented recycling protocols.",
    portfolio_impact: "Taxonomy misalignment risk; potential SFDR downgrade to Article 6",
    action: "Commission EOL management plan; update SFDR disclosure",
  },
  {
    id: "a11",
    severity: "medium",
    domain: "esg",
    holding_id: "h6",
    holding_name: "Nordic Biomass",
    title: "Sustainability Certification Renewal Overdue",
    description:
      "SBTi certification for biomass feedstock supply chain expires Q3 2026. Renewal requires updated scope 3 data with current gaps.",
    portfolio_impact: "Risk to Article 9 SFDR classification and LP commitments",
    action: "Engage certification body 6 months early; commission scope 3 audit",
  },
  {
    id: "a12",
    severity: "medium",
    domain: "technical",
    holding_id: "h7",
    holding_name: "Thames Clean Energy",
    title: "Grid Connection Delay — Phase 3",
    description:
      "Phase 3 grid connection upgrade delayed 8 months by National Grid queue management. Export curtailment limiting revenue.",
    portfolio_impact: "~€900K revenue deferral vs original schedule",
    action: "Pursue queue acceleration options; engage on curtailment compensation",
  },
  {
    id: "a13",
    severity: "low",
    domain: "esg",
    holding_id: "h3",
    holding_name: "Adriatic Infrastructure",
    title: "Community Consultation Overdue",
    description:
      "Annual community consultation required under environmental permit. Last consultation March 2024. 2025 consultation overdue.",
    portfolio_impact: "Reputational risk and potential permit condition breach",
    action: "Schedule consultation within 60 days; update stakeholder register",
  },
  {
    id: "a14",
    severity: "low",
    domain: "regulatory",
    holding_id: "h7",
    holding_name: "Thames Clean Energy",
    title: "UK CfD Round 7 — Exit Valuation Impact",
    description:
      "CfD Round 7 reference price lower than modeled. Existing CfD contracts unchanged but exit valuations affected.",
    portfolio_impact: "No current cash flow impact; relevant for exit valuation",
    action: "Update exit valuation models with new CfD reference prices",
  },
  {
    id: "a15",
    severity: "low",
    domain: "technical",
    holding_id: "h7",
    holding_name: "Thames Clean Energy",
    title: "Transformer Maintenance — Scheduled Outage Q2",
    description:
      "Planned transformer maintenance in Q2 2026 will cause 12-day generation outage. Fully provisioned in O&M budget.",
    portfolio_impact: "~€180K revenue impact, fully budgeted",
    action: "Confirm outage schedule and contractor availability",
  },
];

// ── Domain portfolio averages ──────────────────────────────────────────────────

const DOMAIN_PORTFOLIO = [
  { domain: "technical", score: 79, risk_count: 4 },
  { domain: "financial", score: 73, risk_count: 5 },
  { domain: "regulatory", score: 74, risk_count: 4 },
  { domain: "esg", score: 79, risk_count: 3 },
  { domain: "market", score: 72, risk_count: 3 },
];

// ── Concentration data ────────────────────────────────────────────────────────

type ConcentrationItem = { label: string; pct: number; is_concentrated: boolean };

const CONCENTRATION: {
  by_sector: ConcentrationItem[];
  by_geo: ConcentrationItem[];
  by_counterparty: ConcentrationItem[];
  by_currency: ConcentrationItem[];
  flags: string[];
} = {
  by_sector: [
    { label: "Wind", pct: 20.7, is_concentrated: false },
    { label: "Hydro", pct: 17.3, is_concentrated: false },
    { label: "Multi", pct: 14.7, is_concentrated: false },
    { label: "Solar PV", pct: 15.0, is_concentrated: false },
    { label: "Infra", pct: 12.7, is_concentrated: false },
  ],
  by_geo: [
    { label: "Norway", pct: 20.7, is_concentrated: true },
    { label: "Austria", pct: 17.3, is_concentrated: false },
    { label: "Spain", pct: 15.0, is_concentrated: false },
    { label: "UK", pct: 14.7, is_concentrated: false },
    { label: "Sweden", pct: 10.3, is_concentrated: false },
  ],
  by_counterparty: [
    { label: "Vattenfall (offtake)", pct: 28.4, is_concentrated: true },
    { label: "Statkraft (offtake)", pct: 20.7, is_concentrated: true },
    { label: "National Grid", pct: 14.7, is_concentrated: false },
    { label: "EnBW (offtake)", pct: 12.3, is_concentrated: false },
    { label: "Other", pct: 23.9, is_concentrated: false },
  ],
  by_currency: [
    { label: "EUR", pct: 52.3, is_concentrated: false },
    { label: "NOK", pct: 20.7, is_concentrated: true },
    { label: "GBP", pct: 14.7, is_concentrated: false },
    { label: "SEK", pct: 10.3, is_concentrated: false },
    { label: "HRK/EUR", pct: 2.0, is_concentrated: false },
  ],
  flags: [
    "Norway exposure (20.7%) approaching 20% single-country threshold",
    "Vattenfall offtake concentration (28.4%) exceeds 25% counterparty limit",
    "Statkraft offtake concentration (20.7%) approaching 20% counterparty limit",
    "NOK unhedged currency exposure (20.7%) — no FX hedge in place",
  ],
};

// ── Scenario mock data ────────────────────────────────────────────────────────

const SCENARIO_RESULT = {
  narrative:
    "A 200bps rate increase would reduce portfolio NAV by €29M (10.4%), primarily driven by higher refinancing costs at Baltic BESS and Nordvik Wind. Fund IRR compresses from 12.4% to 9.8%, remaining above the 8% hurdle rate. Four holdings with fixed-rate debt are unaffected.",
  nav_before: 280_000_000,
  nav_after: 251_000_000,
  nav_delta: -29_000_000,
  nav_delta_pct: -10.4,
  irr_before: 0.124,
  irr_after: 0.098,
  waterfall: [
    { label: "Baseline NAV", value: 280_000_000 },
    { label: "Baltic BESS debt", value: -12_500_000 },
    { label: "Nordvik Wind refi", value: -9_200_000 },
    { label: "Thames CE floating", value: -4_800_000 },
    { label: "Nordic Biomass", value: -2_500_000 },
    { label: "Stressed NAV", value: 251_000_000 },
  ],
  holding_impacts: [
    { name: "Helios Solar", current: 45_000_000, stressed: 45_000_000, delta: 0, delta_pct: 0 },
    { name: "Nordvik Wind", current: 62_000_000, stressed: 52_800_000, delta: -9_200_000, delta_pct: -14.8 },
    { name: "Adriatic Infra", current: 38_000_000, stressed: 38_000_000, delta: 0, delta_pct: 0 },
    { name: "Baltic BESS", current: 28_000_000, stressed: 15_500_000, delta: -12_500_000, delta_pct: -44.6 },
    { name: "Alpine Hydro", current: 52_000_000, stressed: 52_000_000, delta: 0, delta_pct: 0 },
    { name: "Nordic Biomass", current: 31_000_000, stressed: 28_500_000, delta: -2_500_000, delta_pct: -8.1 },
    { name: "Thames CE", current: 44_000_000, stressed: 39_200_000, delta: -4_800_000, delta_pct: -10.9 },
  ],
};

const SCENARIO_TYPES = [
  { label: "Interest Rate +200bps", description: "Floating rate debt stress" },
  { label: "Energy Price −30%", description: "Revenue compression scenario" },
  { label: "Currency Stress NOK −15%", description: "FX exposure impact" },
  { label: "Carbon Price +€50/t", description: "CBAM policy scenario" },
  { label: "Recession — GDP −3%", description: "Broad macroeconomic shock" },
];

// ── Compliance mock data ──────────────────────────────────────────────────────

const COMPLIANCE = {
  sustainable_pct: 72.4,
  taxonomy_eligible_pct: 81.6,
  taxonomy_aligned_pct: 58.3,
  pai_indicators: [
    { id: 1, name: "GHG emissions — Scope 1", category: "Climate", value: "12,400 tCO₂e", unit: "tCO₂e/yr", status: "reported" },
    { id: 2, name: "Carbon footprint", category: "Climate", value: "41.3", unit: "tCO₂e/M€", status: "reported" },
    { id: 3, name: "GHG intensity — investees", category: "Climate", value: "38.7", unit: "tCO₂e/M€ rev", status: "reported" },
    { id: 4, name: "Fossil fuel activities exposure", category: "Climate", value: "0%", unit: "%", status: "reported" },
    { id: 5, name: "Renewable energy share", category: "Climate", value: "94.2%", unit: "%", status: "reported" },
    { id: 6, name: "Energy consumption intensity", category: "Climate", value: "2.4", unit: "MWh/M€ rev", status: "reported" },
    { id: 7, name: "Biodiversity — sensitive areas", category: "Biodiversity", value: "0", unit: "# sites", status: "reported" },
    { id: 8, name: "Emissions to water", category: "Water", value: "n/a", unit: "—", status: "not_applicable" },
    { id: 9, name: "Hazardous waste ratio", category: "Waste", value: "0.8%", unit: "%", status: "reported" },
    { id: 10, name: "UNGC violations", category: "Social", value: "0", unit: "# violations", status: "reported" },
    { id: 11, name: "Lack of UNGC processes", category: "Social", value: "0%", unit: "%", status: "reported" },
    { id: 12, name: "Gender pay gap", category: "Social", value: "12.4%", unit: "%", status: "needs_attention" },
    { id: 13, name: "Board gender diversity", category: "Governance", value: "38.5%", unit: "% female", status: "reported" },
    { id: 14, name: "Controversial weapons exposure", category: "Governance", value: "0%", unit: "%", status: "reported" },
  ],
  dnsh: [
    { holding: "Helios Solar", aligned: true, eligible: true, activity: "Electricity generation from solar PV" },
    { holding: "Nordvik Wind", aligned: true, eligible: true, activity: "Electricity generation from wind power" },
    { holding: "Adriatic Infrastructure", aligned: true, eligible: true, activity: "Transmission/distribution of electricity" },
    { holding: "Baltic BESS", aligned: false, eligible: true, activity: "Storage of electricity" },
    { holding: "Alpine Hydro", aligned: true, eligible: true, activity: "Electricity generation from hydropower" },
    { holding: "Nordic Biomass", aligned: false, eligible: true, activity: "Electricity generation from bioenergy" },
    { holding: "Thames Clean Energy", aligned: true, eligible: true, activity: "Electricity generation — multiple sources" },
  ],
};

// ── Advisor data ──────────────────────────────────────────────────────────────

const ADVISOR_RECS = {
  immediate: [
    { holding: "Baltic BESS", action: "Engage lender for DSCR covenant waiver or equity cure mechanism", impact: "High", effort: "Low", domain: "financial" },
    { holding: "Baltic BESS", action: "Obtain Q1 2026 actuals and stress-test 3 covenant scenarios before IC meeting", impact: "High", effort: "Low", domain: "financial" },
    { holding: "Nordvik Wind", action: "Initiate early refinancing conversation with existing lenders on 2026 debt maturity", impact: "High", effort: "Medium", domain: "financial" },
  ],
  short_term: [
    { holding: "Nordvik Wind", action: "Evaluate FX hedge cost vs unhedged NOK/EUR exposure (~€12M unhedged)", impact: "Medium", effort: "Medium", domain: "financial" },
    { holding: "Helios Solar", action: "Review O&M warranty provisions re inverter degradation above P50", impact: "Medium", effort: "Low", domain: "technical" },
    { holding: "Baltic BESS", action: "Commission battery end-of-life management plan (EU Battery Regulation 2027)", impact: "Medium", effort: "Medium", domain: "esg" },
    { holding: "Nordic Biomass", action: "Initiate SBTi certification renewal 6 months early; commission scope 3 audit", impact: "High", effort: "Medium", domain: "esg" },
  ],
  strategic: [
    { holding: "Portfolio", action: "Reduce Vattenfall counterparty concentration below 25% in next deployment cycle", impact: "High", effort: "High", domain: "financial" },
    { holding: "Portfolio", action: "Establish FX hedging policy for NOK exposure exceeding 15% of NAV", impact: "Medium", effort: "Medium", domain: "financial" },
    { holding: "Baltic BESS", action: "Accelerate PPA procurement — target 60% of revenue under long-term contract", impact: "High", effort: "High", domain: "market" },
    { holding: "Portfolio", action: "Commission portfolio-level DNSH review to support Baltic BESS and Nordic Biomass taxonomy alignment", impact: "High", effort: "High", domain: "esg" },
  ],
};

// ── What changed ──────────────────────────────────────────────────────────────

const WHAT_CHANGED = [
  { holding: "Baltic BESS", prev: 61, curr: 54, direction: "down" as const, reason: "DSCR covenant breach risk identified from Q4 financials; merchant margin compressed 40% vs underwriting" },
  { holding: "Nordvik Wind", prev: 72, curr: 68, direction: "down" as const, reason: "Curtailment rate doubled to 6.8%; resource rent tax expansion risk increased" },
  { holding: "Alpine Hydro", prev: 88, curr: 91, direction: "up" as const, reason: "Record hydro inflow Q4 2025; refinancing completed at favourable terms" },
  { holding: "Thames Clean Energy", prev: 74, curr: 77, direction: "up" as const, reason: "CfD income stable; grid upgrade application progressing ahead of schedule" },
];

// ── Audit data ────────────────────────────────────────────────────────────────

const AUDIT_ENTRIES: AuditEntry[] = [
  { id: "au1", ts: "2026-03-12T14:32:00Z", action: "risk_assessment.updated", entity: "holding", entity_id: "Baltic BESS", user: "j.mcallister", detail: "Updated DSCR covenant projection with Q4 2025 actuals" },
  { id: "au2", ts: "2026-03-11T09:15:00Z", action: "alert.created", entity: "alert", entity_id: "a3", user: "system", detail: "Auto-detected DSCR covenant breach risk from Q4 2025 financials" },
  { id: "au3", ts: "2026-03-10T16:48:00Z", action: "mitigation.generated", entity: "holding", entity_id: "Nordvik Wind", user: "ai-gateway", detail: "AI mitigation strategy generated for financial domain" },
  { id: "au4", ts: "2026-03-08T11:22:00Z", action: "risk_assessment.created", entity: "holding", entity_id: "Baltic BESS", user: "j.mcallister", detail: "Quarterly risk review completed — 2 new HIGH alerts added" },
  { id: "au5", ts: "2026-03-07T14:05:00Z", action: "document.uploaded", entity: "holding", entity_id: "Helios Solar", user: "m.harris", detail: "Technical advisor report — inverter performance yr 4" },
  { id: "au6", ts: "2026-03-05T09:33:00Z", action: "alert.resolved", entity: "alert", entity_id: "old-a1", user: "j.mcallister", detail: "Permit renewal for Adriatic Infra confirmed — alert closed" },
  { id: "au7", ts: "2026-03-03T15:19:00Z", action: "scenario.run", entity: "portfolio", entity_id: "SCR-Fund-I", user: "j.mcallister", detail: "Interest Rate Stress +200bps scenario executed" },
  { id: "au8", ts: "2026-02-28T10:44:00Z", action: "risk_assessment.updated", entity: "holding", entity_id: "Nordic Biomass", user: "s.lindberg", detail: "SBTi certification renewal risk flagged" },
  { id: "au9", ts: "2026-02-25T13:27:00Z", action: "compliance.updated", entity: "portfolio", entity_id: "SCR-Fund-I", user: "s.lindberg", detail: "PAI indicators updated with 2025 full-year data" },
  { id: "au10", ts: "2026-02-20T09:00:00Z", action: "risk_assessment.created", entity: "portfolio", entity_id: "SCR-Fund-I", user: "system", detail: "Monthly automated risk check completed — 14 active alerts" },
];

// ── Reusable components ───────────────────────────────────────────────────────

function HeroScoreCard({ score, label }: { score: number; label?: string }) {
  const color = healthColor(score);
  const size = 200;
  const sw = 14;
  const r = (size - sw) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(score, 0), 100) / 100;
  const offset = circ * (1 - pct);
  const cx = size / 2;

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-8 shadow-sm flex flex-col items-center h-full justify-center">
      <div className="relative">
        <svg width={size} height={size} className="rotate-[-90deg]">
          <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e5e7eb" strokeWidth={sw} />
          <circle
            cx={cx}
            cy={cx}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={sw}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 800ms ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-bold tabular-nums leading-none" style={{ fontSize: "72px", color }}>
            {Math.ceil(score)}
          </span>
        </div>
      </div>
      <p className="mt-3 text-sm text-neutral-500">{label ?? "Portfolio Risk Score"}</p>
      <p className="mt-1 text-xs text-neutral-400">Higher score = better risk management</p>
    </div>
  );
}

function DomainBar({
  domain,
  score,
  risk_count,
}: {
  domain: string;
  score: number;
  risk_count: number;
}) {
  const color = healthColor(score);
  const Icon = DOMAIN_ICON[domain] ?? Globe;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-neutral-700 font-medium">
          <Icon className="h-3.5 w-3.5 text-neutral-400" />
          {DOMAIN_LABELS[domain] ?? domain}
        </span>
        <span className="text-xs font-semibold" style={{ color }}>
          {Math.ceil(score)}
          <span className="text-neutral-400 font-normal"> / {risk_count} alerts</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
        <div
          className="h-2 rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function ConcentrationBar({ item }: { item: ConcentrationItem }) {
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-neutral-600 truncate max-w-[140px]">{item.label}</span>
        <span className={cn("font-semibold", item.is_concentrated ? "text-red-600" : "text-neutral-700")}>
          {item.pct.toFixed(1)}%
          {item.is_concentrated && <AlertTriangle className="inline h-3 w-3 ml-1 text-red-500" />}
        </span>
      </div>
      <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", item.is_concentrated ? "bg-red-400" : "bg-primary-500")}
          style={{ width: `${Math.min(item.pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

function SeverityPill({ severity }: { severity: string }) {
  const cls =
    severity === "high"
      ? "bg-red-100 text-red-700 border-red-200"
      : severity === "medium"
        ? "bg-amber-100 text-amber-700 border-amber-200"
        : "bg-green-100 text-green-700 border-green-200";
  const dot =
    severity === "high" ? "bg-red-500" : severity === "medium" ? "bg-amber-500" : "bg-green-500";
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold border capitalize", cls)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {severity.toUpperCase()}
    </span>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab() {
  const highCount = ALERTS.filter((a) => a.severity === "high").length;

  return (
    <div className="space-y-6">
      {/* Hero + Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-stretch">
        <div className="lg:col-span-3">
          <HeroScoreCard score={PORTFOLIO_SCORE} label="Portfolio Risk Assessment" />
        </div>
        <div className="lg:col-span-2 grid grid-cols-2 gap-3">
          {[
            { label: "Holdings Monitored", value: HOLDINGS.length, color: "text-blue-700", border: "border-blue-100", bg: "bg-blue-50" },
            { label: "Active Alerts", value: ALERTS.length, color: "text-amber-700", border: "border-amber-100", bg: "bg-amber-50" },
            { label: "High Severity", value: highCount, color: "text-red-700", border: "border-red-100", bg: "bg-red-50" },
            { label: "Avg Risk Score", value: PORTFOLIO_SCORE, color: "text-green-700", border: "border-green-100", bg: "bg-green-50" },
          ].map(({ label, value, color, border, bg }) => (
            <div key={label} className={cn("rounded-xl border p-4 flex flex-col justify-center", bg, border)}>
              <p className={cn("text-3xl font-bold tabular-nums", color)}>{value}</p>
              <p className="text-xs text-neutral-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Domain bars */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Risk by Domain — Portfolio Average</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {DOMAIN_PORTFOLIO.map(({ domain, score, risk_count }) => (
            <DomainBar key={domain} domain={domain} score={score} risk_count={risk_count} />
          ))}
        </CardContent>
      </Card>

      {/* Holdings table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Holdings Risk Summary</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-neutral-50">
                  {["Holding", "Sector", "Geography", "Risk Score", "High", "Medium", "Low", "Exposure"].map(
                    (h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y">
                {HOLDINGS.slice()
                  .sort((a, b) => a.score - b.score)
                  .map((h) => (
                    <tr key={h.id} className="hover:bg-neutral-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-neutral-900 text-xs">{h.name}</span>
                          {h.trend === "up" && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {h.trend === "down" && <TrendingDown className="h-3 w-3 text-red-500" />}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-neutral-500">{h.sector}</td>
                      <td className="px-4 py-3 text-xs text-neutral-500">{h.geo}</td>
                      <td className="px-4 py-3">
                        <span className="text-sm font-bold" style={{ color: healthColor(h.score) }}>
                          {Math.ceil(h.score)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-red-700 font-semibold">
                        {h.alert_counts.high || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-amber-600">
                        {h.alert_counts.medium || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-green-600">
                        {h.alert_counts.low || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs font-medium text-neutral-700">
                        €{h.exposure_m}M
                      </td>
                    </tr>
                  ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 bg-neutral-50">
                  <td colSpan={7} className="px-4 py-3 text-xs font-semibold text-neutral-600">
                    Total Portfolio
                  </td>
                  <td className="px-4 py-3 text-xs font-bold text-neutral-800">
                    €{TOTAL_EXPOSURE_M}M
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* What changed */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">What Changed — Recent Risk Score Movements</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {WHAT_CHANGED.map((w) => (
            <div
              key={w.holding}
              className="flex items-start gap-4 p-3 rounded-lg bg-neutral-50 border border-neutral-100"
            >
              <div className="flex items-center gap-2 flex-shrink-0">
                {w.direction === "down" ? (
                  <TrendingDown className="h-4 w-4 text-red-500" />
                ) : (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                )}
                <span className="font-semibold text-sm text-neutral-800 w-36">{w.holding}</span>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-sm font-bold" style={{ color: healthColor(w.prev) }}>
                  {w.prev}
                </span>
                <span className="text-xs text-neutral-400">→</span>
                <span className="text-sm font-bold" style={{ color: healthColor(w.curr) }}>
                  {w.curr}
                </span>
                <span
                  className={cn(
                    "text-xs font-semibold",
                    w.direction === "down" ? "text-red-600" : "text-green-600"
                  )}
                >
                  ({w.direction === "down" ? "" : "+"}{w.curr - w.prev})
                </span>
              </div>
              <p className="text-xs text-neutral-500 flex-1">{w.reason}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Concentration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Concentration Risk</CardTitle>
            {CONCENTRATION.flags.length > 0 && (
              <Badge variant="error">{CONCENTRATION.flags.length} flags</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {CONCENTRATION.flags.length > 0 && (
            <div className="rounded-lg bg-red-50 border border-red-100 p-3 space-y-1">
              {CONCENTRATION.flags.map((f, i) => (
                <p key={i} className="text-xs text-red-700 flex items-center gap-1.5">
                  <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                  {f}
                </p>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {(
              [
                ["By Sector", CONCENTRATION.by_sector],
                ["By Geography", CONCENTRATION.by_geo],
                ["By Counterparty", CONCENTRATION.by_counterparty],
                ["By Currency", CONCENTRATION.by_currency],
              ] as [string, ConcentrationItem[]][]
            ).map(([label, items]) => (
              <div key={label}>
                <p className="text-xs font-medium text-neutral-500 mb-2">{label}</p>
                {items.slice(0, 5).map((item) => (
                  <ConcentrationBar key={item.label} item={item} />
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <AIFeedback taskType="risk_assessment" entityType="portfolio" entityId="scr-fund-i" />
    </div>
  );
}

// ── Alerts Tab ────────────────────────────────────────────────────────────────

function AlertCard({ alert }: { alert: AlertEntry }) {
  const [expanded, setExpanded] = useState(false);
  const cls =
    alert.severity === "high"
      ? { bg: "bg-red-50", border: "border-red-200" }
      : alert.severity === "medium"
        ? { bg: "bg-amber-50", border: "border-amber-200" }
        : { bg: "bg-green-50", border: "border-green-200" };

  return (
    <div className={cn("rounded-lg border p-4", cls.bg, cls.border)}>
      <div
        className="flex items-start gap-3 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <SeverityPill severity={alert.severity} />
            <span className="text-xs text-neutral-500 font-medium">
              {DOMAIN_LABELS[alert.domain]}
            </span>
            <span className="text-xs text-neutral-400">· {alert.holding_name}</span>
          </div>
          <p className="text-sm font-semibold text-neutral-900">{alert.title}</p>
          <p className="text-xs text-neutral-600 mt-0.5 line-clamp-2">{alert.description}</p>
        </div>
        <div className="flex-shrink-0 pt-1">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-neutral-400" />
          )}
        </div>
      </div>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-neutral-200 space-y-2">
          <div className="flex items-start gap-2">
            <span className="text-xs font-semibold text-neutral-500 w-32 flex-shrink-0">
              Portfolio Impact:
            </span>
            <span className="text-xs text-neutral-700">{alert.portfolio_impact}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-xs font-semibold text-neutral-500 w-32 flex-shrink-0">
              Recommended Action:
            </span>
            <span className="text-xs text-neutral-700">{alert.action}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function AlertsTab() {
  const [filter, setFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const filtered = ALERTS.filter((a) => filter === "all" || a.severity === filter);
  const highCount = ALERTS.filter((a) => a.severity === "high").length;
  const medCount = ALERTS.filter((a) => a.severity === "medium").length;
  const lowCount = ALERTS.filter((a) => a.severity === "low").length;

  return (
    <div className="space-y-4">
      {/* Filter pills */}
      <div className="flex gap-2 flex-wrap">
        {[
          { key: "all", label: `All (${ALERTS.length})` },
          { key: "high", label: `High (${highCount})` },
          { key: "medium", label: `Medium (${medCount})` },
          { key: "low", label: `Low (${lowCount})` },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key as typeof filter)}
            className={cn(
              "px-3 py-1 rounded-full text-sm font-medium capitalize transition-colors",
              filter === key
                ? "bg-primary-600 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Alert cards */}
      <div className="space-y-3">
        {filtered.map((alert) => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
      </div>

      {/* AI Analysis bar */}
      {filtered.length > 0 && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 flex items-start gap-3">
          <Sparkles className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-blue-700 mb-1">AI Portfolio Risk Analysis</p>
            <p className="text-xs text-blue-700">
              {highCount > 0
                ? `${highCount} high-severity alert${highCount > 1 ? "s" : ""} require immediate action — Baltic BESS DSCR covenant risk and Nordvik Wind refinancing represent the most significant near-term exposures with combined €90M at risk. `
                : ""}
              {medCount > 0 ? `${medCount} medium alerts are manageable within normal monitoring cadence. ` : ""}
              Primary mitigation priorities: lender engagement on Baltic BESS covenant, FX hedge assessment for NOK exposure, and PPA procurement for Baltic BESS to reduce merchant risk.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Domain Tab ────────────────────────────────────────────────────────────────

function DomainTab() {
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [mitigation, setMitigation] = useState<Record<string, string>>({});
  const [generating, setGenerating] = useState<string | null>(null);

  const radarData = DOMAIN_PORTFOLIO.map(({ domain, score }) => ({
    domain: DOMAIN_LABELS[domain] ?? domain,
    score,
  }));

  const MOCK_MITIGATIONS: Record<string, string> = {
    financial:
      "1. Engage Baltic BESS lenders for DSCR waiver within 14 days.\n2. Model 3 refinancing scenarios for Nordvik Wind 2026 maturity.\n3. Implement NOK/EUR FX hedge for >15% NAV currency exposure.\n4. Review DSCR covenants across all debt-bearing holdings quarterly.",
    technical:
      "1. Commission independent technical advisor report on Helios Solar inverter degradation.\n2. Review O&M warranty provisions and performance bond coverage.\n3. Establish quarterly technical KPI dashboard across all operational assets.",
    regulatory:
      "1. Track Spanish windfall tax legislative calendar; model 3 regulatory scenarios.\n2. Engage external counsel on Norwegian resource rent tax exposure.\n3. Build regulatory monitoring into monthly IC reporting.",
    esg:
      "1. Commission Baltic BESS battery EOL management plan for EU Battery Regulation 2027.\n2. Initiate Nordic Biomass SBTi certification renewal 6 months early.\n3. Complete portfolio-level DNSH review to address taxonomy misalignment.",
    market:
      "1. Accelerate PPA procurement for Baltic BESS — target 60% revenue under long-term contract.\n2. Engage capacity market teams for floor revenue options.\n3. Update exit valuation models with revised CfD reference prices.",
  };

  const handleGenerateMitigation = (domain: string) => {
    setGenerating(domain);
    setTimeout(() => {
      setMitigation((prev) => ({ ...prev, [domain]: MOCK_MITIGATIONS[domain] ?? "Strategy generated." }));
      setGenerating(null);
    }, 1500);
  };

  return (
    <div className="space-y-6">
      {/* Radar + Domain scores */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="md:col-span-3">
          <CardContent className="p-4">
            <p className="text-xs font-medium text-neutral-500 mb-2">
              Domain Risk Radar — Portfolio Average
            </p>
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="domain" tick={{ fontSize: 11, fill: "#6b7280" }} />
                <Radar
                  name="Risk Score"
                  dataKey="score"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.18}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm">Domain Scores</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {DOMAIN_PORTFOLIO.map(({ domain, score, risk_count }) => (
              <DomainBar key={domain} domain={domain} score={score} risk_count={risk_count} />
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Expandable domain cards */}
      <div className="space-y-3">
        {DOMAIN_PORTFOLIO.map(({ domain, score }) => {
          const Icon = DOMAIN_ICON[domain] ?? Globe;
          const domainAlerts = ALERTS.filter((a) => a.domain === domain);
          const isExpanded = expandedDomain === domain;
          return (
            <Card key={domain}>
              <button
                onClick={() => setExpandedDomain(isExpanded ? null : domain)}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-neutral-50 rounded-xl"
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-lg bg-neutral-100">
                    <Icon className="h-4 w-4 text-neutral-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-neutral-800">{DOMAIN_LABELS[domain]}</p>
                    <p className="text-xs text-neutral-500 mt-0.5 max-w-md">
                      {DOMAIN_DESC[domain]}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-4">
                  <div className="text-right">
                    <p
                      className="text-lg font-bold tabular-nums"
                      style={{ color: healthColor(score) }}
                    >
                      {score}
                    </p>
                    <p className="text-xs text-neutral-400">/100</p>
                  </div>
                  <div className="w-20 h-2 rounded-full bg-neutral-200 overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-all"
                      style={{ width: `${score}%`, backgroundColor: healthColor(score) }}
                    />
                  </div>
                  {domainAlerts.length > 0 && (
                    <Badge
                      variant={domainAlerts.some((a) => a.severity === "high") ? "error" : "warning"}
                    >
                      {domainAlerts.length} alert{domainAlerts.length > 1 ? "s" : ""}
                    </Badge>
                  )}
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-neutral-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-neutral-400" />
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="border-t px-4 pb-4">
                  {/* Per-holding scores */}
                  <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
                    {HOLDINGS.map((h) => (
                      <div key={h.id} className="rounded-lg bg-neutral-50 p-2 text-center border border-neutral-100">
                        <p className="text-xs font-medium text-neutral-600 truncate">
                          {h.name.split(" ").slice(0, 2).join(" ")}
                        </p>
                        <p
                          className="text-sm font-bold tabular-nums"
                          style={{ color: healthColor(h.domains[domain] ?? 0) }}
                        >
                          {h.domains[domain] ?? "—"}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Domain alerts */}
                  {domainAlerts.length > 0 && (
                    <div className="space-y-2 mb-4">
                      {domainAlerts.map((alert) => (
                        <div
                          key={alert.id}
                          className="flex items-start gap-2 text-xs p-2 rounded bg-neutral-50 border border-neutral-200"
                        >
                          <SeverityPill severity={alert.severity} />
                          <div>
                            <p className="font-medium text-neutral-800">{alert.title}</p>
                            <p className="text-neutral-500">{alert.holding_name}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* AI Mitigation */}
                  <div className="mt-3 pt-3 border-t border-neutral-100">
                    {mitigation[domain] ? (
                      <div className="rounded-lg border border-purple-100 bg-purple-50 p-3 space-y-2">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-700">
                          <Sparkles className="h-3.5 w-3.5" />
                          AI Investor Mitigation Strategy
                        </div>
                        <p className="text-xs text-purple-900 whitespace-pre-line leading-relaxed">
                          {mitigation[domain]}
                        </p>
                        <button className="text-xs text-purple-600 hover:text-purple-800 font-medium">
                          Save to My Documents
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleGenerateMitigation(domain)}
                        disabled={generating === domain}
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
                      >
                        {generating === domain ? (
                          <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        ) : (
                          <Sparkles className="h-3 w-3" />
                        )}
                        {generating === domain ? "Generating…" : "Generate Investor Mitigation Strategy"}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Scenario Tab ──────────────────────────────────────────────────────────────

function fmtM(n: number) {
  return `€${(n / 1_000_000).toFixed(0)}M`;
}

function ScenarioTab() {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [showResult, setShowResult] = useState(true);

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-neutral-700 mb-3">Select Scenario</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
            {SCENARIO_TYPES.map((s, i) => (
              <button
                key={s.label}
                onClick={() => { setSelectedIdx(i); setShowResult(i === 0); }}
                className={cn(
                  "text-left p-3 rounded-lg border text-xs transition-colors",
                  selectedIdx === i
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-neutral-200 hover:border-neutral-300 text-neutral-600"
                )}
              >
                <p className="font-semibold">{s.label}</p>
                <p className="mt-0.5 text-neutral-500 leading-tight">{s.description}</p>
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowResult(true)}
            className="flex items-center gap-1.5 text-xs px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Run Scenario
          </button>
        </CardContent>
      </Card>

      {showResult && selectedIdx === 0 && (
        <>
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-3">
            <p className="text-sm text-blue-800 italic">{SCENARIO_RESULT.narrative}</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "NAV Before", value: fmtM(SCENARIO_RESULT.nav_before), color: "text-neutral-800", sub: null },
              { label: "NAV After", value: fmtM(SCENARIO_RESULT.nav_after), color: "text-red-600", sub: null },
              { label: "NAV Impact", value: `${SCENARIO_RESULT.nav_delta_pct.toFixed(1)}%`, color: "text-red-600", sub: fmtM(SCENARIO_RESULT.nav_delta) },
              { label: "Fund IRR", value: `${(SCENARIO_RESULT.irr_before * 100).toFixed(1)}% → ${(SCENARIO_RESULT.irr_after * 100).toFixed(1)}%`, color: "text-amber-700", sub: null },
            ].map((m) => (
              <Card key={m.label}>
                <CardContent className="p-4">
                  <p className="text-xs text-neutral-500 mb-1">{m.label}</p>
                  <p className={cn("text-xl font-bold", m.color)}>{m.value}</p>
                  {m.sub && <p className={cn("text-xs mt-0.5", m.color)}>{m.sub}</p>}
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-neutral-700 mb-4">Impact Waterfall</p>
              <div className="space-y-1.5">
                {SCENARIO_RESULT.waterfall.map((w, i) => {
                  const isBase = i === 0 || i === SCENARIO_RESULT.waterfall.length - 1;
                  const barPct = isBase
                    ? 100
                    : Math.min((Math.abs(w.value) / SCENARIO_RESULT.nav_before) * 100, 100);
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-neutral-500 w-36 truncate flex-shrink-0">
                        {w.label}
                      </span>
                      <div className="flex-1 h-5 bg-neutral-100 rounded overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded",
                            isBase ? "bg-neutral-400" : w.value < 0 ? "bg-red-400" : "bg-green-400"
                          )}
                          style={{ width: `${barPct}%` }}
                        />
                      </div>
                      <span
                        className={cn(
                          "text-xs font-semibold w-20 text-right flex-shrink-0",
                          isBase ? "text-neutral-600" : w.value < 0 ? "text-red-600" : "text-green-600"
                        )}
                      >
                        {isBase ? fmtM(w.value) : `${w.value > 0 ? "+" : ""}${fmtM(w.value)}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-neutral-700 mb-3">Per-Holding Impact</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      {["Holding", "Current NAV", "Stressed NAV", "Δ Value", "Δ %"].map((h) => (
                        <th key={h} className="py-2 px-2 text-left text-xs font-semibold text-neutral-500">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {SCENARIO_RESULT.holding_impacts.map((hi) => (
                      <tr key={hi.name} className="border-b border-neutral-100 hover:bg-neutral-50">
                        <td className="py-2 px-2 font-medium text-neutral-700">{hi.name}</td>
                        <td className="py-2 px-2 text-neutral-600">{fmtM(hi.current)}</td>
                        <td className="py-2 px-2 text-neutral-600">{fmtM(hi.stressed)}</td>
                        <td className={cn("py-2 px-2 font-medium", hi.delta < 0 ? "text-red-600" : "text-neutral-600")}>
                          {hi.delta !== 0 ? `${hi.delta > 0 ? "+" : ""}${fmtM(hi.delta)}` : "—"}
                        </td>
                        <td className={cn("py-2 px-2 font-semibold", hi.delta_pct < 0 ? "text-red-600" : "text-neutral-600")}>
                          {hi.delta_pct !== 0 ? `${hi.delta_pct > 0 ? "+" : ""}${hi.delta_pct.toFixed(1)}%` : "—"}
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

      {showResult && selectedIdx !== 0 && (
        <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-8 text-center text-neutral-400">
          <p className="font-medium">Results for &ldquo;{SCENARIO_TYPES[selectedIdx].label}&rdquo;</p>
          <p className="text-sm mt-1">
            Run the scenario to see NAV impact and per-holding breakdown.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Compliance Tab ────────────────────────────────────────────────────────────

function ComplianceTab() {
  const [expandedHolding, setExpandedHolding] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* SFDR + bars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-1">
          <CardContent className="p-6 flex flex-col items-center justify-center text-center">
            <ShieldCheck className="h-8 w-8 text-blue-400 mb-3" />
            <p className="text-xs text-neutral-500 mb-2 font-medium uppercase tracking-wide">
              SFDR Classification
            </p>
            <span className="text-lg font-bold px-4 py-2 rounded-full border border-blue-200 bg-blue-50 text-blue-700">
              Article 8
            </span>
            <p className="text-sm font-semibold mt-3 text-amber-600">⚠ Needs Attention</p>
            <p className="text-xs text-neutral-400 mt-1">
              Baltic BESS & Nordic Biomass taxonomy gaps
            </p>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardContent className="p-5 space-y-5">
            {[
              { label: "Sustainable Investment", value: COMPLIANCE.sustainable_pct, threshold: 50 },
              { label: "Taxonomy Eligible", value: COMPLIANCE.taxonomy_eligible_pct, threshold: undefined },
              { label: "Taxonomy Aligned", value: COMPLIANCE.taxonomy_aligned_pct, threshold: 60 },
            ].map(({ label, value, threshold }) => (
              <div key={label}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-neutral-700">{label}</span>
                  <span className="font-bold text-neutral-800">{value.toFixed(1)}%</span>
                </div>
                <div className="h-3 bg-neutral-100 rounded-full overflow-hidden relative">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      !threshold || value >= threshold ? "bg-green-500" : "bg-amber-400"
                    )}
                    style={{ width: `${Math.min(value, 100)}%` }}
                  />
                  {threshold && (
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-neutral-400"
                      style={{ left: `${threshold}%` }}
                    />
                  )}
                </div>
                {threshold && (
                  <p className="text-xs text-neutral-400 mt-1">
                    Target: {threshold}% for Article 8
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* PAI indicators */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-neutral-700 mb-3">
            Principal Adverse Impact (PAI) Indicators — 14 Mandatory
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200">
                  {["#", "Indicator", "Category", "Value", "Unit", "Status"].map((h) => (
                    <th key={h} className="py-2 px-2 text-left text-xs font-semibold text-neutral-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPLIANCE.pai_indicators.map((pai) => (
                  <tr key={pai.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                    <td className="py-2 px-2 text-neutral-400 text-xs">{pai.id}</td>
                    <td className="py-2 px-2 font-medium text-neutral-700">{pai.name}</td>
                    <td className="py-2 px-2 text-neutral-500">{pai.category}</td>
                    <td className="py-2 px-2 text-neutral-600">{pai.value}</td>
                    <td className="py-2 px-2 text-neutral-400 text-xs">{pai.unit}</td>
                    <td
                      className={cn(
                        "py-2 px-2 text-xs font-semibold",
                        pai.status === "reported"
                          ? "text-green-600"
                          : pai.status === "needs_attention"
                            ? "text-amber-600"
                            : "text-neutral-400"
                      )}
                    >
                      {pai.status === "reported"
                        ? "✓ Reported"
                        : pai.status === "not_applicable"
                          ? "N/A"
                          : "⚠ Attention"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* DNSH per holding */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-semibold text-neutral-700 mb-3">
            EU Taxonomy — Alignment by Holding
          </p>
          <div className="space-y-2">
            {COMPLIANCE.dnsh.map((tr) => (
              <div key={tr.holding} className="border border-neutral-200 rounded-lg">
                <button
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-neutral-50"
                  onClick={() =>
                    setExpandedHolding(expandedHolding === tr.holding ? null : tr.holding)
                  }
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={tr.aligned ? "success" : tr.eligible ? "warning" : "neutral"}>
                      {tr.aligned ? "Aligned" : tr.eligible ? "Eligible" : "Not Eligible"}
                    </Badge>
                    <span className="text-sm font-medium text-neutral-700">{tr.holding}</span>
                    <span className="text-xs text-neutral-400 hidden sm:block">{tr.activity}</span>
                  </div>
                  {expandedHolding === tr.holding ? (
                    <ChevronDown className="h-4 w-4 text-neutral-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-neutral-400" />
                  )}
                </button>
                {expandedHolding === tr.holding && (
                  <div className="border-t border-neutral-200 p-3">
                    <p className="text-xs text-neutral-500">
                      {tr.aligned
                        ? "✓ Meets all Do No Significant Harm criteria and minimum social safeguards."
                        : "⚠ Taxonomy eligible but not yet fully aligned. DNSH assessment gaps identified — see active ESG alerts."}
                    </p>
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

// ── Investment Advisor Tab ────────────────────────────────────────────────────

function AdvisorTab() {
  const sections = [
    {
      key: "immediate",
      label: "Immediate — This Week",
      icon: Zap,
      color: "text-red-600",
      bg: "bg-red-50",
      border: "border-red-100",
      recs: ADVISOR_RECS.immediate,
    },
    {
      key: "short_term",
      label: "Short-term — This Month",
      icon: Clock,
      color: "text-amber-600",
      bg: "bg-amber-50",
      border: "border-amber-100",
      recs: ADVISOR_RECS.short_term,
    },
    {
      key: "strategic",
      label: "Strategic — This Quarter",
      icon: Target,
      color: "text-blue-600",
      bg: "bg-blue-50",
      border: "border-blue-100",
      recs: ADVISOR_RECS.strategic,
    },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Summary hero */}
      <div className="rounded-xl border border-[#1B2A4A]/20 bg-gradient-to-br from-[#1B2A4A] to-[#243660] p-6 text-white">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="h-5 w-5 text-amber-300" />
          <h3 className="font-semibold">Investment Risk Advisor</h3>
        </div>
        <p className="text-sm text-blue-100">
          Based on current portfolio risk scores and active alerts, your most critical near-term
          priorities are:{" "}
          <strong className="text-white">Baltic BESS covenant management</strong> (risk of lender
          acceleration),{" "}
          <strong className="text-white">Nordvik Wind refinancing</strong> (2026 debt maturity),
          and <strong className="text-white">NOK/EUR FX exposure</strong> (€12M unhedged). Fund IRR
          remains above 8% hurdle in base case but compresses to 9.8% under 200bps rate stress.
        </p>
        <div className="mt-4 flex gap-6">
          {[
            { label: "Immediate Actions", value: ADVISOR_RECS.immediate.length, color: "text-red-300" },
            { label: "Short-term Actions", value: ADVISOR_RECS.short_term.length, color: "text-amber-300" },
            { label: "Strategic Actions", value: ADVISOR_RECS.strategic.length, color: "text-blue-300" },
          ].map((s) => (
            <div key={s.label}>
              <p className={cn("text-2xl font-bold", s.color)}>{s.value}</p>
              <p className="text-xs text-blue-200">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendation sections */}
      {sections.map(({ key, label, icon: Icon, color, bg, border, recs }) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Icon className={cn("h-4 w-4", color)} />
              {label}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {recs.map((rec, i) => (
              <div key={i} className={cn("rounded-lg border p-4", bg, border)}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-neutral-600">{rec.holding}</span>
                      <span className="text-xs text-neutral-400">·</span>
                      <span className="text-xs text-neutral-500">
                        {DOMAIN_LABELS[rec.domain]}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-neutral-800">{rec.action}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <Badge
                      variant={
                        rec.impact === "High"
                          ? "error"
                          : rec.impact === "Medium"
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {rec.impact} Impact
                    </Badge>
                    <span className="text-xs text-neutral-400">{rec.effort} Effort</span>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      <div className="flex justify-center">
        <button className="flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
          <Sparkles className="h-4 w-4" />
          Generate Risk-Adjusted Portfolio Review
        </button>
      </div>

      <AIFeedback taskType="risk_assessment" entityType="portfolio" entityId="scr-fund-i" />
    </div>
  );
}

// ── Audit Tab ─────────────────────────────────────────────────────────────────

function AuditTab() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [entityFilter, setEntityFilter] = useState("");

  const filtered = AUDIT_ENTRIES.filter(
    (e) => !entityFilter || e.action.includes(entityFilter) || e.entity.includes(entityFilter)
  );

  const handleExportCsv = () => {
    const rows = [
      ["Timestamp", "Action", "Entity", "Entity ID", "User", "Detail"],
      ...AUDIT_ENTRIES.map((e) => [e.ts, e.action, e.entity, e.entity_id, e.user, e.detail]),
    ];
    const csv = rows.map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audit-trail.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
        <select
          className="text-sm border border-neutral-200 rounded px-2 py-1 bg-white"
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
        >
          <option value="">All Events</option>
          <option value="risk_assessment">Risk Assessments</option>
          <option value="alert">Alerts</option>
          <option value="scenario">Scenarios</option>
          <option value="compliance">Compliance</option>
          <option value="document">Documents</option>
          <option value="mitigation">Mitigations</option>
        </select>
        <button
          onClick={handleExportCsv}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-neutral-200 rounded bg-white hover:bg-neutral-50"
        >
          Export CSV
        </button>
      </div>

      <div className="space-y-1">
        {filtered.map((entry) => {
          const isCreate =
            entry.action.includes("created") || entry.action.includes("generated");
          const isResolve =
            entry.action.includes("resolved") || entry.action.includes("updated");
          const actionColor = isResolve
            ? "text-green-700 bg-green-50"
            : isCreate
              ? "text-blue-700 bg-blue-50"
              : "text-neutral-700 bg-neutral-100";

          return (
            <div key={entry.id} className="border border-neutral-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-neutral-50 text-sm"
              >
                <span className="text-xs text-neutral-400 font-mono w-36 flex-shrink-0">
                  {new Date(entry.ts).toLocaleString()}
                </span>
                <span
                  className={cn(
                    "text-xs font-semibold px-2 py-0.5 rounded capitalize flex-shrink-0",
                    actionColor
                  )}
                >
                  {entry.action.replace(/\./g, " ").replace(/_/g, " ")}
                </span>
                <span className="text-xs text-neutral-500 flex-shrink-0 capitalize">
                  {entry.entity.replace(/_/g, " ")}
                </span>
                <span className="text-xs text-neutral-400 truncate flex-1">{entry.entity_id}</span>
                <span className="text-xs text-neutral-400 font-mono hidden sm:block flex-shrink-0">
                  {entry.user}
                </span>
                {expandedId === entry.id ? (
                  <ChevronDown className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                )}
              </button>
              {expandedId === entry.id && (
                <div className="border-t border-neutral-200 bg-neutral-50 p-3">
                  <p className="text-xs text-neutral-600">{entry.detail}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvestorRiskPage() {
  const highAlerts = ALERTS.filter((a) => a.severity === "high").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <ShieldCheck className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Portfolio Risk Assessment</h1>
            <p className="text-neutral-500 mt-1">
              Investment risk monitoring, stress testing, SFDR compliance, and investment advisor
            </p>
          </div>
        </div>
        <select className="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 bg-white font-medium">
          <option value="portfolio">All Holdings (Portfolio View)</option>
          <optgroup label="Portfolio Holdings">
            {HOLDINGS.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name} — {h.score}/100
              </option>
            ))}
          </optgroup>
        </select>
      </div>

      <InfoBanner>
        <strong>Portfolio Risk Assessment</strong> monitors investment risk across 5 domains, runs
        stress scenarios, tracks SFDR compliance, and generates AI-powered mitigation strategies.{" "}
        <strong>Higher score = better risk management</strong> — green ≥ 80, blue ≥ 70, amber ≥
        60, red below 50.
      </InfoBanner>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="alerts">
            Alerts
            {highAlerts > 0 && (
              <span className="ml-1.5 bg-red-500 text-white text-xs font-bold rounded-full px-1.5 py-0.5 leading-none">
                {highAlerts}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="domains">Domain Analysis</TabsTrigger>
          <TabsTrigger value="scenario">Scenario Analysis</TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
          <TabsTrigger value="advisor">Investment Advisor</TabsTrigger>
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab />
        </TabsContent>
        <TabsContent value="alerts" className="mt-6">
          <AlertsTab />
        </TabsContent>
        <TabsContent value="domains" className="mt-6">
          <DomainTab />
        </TabsContent>
        <TabsContent value="scenario" className="mt-6">
          <ScenarioTab />
        </TabsContent>
        <TabsContent value="compliance" className="mt-6">
          <ComplianceTab />
        </TabsContent>
        <TabsContent value="advisor" className="mt-6">
          <AdvisorTab />
        </TabsContent>
        <TabsContent value="audit" className="mt-6">
          <AuditTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
