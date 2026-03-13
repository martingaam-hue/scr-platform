"use client";

import { useState } from "react";
import {
  BarChart2,
  Bell,
  BookOpen,
  Building2,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  FileText,
  Filter,
  Globe,
  Layers,
  Loader2,
  MessageSquare,
  Minus,
  Plus,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@scr/ui";
import {
  useMarketDataSummary,
  useMarketDataSeries,
  useSeriesHistory,
  useRefreshMarketData,
  formatIndicatorValue,
  changePctColor,
  SOURCE_LABELS,
  type MarketDataSummary,
  type ExternalDataPoint,
} from "@/lib/market-data";
import { InfoBanner } from "@/components/info-banner";
import { AIFeedback } from "@/components/ai-feedback";

// ── Types ─────────────────────────────────────────────────────────────────────

type NewsItem = {
  id: string;
  headline: string;
  source: string;
  source_category: string;
  published: string;
  relevance: "high" | "medium" | "low";
  impact: "positive" | "negative" | "neutral";
  category: "Regulatory" | "Market" | "Transaction" | "Policy" | "Technology" | "ESG" | "Financial";
  sector: string;
  geography: string;
  affected_holdings: string[];
  summary: string;
  ai_analysis: string;
  recommended_action: string;
  confidence: number;
};

type MarketMetric = {
  id: string;
  label: string;
  value: string;
  change_pct: number;
  unit: string;
  favorable_direction: "up" | "down";
  category: string;
};

type RegulatoryItem = {
  id: string;
  name: string;
  jurisdiction: string;
  status: "Proposed" | "Consultation" | "Adopted" | "Effective";
  effective_date: string;
  sector: string;
  severity: "Critical" | "Important" | "Informational";
  summary: string;
  affected_holdings: string[];
};

type UpcomingDate = {
  id: string;
  title: string;
  date: string;
  type: string;
  urgency: "high" | "medium" | "low";
  regulation: string;
};

type ComparableTransaction = {
  id: string;
  buyer: string;
  seller: string;
  asset: string;
  sector: string;
  geography: string;
  deal_size: string;
  multiple: string | null;
  date: string;
};

type WatchlistItem = {
  id: string;
  name: string;
  criteria: string;
  type: "keyword" | "company" | "regulation" | "price";
  active: boolean;
  alerts_today: number;
};

// ── Mock Data ─────────────────────────────────────────────────────────────────

const BRIEFING_SUMMARY =
  "European Commission announced enhanced renewable energy targets under REPowerEU revision, potentially accelerating permitting for solar and wind projects across Southern Europe. This directly benefits Helios Solar Portfolio Iberia and Thames Clean Energy Hub. Meanwhile, lithium carbonate prices dropped 8% this month, improving the cost outlook for Baltic BESS Grid Storage. ECB held rates steady at 2.5%, maintaining favorable refinancing conditions for infrastructure debt across the portfolio.";

const BRIEFING_STATS = [
  { label: "Articles Screened", value: "1,247", icon: FileText },
  { label: "Portfolio-Relevant", value: "43", icon: Layers },
  { label: "High Impact", value: "8", icon: Zap },
  { label: "Sectors Covered", value: "6", icon: Globe },
];

const NEWS_ITEMS: NewsItem[] = [
  {
    id: "n1",
    headline: "EU Adopts Accelerated Permitting Framework for Renewables",
    source: "Reuters",
    source_category: "Financial News",
    published: "2h ago",
    relevance: "high",
    impact: "positive",
    category: "Regulatory",
    sector: "Renewable Energy",
    geography: "European Union",
    affected_holdings: ["Helios Solar Portfolio Iberia", "Nordvik Wind Farm", "Thames Clean Energy Hub"],
    summary:
      "The European Commission formally adopted a revised permitting framework that cuts average approval times for renewables from 9 years to under 2 years. The regulation applies immediately across all EU member states and includes fast-track processes for solar, wind, and storage.",
    ai_analysis:
      "This is a material positive for solar and wind holdings in EU jurisdictions. Helios Solar Iberia's pending 340 MW expansion and Nordvik Wind's Danish repowering project could benefit from significantly reduced permitting timelines. Expected development cost reduction of 8-12% for future projects. Thames Clean Energy Hub (UK) operates under separate GB rules but EU precedent often influences UK policy direction.",
    recommended_action: "Monitor and investigate",
    confidence: 94,
  },
  {
    id: "n2",
    headline: "Spanish Government Announces Solar Auction Schedule for 2026",
    source: "El Economista",
    source_category: "Industry Publications",
    published: "5h ago",
    relevance: "high",
    impact: "positive",
    category: "Policy",
    sector: "Renewable Energy",
    geography: "Spain",
    affected_holdings: ["Helios Solar Portfolio Iberia"],
    summary:
      "Spain's Ministry for Ecological Transition confirmed a 6 GW competitive auction for solar capacity in Q3 2026, with guaranteed grid connection within 18 months. The auction includes a 15-year contract-for-difference mechanism priced above current PPA market rates.",
    ai_analysis:
      "Helios Solar Portfolio Iberia has two development-stage projects in Andalusia and Castile totaling 180 MW of uncontracted capacity. This auction creates a direct monetization pathway at potentially above-market contracted rates. The CfD mechanism reduces merchant price risk significantly. Recommend evaluating bid strategy for the Q3 auction.",
    recommended_action: "Investigate",
    confidence: 91,
  },
  {
    id: "n3",
    headline: "Battery Storage Costs Hit Record Low in European Markets",
    source: "BloombergNEF",
    source_category: "Market Data",
    published: "8h ago",
    relevance: "medium",
    impact: "positive",
    category: "Market",
    sector: "Energy Storage",
    geography: "Europe",
    affected_holdings: ["Baltic BESS Grid Storage"],
    summary:
      "European utility-scale battery system costs fell to €118/kWh in Q1 2026, down 23% year-on-year, driven by lithium carbonate price declines and increased cell manufacturing capacity. Grid-scale BESS IRRs are improving across most markets.",
    ai_analysis:
      "Baltic BESS Grid Storage's expansion tranche (100 MW / 200 MWh) was underwritten at €135/kWh in 2024. Current market rates imply capex savings of €3.4M on the planned Phase 2. However, competitive dynamics for grid services revenue may tighten as more storage enters the market in the Baltic states.",
    recommended_action: "Monitor",
    confidence: 87,
  },
  {
    id: "n4",
    headline: "Norway Grid Operator Reports Connection Queue Delays",
    source: "Montel",
    source_category: "Industry Publications",
    published: "1d ago",
    relevance: "high",
    impact: "negative",
    category: "Regulatory",
    sector: "Renewable Energy",
    geography: "Norway",
    affected_holdings: ["Nordvik Wind Farm"],
    summary:
      "Statnett announced that grid connection requests in northern Norway face 4-6 year queuing delays due to transmission capacity constraints. New applicants will be assigned to post-2030 connection slots unless network reinforcement investments are accelerated.",
    ai_analysis:
      "Nordvik Wind Farm's Phase 3 repowering (120 MW) holds a provisional connection agreement from 2022 that pre-dates the queue freeze. However, Nordvik's Phase 4 expansion plans (80 MW) may be materially impacted. Recommend confirming the legal status of existing connection rights with the project operator and assessing Phase 4 timeline risk.",
    recommended_action: "Investigate",
    confidence: 89,
  },
  {
    id: "n5",
    headline: "ECB Maintains Interest Rates at 2.5%",
    source: "European Central Bank",
    source_category: "Government & Regulatory",
    published: "1d ago",
    relevance: "medium",
    impact: "neutral",
    category: "Financial",
    sector: "All Sectors",
    geography: "Eurozone",
    affected_holdings: [
      "Helios Solar Portfolio Iberia",
      "Nordvik Wind Farm",
      "Adriatic Infrastructure Fund",
      "Baltic BESS Grid Storage",
      "Alpine Hydro Concessions",
      "Nordic Biomass Energy",
      "Thames Clean Energy Hub",
    ],
    summary:
      "The ECB Governing Council voted to hold the deposit facility rate at 2.5% at its March 2026 meeting. Forward guidance indicates rates will remain at current levels through mid-2026 before potential further easing.",
    ai_analysis:
      "Stable rates benefit the portfolio's fixed-income financed holdings. Adriatic Infrastructure Fund has €180M of floating-rate project finance debt hedged above current market rates — the hedge book is now generating positive carry. Alpine Hydro and Nordvik refinancings scheduled for H2 2026 face a potentially more favorable rate environment if ECB easing proceeds as signaled.",
    recommended_action: "Monitor",
    confidence: 99,
  },
  {
    id: "n6",
    headline: "Italian Infrastructure Spending Bill Passes Senate",
    source: "Il Sole 24 Ore",
    source_category: "Financial News",
    published: "2d ago",
    relevance: "medium",
    impact: "positive",
    category: "Policy",
    sector: "Infrastructure",
    geography: "Italy",
    affected_holdings: ["Adriatic Infrastructure Fund"],
    summary:
      "Italy's Senate approved a €28 billion infrastructure investment bill, including €4.2 billion specifically allocated for port modernization and coastal transport infrastructure in the Adriatic and Ionian regions. Projects qualifying for co-financing must commence by December 2026.",
    ai_analysis:
      "Adriatic Infrastructure Fund's two concession assets in the Trieste port complex could qualify for co-financing under the bill's coastal infrastructure provisions. Potential to access non-dilutive grant funding for Phase 2 expansion. The December 2026 commencement deadline aligns with the fund's current development timeline.",
    recommended_action: "Investigate",
    confidence: 76,
  },
  {
    id: "n7",
    headline: "Carbon Credit Prices Reach €85/tonne on EU ETS",
    source: "Carbon Pulse",
    source_category: "Market Data",
    published: "2d ago",
    relevance: "medium",
    impact: "positive",
    category: "Market",
    sector: "Carbon Markets",
    geography: "European Union",
    affected_holdings: ["Nordic Biomass Energy", "Helios Solar Portfolio Iberia"],
    summary:
      "EU Emissions Trading System (ETS) allowance prices touched €85/tonne for the first time, driven by stronger industrial output and tighter cap allocation ahead of the 2026 review. Voluntary carbon markets also firmed, with nature-based credits trading at $18-22/tonne.",
    ai_analysis:
      "Nordic Biomass Energy generates approximately 85,000 EUAs annually as a bioenergy facility eligible for EU ETS free allocations. At €85/tonne, annual EUA revenue has increased by €7.65M versus the underwriting assumption of €55/tonne. Recommend reviewing whether the hedging policy for EUA sales is still optimal at current price levels.",
    recommended_action: "Monitor",
    confidence: 92,
  },
  {
    id: "n8",
    headline: "Swiss Hydropower Concession Renewals Face Political Scrutiny",
    source: "Neue Zürcher Zeitung",
    source_category: "Financial News",
    published: "3d ago",
    relevance: "medium",
    impact: "negative",
    category: "Regulatory",
    sector: "Hydropower",
    geography: "Switzerland",
    affected_holdings: ["Alpine Hydro Concessions"],
    summary:
      "A parliamentary motion filed by the Swiss Green Party seeks to impose stricter minimum ecological flow requirements and community benefit sharing on hydro concession renewals. The motion targets concessions up for renewal between 2026 and 2032 and could affect plants representing 4 GW of installed capacity.",
    ai_analysis:
      "Alpine Hydro Concessions has two plants (Simplon 180 MW, Graubünden 95 MW) with concession renewal windows in 2027-2028, directly in scope. New minimum ecological flow requirements could reduce annual generation by an estimated 6-9%. The motion has cross-party support but requires Federal Council approval — estimated 40% probability of adoption in current form. Recommend engaging legal counsel to assess renewal strategy and community benefit structures.",
    recommended_action: "Investigate",
    confidence: 71,
  },
];

const MARKET_METRICS: MarketMetric[] = [
  { id: "m1", label: "EU ETS Carbon", value: "€85.20", change_pct: 3.2, unit: "/tonne", favorable_direction: "up", category: "Carbon" },
  { id: "m2", label: "Solar PPA (Spain)", value: "€42.50", change_pct: -1.1, unit: "/MWh", favorable_direction: "up", category: "Power" },
  { id: "m3", label: "Wind PPA (Nordics)", value: "€38.80", change_pct: 0.5, unit: "/MWh", favorable_direction: "up", category: "Power" },
  { id: "m4", label: "ECB Rate", value: "2.50", change_pct: 0, unit: "%", favorable_direction: "down", category: "Rates" },
  { id: "m5", label: "Solar Module", value: "$0.11", change_pct: -4.3, unit: "/Wp", favorable_direction: "down", category: "Equipment" },
  { id: "m6", label: "Lithium Carbonate", value: "$12,400", change_pct: -8.1, unit: "/t", favorable_direction: "down", category: "Commodities" },
];

const REGULATORY_ITEMS: RegulatoryItem[] = [
  {
    id: "r1",
    name: "REPowerEU Permitting Revision",
    jurisdiction: "European Union",
    status: "Adopted",
    effective_date: "Jul 2026",
    sector: "Solar & Wind",
    severity: "Critical",
    summary:
      "Streamlines permitting to under 2 years for new renewables, 1 year for repowering. Introduces 'go-to areas' with pre-assessed environmental suitability. Binding on all EU member states.",
    affected_holdings: ["Helios Solar Portfolio Iberia", "Nordvik Wind Farm", "Thames Clean Energy Hub"],
  },
  {
    id: "r2",
    name: "UK Grid Code Reform — NGESO",
    jurisdiction: "United Kingdom",
    status: "Consultation",
    effective_date: "Deadline Apr 2026",
    sector: "Wind & Storage",
    severity: "Important",
    summary:
      "Ofgem and NGESO are consulting on revised grid code requirements for inverter-based resources. Proposed changes to fault ride-through and reactive power requirements may require hardware upgrades for pre-2020 assets.",
    affected_holdings: ["Thames Clean Energy Hub"],
  },
  {
    id: "r3",
    name: "SFDR Level 2 — Revised PAI Templates",
    jurisdiction: "European Union",
    status: "Proposed",
    effective_date: "2027 (expected)",
    sector: "All — Reporting",
    severity: "Informational",
    summary:
      "European Commission is reviewing SFDR Level 2 PAI disclosure templates. Proposed changes include 4 new mandatory PAI indicators for biodiversity and 2 for social factors. Consultation period runs until June 2026.",
    affected_holdings: ["Helios Solar Portfolio Iberia", "Nordvik Wind Farm", "Adriatic Infrastructure Fund", "Baltic BESS Grid Storage", "Alpine Hydro Concessions", "Nordic Biomass Energy", "Thames Clean Energy Hub"],
  },
];

const UPCOMING_DATES: UpcomingDate[] = [
  { id: "d1", title: "UK Grid Code Consultation Deadline", date: "15 Apr 2026", type: "Consultation deadline", urgency: "high", regulation: "NGESO Grid Code Reform" },
  { id: "d2", title: "SFDR PAI Consultation Closes", date: "30 Jun 2026", type: "Consultation deadline", urgency: "medium", regulation: "SFDR Level 2 Revision" },
  { id: "d3", title: "REPowerEU Permitting — Effective Date", date: "1 Jul 2026", type: "Effective date", urgency: "medium", regulation: "REPowerEU Permitting Revision" },
  { id: "d4", title: "Italian Infrastructure Bill — Commencement Deadline", date: "31 Dec 2026", type: "Project deadline", urgency: "low", regulation: "Italian Infrastructure Spending Bill" },
];

const COMPARABLE_TRANSACTIONS: ComparableTransaction[] = [
  { id: "t1", buyer: "Brookfield Asset Mgmt", seller: "Enel Green Power", asset: "850 MW Spanish Solar Portfolio", sector: "Solar", geography: "Spain", deal_size: "€1.2B", multiple: "11.4x EBITDA", date: "Feb 2026" },
  { id: "t2", buyer: "Copenhagen Infrastructure Partners", seller: "Equinor", asset: "300 MW Norwegian Offshore Wind", sector: "Wind", geography: "Norway", deal_size: "€780M", multiple: "12.1x EBITDA", date: "Jan 2026" },
  { id: "t3", buyer: "BlackRock Infrastructure", seller: "Enel X", asset: "400 MWh Baltic BESS Portfolio", sector: "Storage", geography: "Lithuania / Latvia", deal_size: "€220M", multiple: null, date: "Jan 2026" },
  { id: "t4", buyer: "DIF Capital Partners", seller: "TotalEnergies", asset: "UK Biomass CHP Plants (3 assets)", sector: "Biomass", geography: "United Kingdom", deal_size: "€340M", multiple: "9.8x EBITDA", date: "Dec 2025" },
];

const WATCHLIST_ITEMS: WatchlistItem[] = [
  { id: "w1", name: "Spanish Solar Auctions", criteria: "Keywords: Spain, solar auction, licitación solar", type: "keyword", active: true, alerts_today: 2 },
  { id: "w2", name: "Nordvik Wind — Grid Connection", criteria: "Statnett + connection queue + northern Norway", type: "keyword", active: true, alerts_today: 1 },
  { id: "w3", name: "EU ETS Carbon Price", criteria: "Price threshold: above €80/tonne", type: "price", active: true, alerts_today: 1 },
  { id: "w4", name: "SFDR Level 2 Updates", criteria: "Regulation: SFDR, sustainable finance disclosure", type: "regulation", active: false, alerts_today: 0 },
];

const AI_ACTIONS = [
  { id: "a1", label: "Generate Weekly Portfolio Brief", description: "Comprehensive summary of market developments affecting the portfolio", icon: FileText, color: "text-blue-600 bg-blue-50" },
  { id: "a2", label: "Run Sector Deep Dive", description: "Detailed analysis of a specific sector's outlook and portfolio exposure", icon: Layers, color: "text-purple-600 bg-purple-50" },
  { id: "a3", label: "Analyze Regulatory Impact", description: "Assess how a specific regulation affects portfolio holdings", icon: Shield, color: "text-amber-600 bg-amber-50" },
  { id: "a4", label: "Compare Market Conditions", description: "Current market environment vs 6 and 12 months ago", icon: BarChart2, color: "text-green-600 bg-green-50" },
  { id: "a5", label: "Ask Ralph About Markets", description: "Open Ralph AI with market context pre-loaded for questions", icon: MessageSquare, color: "text-indigo-600 bg-indigo-50" },
];

const SOURCES = [
  { category: "Financial News", examples: "Reuters, Bloomberg, Financial Times, Wall Street Journal", icon: FileText, count: 42 },
  { category: "Government & Regulatory", examples: "EU Official Journal, national regulators, energy ministries", icon: Building2, count: 38 },
  { category: "Industry Publications", examples: "BloombergNEF, Wood Mackenzie, Montel, Carbon Pulse", icon: BookOpen, count: 27 },
  { category: "Market Data", examples: "ICE, EEX, EPEX, Nord Pool, auction platforms", icon: BarChart2, count: 19 },
  { category: "ESG & Sustainability", examples: "MSCI ESG, Sustainalytics, CDP, GRESB", icon: Globe, count: 14 },
];

// ── Helper components ─────────────────────────────────────────────────────────

function relevanceBadge(r: "high" | "medium" | "low") {
  if (r === "high") return <Badge variant="error">HIGH</Badge>;
  if (r === "medium") return <Badge variant="warning">MEDIUM</Badge>;
  return <Badge variant="neutral">LOW</Badge>;
}

function impactBadge(impact: "positive" | "negative" | "neutral") {
  if (impact === "positive") return <Badge variant="success">Positive</Badge>;
  if (impact === "negative") return <Badge variant="error">Negative</Badge>;
  return <Badge variant="neutral">Neutral</Badge>;
}

function regulatoryStatusBadge(status: RegulatoryItem["status"]) {
  if (status === "Adopted" || status === "Effective") return <Badge variant="success">{status}</Badge>;
  if (status === "Consultation") return <Badge variant="warning">{status}</Badge>;
  return <Badge variant="info">{status}</Badge>;
}

function regulatorySeverityBadge(severity: RegulatoryItem["severity"]) {
  if (severity === "Critical") return <Badge variant="error">Critical</Badge>;
  if (severity === "Important") return <Badge variant="warning">Important</Badge>;
  return <Badge variant="info">Informational</Badge>;
}

function urgencyColor(urgency: "high" | "medium" | "low") {
  if (urgency === "high") return "border-l-red-500 bg-red-50";
  if (urgency === "medium") return "border-l-amber-500 bg-amber-50";
  return "border-l-gray-300 bg-gray-50";
}

function MetricChangeIcon({ change_pct, favorable_direction }: { change_pct: number; favorable_direction: "up" | "down" }) {
  const isFavorable = favorable_direction === "up" ? change_pct > 0 : change_pct < 0;
  if (change_pct === 0) return <Minus className="h-3 w-3 text-gray-400" />;
  const color = isFavorable ? "text-green-600" : "text-red-500";
  return change_pct > 0
    ? <TrendingUp className={`h-3 w-3 ${color}`} />
    : <TrendingDown className={`h-3 w-3 ${color}`} />;
}

function metricChangeColor(change_pct: number, favorable_direction: "up" | "down") {
  if (change_pct === 0) return "text-gray-500";
  const isFavorable = favorable_direction === "up" ? change_pct > 0 : change_pct < 0;
  return isFavorable ? "text-green-600" : "text-red-500";
}

// ── News Item Card ────────────────────────────────────────────────────────────

function NewsCard({ item }: { item: NewsItem }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Card className={`border-l-4 ${item.impact === "positive" ? "border-l-green-400" : item.impact === "negative" ? "border-l-red-400" : "border-l-gray-300"}`}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs font-semibold text-gray-500">{item.source}</span>
              <span className="text-xs text-gray-400">{item.published}</span>
              <Badge variant="neutral">{item.category}</Badge>
            </div>
            <p className="text-sm font-semibold text-gray-900 leading-snug">{item.headline}</p>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            {relevanceBadge(item.relevance)}
            {impactBadge(item.impact)}
          </div>
        </div>
        <p className="text-xs text-gray-600 leading-relaxed">{item.summary}</p>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-gray-400">Affects:</span>
          {item.affected_holdings.map((h) => (
            <span key={h} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium">{h}</span>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{item.sector}</span>
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{item.geography}</span>
        </div>
        <button
          className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {expanded ? "Hide" : "Show"} AI Analysis
        </button>
        {expanded && (
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 space-y-2">
            <p className="text-xs font-semibold text-blue-800 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5" /> AI Analysis
            </p>
            <p className="text-xs text-blue-900 leading-relaxed">{item.ai_analysis}</p>
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-blue-700">Recommended: <strong>{item.recommended_action}</strong></span>
              <span className="text-xs text-blue-600">Confidence: {item.confidence}%</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Economic Series (kept from original) ─────────────────────────────────────

function EcoIndicatorCard({ indicator }: { indicator: MarketDataSummary }) {
  const changeColor = changePctColor(indicator.change_pct, indicator.series_id);
  const isUp = indicator.change_pct !== null && indicator.change_pct > 0;
  const isDown = indicator.change_pct !== null && indicator.change_pct < 0;
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-gray-500 truncate mb-1">{indicator.series_name}</p>
        <p className="text-2xl font-semibold text-gray-900 tabular-nums">
          {formatIndicatorValue(indicator.latest_value, indicator.unit)}
        </p>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-gray-400">as of {indicator.latest_date}</span>
          {indicator.change_pct !== null ? (
            <span className={`flex items-center gap-0.5 text-xs font-medium ${changeColor}`}>
              {isUp ? <TrendingUp className="h-3 w-3" /> : isDown ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
              {Math.abs(indicator.change_pct).toFixed(3)}%
            </span>
          ) : (
            <span className="text-xs text-gray-400">no change</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function EcoSparkline({ points }: { points: ExternalDataPoint[] }) {
  if (points.length < 2) return null;
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 200; const H = 40;
  const step = W / (points.length - 1);
  const path = points.map((p, i) => {
    const x = i * step;
    const y = H - ((p.value - min) / range) * H;
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  const lastY = H - ((values[values.length - 1] - min) / range) * H;
  const isUp = values[values.length - 1] >= values[0];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-10" preserveAspectRatio="none">
      <path d={path} fill="none" stroke={isUp ? "#10b981" : "#ef4444"} strokeWidth="1.5" />
      <circle cx={W} cy={lastY} r="2" fill={isUp ? "#10b981" : "#ef4444"} />
    </svg>
  );
}

function EcoSeriesCard({ source, seriesId, seriesName, unit }: { source: string; seriesId: string; seriesName: string; unit: string | null }) {
  const { data: points, isLoading } = useSeriesHistory(source, seriesId, 90);
  const latest = points?.[points.length - 1];
  const oldest = points?.[0];
  const changePct = oldest && latest && oldest.value !== 0 ? ((latest.value - oldest.value) / Math.abs(oldest.value)) * 100 : null;
  return (
    <Card>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-medium text-gray-700 leading-tight">{seriesName}</p>
            <p className="text-xs text-gray-400">{source.toUpperCase()} · {seriesId}</p>
          </div>
          {latest && <span className="text-sm font-semibold text-gray-900 tabular-nums shrink-0">{formatIndicatorValue(latest.value, unit)}</span>}
        </div>
        {isLoading ? (
          <div className="h-10 flex items-center justify-center"><Loader2 className="h-4 w-4 animate-spin text-gray-400" /></div>
        ) : points && points.length > 1 ? (
          <EcoSparkline points={points} />
        ) : (
          <div className="h-10 flex items-center text-xs text-gray-400">No data</div>
        )}
        {changePct !== null && (
          <p className={`text-xs text-right ${changePctColor(changePct, seriesId)}`}>
            90d: {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function MarketDataPage() {
  const [activeSource, setActiveSource] = useState<string | null>(null);
  const [briefingGenerating, setBriefingGenerating] = useState(false);
  const [newsFilter, setNewsFilter] = useState<"all" | "positive" | "negative" | "neutral">("all");
  const [newsCategoryFilter, setNewsCategoryFilter] = useState<string>("all");
  const [newsSearch, setNewsSearch] = useState("");
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>(WATCHLIST_ITEMS);
  const [aiActionRunning, setAiActionRunning] = useState<string | null>(null);

  const { data: summary, isLoading: summaryLoading } = useMarketDataSummary();
  const { data: seriesGroups, isLoading: seriesLoading } = useMarketDataSeries();
  const { mutate: refresh, isPending: refreshing } = useRefreshMarketData();

  const availableSources = seriesGroups?.map((g) => g.source) ?? [];
  const filteredGroups = activeSource === null ? seriesGroups ?? [] : (seriesGroups ?? []).filter((g) => g.source === activeSource);

  const filteredNews = NEWS_ITEMS.filter((item) => {
    if (newsFilter !== "all" && item.impact !== newsFilter) return false;
    if (newsCategoryFilter !== "all" && item.category !== newsCategoryFilter) return false;
    if (newsSearch && !item.headline.toLowerCase().includes(newsSearch.toLowerCase()) && !item.summary.toLowerCase().includes(newsSearch.toLowerCase())) return false;
    return true;
  });

  const handleBriefingRefresh = () => {
    setBriefingGenerating(true);
    setTimeout(() => setBriefingGenerating(false), 2000);
  };

  const handleAiAction = (id: string) => {
    setAiActionRunning(id);
    setTimeout(() => setAiActionRunning(null), 2500);
  };

  const toggleWatchlist = (id: string) => {
    setWatchlistItems((prev) => prev.map((w) => w.id === id ? { ...w, active: !w.active } : w));
  };

  const NEWS_CATEGORIES = ["all", "Regulatory", "Market", "Policy", "Financial", "ESG", "Technology", "Transaction"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 rounded-lg">
          <BarChart2 className="h-6 w-6 text-primary-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Market Intelligence</h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            AI-powered market monitoring and portfolio-relevant intelligence briefings
          </p>
        </div>
      </div>

      <InfoBanner>
        <strong>Market Intelligence</strong> continuously monitors news, regulatory developments, market data, and industry
        trends relevant to your portfolio and investment strategy. Every alert is scored for portfolio relevance and analyzed
        for potential impact on your holdings. Intelligence is sourced from financial news, government publications, industry
        reports, and regulatory filings.
      </InfoBanner>

      <Tabs defaultValue="briefing">
        <TabsList>
          <TabsTrigger value="briefing">Briefing</TabsTrigger>
          <TabsTrigger value="news">News Feed</TabsTrigger>
          <TabsTrigger value="regulatory">Regulatory</TabsTrigger>
          <TabsTrigger value="market">Market Data</TabsTrigger>
          <TabsTrigger value="economic">Economic Series</TabsTrigger>
          <TabsTrigger value="watchlists">Watchlists</TabsTrigger>
        </TabsList>

        {/* ── TAB: Briefing ───────────────────────────────────────────────────── */}
        <TabsContent value="briefing" className="space-y-6 mt-6">
          {/* Daily brief hero */}
          <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <p className="text-xs font-semibold text-primary-600 uppercase tracking-wide mb-1">Today&apos;s Portfolio Intelligence Brief</p>
                <h2 className="text-lg font-bold text-neutral-900">AI Daily Summary</h2>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBriefingRefresh}
                  disabled={briefingGenerating}
                >
                  {briefingGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
                  Refresh
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleAiAction("brief")}
                  disabled={aiActionRunning === "brief"}
                >
                  {aiActionRunning === "brief" ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <FileText className="h-3.5 w-3.5 mr-1.5" />}
                  Generate Full Briefing
                </Button>
              </div>
            </div>
            {briefingGenerating ? (
              <div className="flex items-center gap-2 text-neutral-400 text-sm py-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                Scanning {(1247).toLocaleString()} sources for portfolio-relevant developments…
              </div>
            ) : (
              <p className="text-sm text-neutral-600 leading-relaxed">{BRIEFING_SUMMARY}</p>
            )}
            <p className="text-xs text-neutral-400 mt-3 flex items-center gap-1.5">
              <Clock className="h-3 w-3" /> Last updated: Today at 08:30 UTC
            </p>
            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
              {BRIEFING_STATS.map((stat) => (
                <div key={stat.label} className="bg-neutral-50 rounded-xl p-3 border border-neutral-100">
                  <stat.icon className="h-4 w-4 text-primary-500 mb-1" />
                  <p className="text-2xl font-bold text-neutral-900">{stat.value}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* AI Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-gray-500" /> AI Intelligence Actions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {AI_ACTIONS.map((action) => (
                  <button
                    key={action.id}
                    className="text-left p-4 rounded-xl border border-gray-200 bg-white hover:border-indigo-300 hover:shadow-sm transition-all"
                    onClick={() => handleAiAction(action.id)}
                    disabled={aiActionRunning === action.id}
                  >
                    <div className={`inline-flex p-2 rounded-lg mb-3 ${action.color}`}>
                      {aiActionRunning === action.id
                        ? <Loader2 className="h-4 w-4 animate-spin" />
                        : <action.icon className="h-4 w-4" />}
                    </div>
                    <p className="text-sm font-semibold text-gray-900">{action.label}</p>
                    <p className="text-xs text-gray-500 mt-1">{action.description}</p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Sources transparency */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Globe className="h-4 w-4 text-gray-500" /> Intelligence Sources
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {SOURCES.map((src) => (
                  <div key={src.category} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <src.icon className="h-3.5 w-3.5 text-gray-500" />
                      <p className="text-xs font-semibold text-gray-800">{src.category}</p>
                      <span className="ml-auto text-xs text-gray-400">{src.count} sources</span>
                    </div>
                    <p className="text-xs text-gray-500">{src.examples}</p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3 flex items-center gap-1.5">
                <Clock className="h-3 w-3" /> Sources last checked: Today at 08:30 UTC ·{" "}
                <span className="font-medium text-gray-600">140 total sources monitored</span> ·
                Intelligence is AI-curated — all items are scored for portfolio relevance before surfacing.
              </p>
            </CardContent>
          </Card>

          <AIFeedback taskType="market-intelligence-briefing" />
        </TabsContent>

        {/* ── TAB: News Feed ─────────────────────────────────────────────────── */}
        <TabsContent value="news" className="space-y-4 mt-6">
          {/* Controls */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
              <input
                type="text"
                placeholder="Search intelligence…"
                value={newsSearch}
                onChange={(e) => setNewsSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-3.5 w-3.5 text-gray-400 shrink-0" />
              {(["all", "positive", "negative", "neutral"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setNewsFilter(f)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize transition-colors ${
                    newsFilter === f ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {f === "all" ? "All Impact" : f}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {NEWS_CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setNewsCategoryFilter(c)}
                className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-colors ${
                  newsCategoryFilter === c ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {c === "all" ? "All Categories" : c}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500">{filteredNews.length} items</p>
          <div className="space-y-3">
            {filteredNews.length === 0 ? (
              <EmptyState title="No matching items" description="Adjust your filters to see more intelligence." />
            ) : (
              filteredNews.map((item) => <NewsCard key={item.id} item={item} />)
            )}
          </div>
          <AIFeedback taskType="market-intelligence-news-feed" />
        </TabsContent>

        {/* ── TAB: Regulatory ───────────────────────────────────────────────── */}
        <TabsContent value="regulatory" className="space-y-6 mt-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Regulatory Alerts</h3>
            <div className="space-y-3">
              {REGULATORY_ITEMS.map((reg) => (
                <Card key={reg.id} className={`border-l-4 ${reg.severity === "Critical" ? "border-l-red-500" : reg.severity === "Important" ? "border-l-amber-500" : "border-l-blue-400"}`}>
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{reg.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-500">{reg.jurisdiction}</span>
                          <span className="text-xs text-gray-400">·</span>
                          <span className="text-xs text-gray-500">{reg.sector}</span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        {regulatoryStatusBadge(reg.status)}
                        {regulatorySeverityBadge(reg.severity)}
                      </div>
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed">{reg.summary}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs text-gray-400">Affects:</span>
                        {reg.affected_holdings.slice(0, 3).map((h) => (
                          <span key={h} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium">{h}</span>
                        ))}
                        {reg.affected_holdings.length > 3 && (
                          <span className="text-xs text-gray-400">+{reg.affected_holdings.length - 3} more</span>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 flex items-center gap-1"><Clock className="h-3 w-3" />{reg.effective_date}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Upcoming dates */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Upcoming Regulatory Dates</h3>
            <div className="space-y-2">
              {UPCOMING_DATES.map((d) => (
                <div key={d.id} className={`flex items-center gap-4 p-3 rounded-lg border-l-4 ${urgencyColor(d.urgency)}`}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{d.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{d.regulation} · {d.type}</p>
                  </div>
                  <span className="text-sm font-semibold text-gray-700 shrink-0">{d.date}</span>
                </div>
              ))}
            </div>
          </div>

          <AIFeedback taskType="market-intelligence-regulatory" />
        </TabsContent>

        {/* ── TAB: Market Data ──────────────────────────────────────────────── */}
        <TabsContent value="market" className="space-y-6 mt-6">
          {/* Key market metrics */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Key Market Indicators</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {MARKET_METRICS.map((m) => {
                const color = metricChangeColor(m.change_pct, m.favorable_direction);
                return (
                  <Card key={m.id}>
                    <CardContent className="p-4">
                      <p className="text-xs text-gray-500 truncate mb-1">{m.label}</p>
                      <p className="text-xl font-bold text-gray-900 tabular-nums">
                        {m.value}<span className="text-xs font-normal text-gray-400 ml-0.5">{m.unit}</span>
                      </p>
                      <div className="flex items-center gap-1 mt-2">
                        <MetricChangeIcon change_pct={m.change_pct} favorable_direction={m.favorable_direction} />
                        <span className={`text-xs font-medium ${color}`}>
                          {m.change_pct === 0 ? "Unchanged" : `${m.change_pct > 0 ? "+" : ""}${m.change_pct}%`}
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">{m.category}</span>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Comparable Transactions */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Comparable Transactions</h3>
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600">Asset</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600">Buyer</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600">Sector</th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-600">Geography</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-600">Deal Size</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-600">Multiple</th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-600">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {COMPARABLE_TRANSACTIONS.map((tx, i) => (
                        <tr key={tx.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}>
                          <td className="px-4 py-3 text-xs font-medium text-gray-900">{tx.asset}</td>
                          <td className="px-4 py-3 text-xs text-gray-600">{tx.buyer}</td>
                          <td className="px-4 py-3"><Badge variant="info">{tx.sector}</Badge></td>
                          <td className="px-4 py-3 text-xs text-gray-600">{tx.geography}</td>
                          <td className="px-4 py-3 text-xs font-semibold text-gray-900 text-right">{tx.deal_size}</td>
                          <td className="px-4 py-3 text-xs text-gray-600 text-right">{tx.multiple ?? "—"}</td>
                          <td className="px-4 py-3 text-xs text-gray-400 text-right">{tx.date}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          <AIFeedback taskType="market-intelligence-market-data" />
        </TabsContent>

        {/* ── TAB: Economic Series (compressed original) ───────────────────── */}
        <TabsContent value="economic" className="space-y-6 mt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-gray-700">Economic Data Series</h3>
              <p className="text-xs text-gray-400 mt-0.5">Historical economic data from FRED, World Bank, and ECB</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => refresh()} disabled={refreshing}>
              {refreshing ? <Loader2 className="h-3 w-3 animate-spin mr-1.5" /> : <RefreshCw className="h-3 w-3 mr-1.5" />}
              Refresh
            </Button>
          </div>

          {/* Key indicators */}
          {summaryLoading ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm"><Loader2 className="h-4 w-4 animate-spin" /> Loading indicators…</div>
          ) : !summary?.indicators.length ? (
            <EmptyState title="No indicators available" description="Run a data refresh to populate market indicators." />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {summary.indicators.map((ind) => (
                <EcoIndicatorCard key={`${ind.source}/${ind.series_id}`} indicator={ind} />
              ))}
            </div>
          )}

          {/* Source filter */}
          {availableSources.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-500">Source:</span>
              <button onClick={() => setActiveSource(null)} className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${activeSource === null ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>All</button>
              {availableSources.map((src) => (
                <button key={src} onClick={() => setActiveSource(src)} className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${activeSource === src ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
                  {SOURCE_LABELS[src] ?? src.toUpperCase()}
                </button>
              ))}
            </div>
          )}

          {/* Series grid */}
          {seriesLoading ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm"><Loader2 className="h-4 w-4 animate-spin" /> Loading series…</div>
          ) : filteredGroups.length === 0 ? (
            <EmptyState title="No data yet" description="Click Refresh to fetch FRED and World Bank data." />
          ) : (
            <div className="space-y-5">
              {filteredGroups.map((group) => (
                <div key={group.source}>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                    {SOURCE_LABELS[group.source] ?? group.source}
                    <span className="ml-2 text-gray-400 font-normal normal-case">{group.series.length} series</span>
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {group.series.map((s) => (
                      <EcoSeriesCard key={`${group.source}/${s.series_id}`} source={group.source} seriesId={s.series_id} seriesName={s.series_name} unit={s.unit} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── TAB: Watchlists ───────────────────────────────────────────────── */}
        <TabsContent value="watchlists" className="space-y-6 mt-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Custom Monitoring Alerts</h3>
            <Button size="sm" variant="outline">
              <Plus className="h-3.5 w-3.5 mr-1.5" /> Add Alert
            </Button>
          </div>

          <div className="space-y-3">
            {watchlistItems.map((item) => (
              <Card key={item.id} className={!item.active ? "opacity-60" : undefined}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-semibold text-gray-900">{item.name}</p>
                        <Badge variant={item.type === "regulation" ? "info" : item.type === "price" ? "warning" : "neutral"}>
                          {item.type}
                        </Badge>
                        {item.active && item.alerts_today > 0 && (
                          <Badge variant="error">{item.alerts_today} today</Badge>
                        )}
                      </div>
                      <p className="text-xs text-gray-500">{item.criteria}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${item.active ? "bg-indigo-600" : "bg-gray-200"}`}
                        onClick={() => toggleWatchlist(item.id)}
                      >
                        <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${item.active ? "translate-x-4.5" : "translate-x-0.5"}`} />
                      </button>
                      <button className="text-gray-400 hover:text-gray-600">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Notification preferences note */}
          <Card className="bg-blue-50 border-blue-100">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Bell className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-blue-900">Notification Preferences</p>
                  <p className="text-xs text-blue-700 mt-1">
                    Active watchlist alerts surface in the News Feed and are included in your daily briefing.
                    To receive email notifications, configure your digest preferences in{" "}
                    <span className="font-medium underline cursor-pointer">Account Settings → Digest</span>.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <AIFeedback taskType="market-intelligence-watchlists" />
        </TabsContent>
      </Tabs>
    </div>
  );
}
