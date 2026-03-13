/**
 * Mock data — fallback data for all React Query hooks when the API returns empty.
 * Real API data always takes precedence; this only fills empty states.
 *
 * Score conventions:
 *  - latest_signal_score / alley-score API: 0–10 raw (hooks multiply ×10 for display)
 *  - signal-score API (SignalScoreDetail): 0–10 raw for overall/dimension scores
 *  - investor signal score: 0–100
 */

import type { ProjectResponse } from "@/lib/projects";
import type {
  PortfolioScoreResponse,
  ProjectScoreDetailResponse,
} from "@/lib/alley-score";
import type {
  PortfolioResponse,
  PortfolioMetricsResponse,
  HoldingResponse,
  HoldingTotals,
  CashFlowEntry,
  AllocationResponse,
} from "@/lib/portfolio";
import type {
  SignalScoreDetail,
  GapsResponse,
  ScoreHistoryResponse,
} from "@/lib/signal-score";
import type { FiveDomainRisk, RiskDashboard, MonitoringAlert } from "@/lib/risk";
import type { DealPipeline, DiscoveryResponse } from "@/lib/deals";
import type { CompsListResponse } from "@/lib/comps";
import type { LPReport } from "@/lib/lp-reports";
import type { LegalDocumentListResponse } from "@/lib/legal";
import type { GeneratedReportListResponse, ReportTemplateListResponse } from "@/lib/reports";
import type { Watchlist, WatchlistAlert } from "@/lib/watchlists";
import type {
  NotificationListResponse,
} from "@/lib/notifications";
import type { ComplianceResponse } from "@/lib/compliance";
import type { ESGPortfolioSummaryResponse } from "@/lib/esg";
import type {
  InvestorSignalScore,
  BenchmarkData,
  TopMatchItem,
  ImprovementAction,
  ScoreFactorItem,
} from "@/lib/investor-signal-score";
import type { InvestorRecommendations } from "@/lib/matching";
import type {
  PipelineOverview,
  StageDistributionItem,
  ScoreDistributionItem,
  DocumentCompletenessItem,
} from "@/lib/alley-analytics";
import type { SavedSearch } from "@/lib/screener";
import type { AuditReport } from "@/lib/blockchain";
import type {
  ListingListResponse,
  RFQListResponse,
  TransactionListResponse,
} from "@/lib/marketplace";
import type {
  PortfolioImpactResponse,
  CarbonCreditListResponse,
  SDGGoal,
} from "@/lib/impact";

// ── Project IDs ──────────────────────────────────────────────────────────────

export const MOCK_IDS = {
  p1: "11111111-1111-1111-1111-111111111111",
  p2: "22222222-2222-2222-2222-222222222222",
  p3: "33333333-3333-3333-3333-333333333333",
  p4: "44444444-4444-4444-4444-444444444444",
  p5: "55555555-5555-5555-5555-555555555555",
  p6: "66666666-6666-6666-6666-666666666666",
  p7: "77777777-7777-7777-7777-777777777777",
  p8: "88888888-8888-8888-8888-888888888888",
  portfolio: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
};

// ── Projects ─────────────────────────────────────────────────────────────────

export const MOCK_PROJECTS: ProjectResponse[] = [
  {
    id: MOCK_IDS.p1,
    name: "Helios Solar Portfolio Iberia",
    slug: "helios-solar-portfolio-iberia",
    description: "Diversified solar portfolio across Spain and Portugal, comprising 12 utility-scale PV assets with long-term PPAs.",
    project_type: "solar",
    status: "operational",
    stage: "operational",
    geography_country: "ES",
    geography_region: "Iberian Peninsula",
    geography_coordinates: null,
    technology_details: { technology: "utility_scale_pv", tracker: "single_axis" },
    capacity_mw: "180",
    total_investment_required: "312000000",
    currency: "USD",
    target_close_date: null,
    cover_image_url: null,
    is_published: true,
    published_at: "2023-03-15T10:00:00Z",
    latest_signal_score: 9.2,
    created_at: "2023-01-10T09:00:00Z",
    updated_at: "2025-11-20T14:30:00Z",
  },
  {
    id: MOCK_IDS.p2,
    name: "Nordvik Wind Farm II",
    slug: "nordvik-wind-farm-ii",
    description: "Offshore wind expansion project off the Norwegian coast. 24 turbines, 15-year fixed-price CfD.",
    project_type: "wind",
    status: "active",
    stage: "construction",
    geography_country: "NO",
    geography_region: "Nordland",
    geography_coordinates: null,
    technology_details: { technology: "offshore_wind", turbines: 24 },
    capacity_mw: "120",
    total_investment_required: "180000000",
    currency: "USD",
    target_close_date: "2026-06-30",
    cover_image_url: null,
    is_published: true,
    published_at: "2024-02-01T08:00:00Z",
    latest_signal_score: 7.8,
    created_at: "2023-09-05T11:00:00Z",
    updated_at: "2025-12-10T16:00:00Z",
  },
  {
    id: MOCK_IDS.p3,
    name: "Adriatic Infrastructure Holdings",
    slug: "adriatic-infrastructure-holdings",
    description: "Portfolio of toll road, port, and logistics infrastructure assets across northern Italy.",
    project_type: "infrastructure",
    status: "operational",
    stage: "operational",
    geography_country: "IT",
    geography_region: "Northern Italy",
    geography_coordinates: null,
    technology_details: null,
    capacity_mw: null,
    total_investment_required: "245000000",
    currency: "USD",
    target_close_date: null,
    cover_image_url: null,
    is_published: true,
    published_at: "2022-11-01T09:00:00Z",
    latest_signal_score: 8.5,
    created_at: "2022-08-15T10:00:00Z",
    updated_at: "2025-10-05T12:00:00Z",
  },
  {
    id: MOCK_IDS.p4,
    name: "Baltic BESS Grid Storage",
    slug: "baltic-bess-grid-storage",
    description: "Battery energy storage system providing frequency regulation and capacity to the Lithuanian grid.",
    project_type: "storage",
    status: "active",
    stage: "development",
    geography_country: "LT",
    geography_region: "Kaunas Region",
    geography_coordinates: null,
    technology_details: { technology: "li_ion_bess", duration_hours: 4 },
    capacity_mw: "50",
    total_investment_required: "95000000",
    currency: "USD",
    target_close_date: "2026-12-31",
    cover_image_url: null,
    is_published: true,
    published_at: "2024-05-20T10:00:00Z",
    latest_signal_score: 6.3,
    created_at: "2024-01-10T09:00:00Z",
    updated_at: "2025-11-15T10:00:00Z",
  },
  {
    id: MOCK_IDS.p5,
    name: "Alpine Hydro Partners",
    slug: "alpine-hydro-partners",
    description: "Run-of-river and reservoir hydropower portfolio in the Swiss Alps. Fully operational with 40-year water rights.",
    project_type: "hydro",
    status: "operational",
    stage: "operational",
    geography_country: "CH",
    geography_region: "Valais & Graubünden",
    geography_coordinates: null,
    technology_details: { technology: "run_of_river", water_rights_years: 40 },
    capacity_mw: "320",
    total_investment_required: "420000000",
    currency: "USD",
    target_close_date: null,
    cover_image_url: null,
    is_published: true,
    published_at: "2021-06-01T08:00:00Z",
    latest_signal_score: 8.8,
    created_at: "2021-03-20T10:00:00Z",
    updated_at: "2025-09-30T11:00:00Z",
  },
  {
    id: MOCK_IDS.p6,
    name: "Sahara CSP Development",
    slug: "sahara-csp-development",
    description: "Concentrated solar power plant with 8-hour thermal storage in Morocco's Draa-Tafilalet region.",
    project_type: "solar",
    status: "active",
    stage: "concept",
    geography_country: "MA",
    geography_region: "Draa-Tafilalet",
    geography_coordinates: null,
    technology_details: { technology: "csp_parabolic_trough", storage_hours: 8 },
    capacity_mw: "400",
    total_investment_required: "560000000",
    currency: "USD",
    target_close_date: "2028-12-31",
    cover_image_url: null,
    is_published: true,
    published_at: "2025-01-15T09:00:00Z",
    latest_signal_score: 4.7,
    created_at: "2024-10-01T10:00:00Z",
    updated_at: "2025-12-01T09:00:00Z",
  },
  {
    id: MOCK_IDS.p7,
    name: "Nordic Biomass Energy",
    slug: "nordic-biomass-energy",
    description: "Sustainable biomass CHP plant in Sweden using certified forest residues for heat and power.",
    project_type: "biomass",
    status: "active",
    stage: "development",
    geography_country: "SE",
    geography_region: "Dalarna",
    geography_coordinates: null,
    technology_details: { technology: "chp_biomass", feedstock: "forest_residues" },
    capacity_mw: "45",
    total_investment_required: "75000000",
    currency: "USD",
    target_close_date: "2027-03-31",
    cover_image_url: null,
    is_published: true,
    published_at: "2024-07-10T10:00:00Z",
    latest_signal_score: 7.1,
    created_at: "2024-04-01T09:00:00Z",
    updated_at: "2025-11-28T14:00:00Z",
  },
  {
    id: MOCK_IDS.p8,
    name: "Thames Clean Energy Hub",
    slug: "thames-clean-energy-hub",
    description: "Floating offshore wind pilot and hydrogen production facility in the Thames Estuary.",
    project_type: "wind",
    status: "active",
    stage: "development",
    geography_country: "GB",
    geography_region: "Thames Estuary",
    geography_coordinates: null,
    technology_details: { technology: "floating_offshore_wind", hydrogen: true },
    capacity_mw: "150",
    total_investment_required: "290000000",
    currency: "USD",
    target_close_date: "2027-09-30",
    cover_image_url: null,
    is_published: true,
    published_at: "2024-09-01T09:00:00Z",
    latest_signal_score: 5.5,
    created_at: "2024-06-15T10:00:00Z",
    updated_at: "2025-12-05T10:00:00Z",
  },
];

// ── Alley Score — Portfolio Overview ─────────────────────────────────────────
// Scores here are 0–10 raw (hooks multiply ×10 before rendering)

export const MOCK_PORTFOLIO_OVERVIEW: PortfolioScoreResponse = {
  stats: {
    avg_score: 7.24,
    total_projects: 8,
    investment_ready_count: 4,
  },
  projects: [
    { project_id: MOCK_IDS.p1, project_name: "Helios Solar Portfolio Iberia",   sector: "solar",          stage: "operational", score: 9.2, score_label: "Excellent", score_label_color: "green",  status: "Investment Ready", calculated_at: "2025-11-20T14:30:00Z", trend: "stable" },
    { project_id: MOCK_IDS.p2, project_name: "Nordvik Wind Farm II",            sector: "wind",           stage: "construction", score: 7.8, score_label: "Good",      score_label_color: "teal",   status: "Investment Ready", calculated_at: "2025-12-10T16:00:00Z", trend: "up" },
    { project_id: MOCK_IDS.p3, project_name: "Adriatic Infrastructure Holdings", sector: "infrastructure", stage: "operational", score: 8.5, score_label: "Strong",    score_label_color: "green",  status: "Investment Ready", calculated_at: "2025-10-05T12:00:00Z", trend: "stable" },
    { project_id: MOCK_IDS.p4, project_name: "Baltic BESS Grid Storage",        sector: "storage",        stage: "development",  score: 6.3, score_label: "Fair",       score_label_color: "amber",  status: "Needs Review",     calculated_at: "2025-11-15T10:00:00Z", trend: "up" },
    { project_id: MOCK_IDS.p5, project_name: "Alpine Hydro Partners",           sector: "hydro",          stage: "operational", score: 8.8, score_label: "Strong",    score_label_color: "green",  status: "Investment Ready", calculated_at: "2025-09-30T11:00:00Z", trend: "stable" },
    { project_id: MOCK_IDS.p6, project_name: "Sahara CSP Development",          sector: "solar",          stage: "concept",     score: 4.7, score_label: "Needs Review", score_label_color: "red", status: "In Progress",      calculated_at: "2025-12-01T09:00:00Z", trend: "new" },
    { project_id: MOCK_IDS.p7, project_name: "Nordic Biomass Energy",           sector: "biomass",        stage: "development",  score: 7.1, score_label: "Good",      score_label_color: "teal",   status: "Investment Ready", calculated_at: "2025-11-28T14:00:00Z", trend: "up" },
    { project_id: MOCK_IDS.p8, project_name: "Thames Clean Energy Hub",         sector: "wind",           stage: "development",  score: 5.5, score_label: "Fair",       score_label_color: "amber",  status: "Needs Review",     calculated_at: "2025-12-05T10:00:00Z", trend: "down" },
  ],
  improvement_factors: [
    { dimension: "Financial Planning",  avg_score: 6.2 },
    { dimension: "ESG & Impact",        avg_score: 7.8 },
    { dimension: "Risk Assessment",     avg_score: 5.9 },
    { dimension: "Market Opportunity",  avg_score: 7.1 },
  ],
  improvement_actions: [
    { action: "Upload financial model with 10-year projections", dimension: "Financial Planning", priority: "high", estimated_impact: 12 },
    { action: "Complete SFDR Article 9 impact metrics",           dimension: "ESG & Impact",       priority: "high", estimated_impact: 8 },
    { action: "Submit permitting documentation",                  dimension: "Risk Assessment",    priority: "medium", estimated_impact: 6 },
  ],
};

// ── Alley Score — Project Detail ─────────────────────────────────────────────
// Scores 0–10 raw (hook multiplies ×10)

function makeProjectScoreDetail(
  id: string,
  name: string,
  score: number,
  dims: [number, number, number, number, number, number]
): ProjectScoreDetailResponse {
  const [pv, fp, esg, ra, ts, mo] = dims;
  return {
    project_id: id,
    project_name: name,
    score,
    score_label: score >= 9 ? "Excellent" : score >= 8 ? "Strong" : score >= 7 ? "Good" : score >= 6 ? "Fair" : "Needs Review",
    score_label_color: score >= 9 ? "green" : score >= 8 ? "green" : score >= 7 ? "teal" : score >= 6 ? "amber" : "red",
    calculated_at: "2025-12-01T10:00:00Z",
    dimensions: [
      { id: "technical",          label: "Project Viability",   score: pv },
      { id: "financial",          label: "Financial Planning",  score: fp },
      { id: "esg",                label: "ESG & Impact",        score: esg },
      { id: "regulatory",         label: "Risk Assessment",     score: ra },
      { id: "team",               label: "Team Strength",       score: ts },
      { id: "market_opportunity", label: "Market Opportunity",  score: mo },
    ],
    readiness_indicators: [
      { label: "Business Plan uploaded",       met: score >= 7 },
      { label: "Financial model complete",     met: score >= 8 },
      { label: "ESG documentation in place",   met: score >= 6 },
      { label: "Legal structure confirmed",    met: score >= 7 },
    ],
    criteria_breakdown: [
      {
        dimension_id: "technical",
        dimension_name: "Project Viability",
        score: pv,
        criteria: [
          { id: "tech_maturity", name: "Technology Maturity",    status: pv >= 8 ? "met" : "partial", points_earned: Math.round(pv * 5), points_max: 10, evidence_note: "Technology is proven at scale" },
          { id: "site_control",  name: "Site Control",           status: pv >= 7 ? "met" : "partial", points_earned: Math.round(pv * 3), points_max: 8,  evidence_note: "Land lease agreements in place" },
          { id: "permits",       name: "Permitting Status",      status: pv >= 9 ? "met" : "partial", points_earned: Math.round(pv * 4), points_max: 7 },
        ],
      },
    ],
    gap_analysis: score < 8 ? [
      { dimension: "Financial Planning", action: "Upload 3-statement financial model", effort: "medium", timeline: "2–4 weeks", estimated_impact: 10 },
      { dimension: "Risk Assessment",    action: "Provide insurance coverage summary", effort: "low",    timeline: "1 week",   estimated_impact: 6 },
    ] : [],
    score_history: [
      { date: "2025-09-01", score: Math.max(0, score - 0.8) },
      { date: "2025-10-01", score: Math.max(0, score - 0.5) },
      { date: "2025-11-01", score: Math.max(0, score - 0.2) },
      { date: "2025-12-01", score },
    ],
  };
}

export const MOCK_PROJECT_SCORES: Record<string, ProjectScoreDetailResponse> = {
  [MOCK_IDS.p1]: makeProjectScoreDetail(MOCK_IDS.p1, "Helios Solar Portfolio Iberia",   9.2, [9.5, 9.0, 9.0, 9.2, 8.8, 9.5]),
  [MOCK_IDS.p2]: makeProjectScoreDetail(MOCK_IDS.p2, "Nordvik Wind Farm II",            7.8, [8.2, 7.5, 8.0, 7.5, 7.8, 7.8]),
  [MOCK_IDS.p3]: makeProjectScoreDetail(MOCK_IDS.p3, "Adriatic Infrastructure Holdings", 8.5, [8.8, 8.5, 8.0, 8.5, 8.5, 8.7]),
  [MOCK_IDS.p4]: makeProjectScoreDetail(MOCK_IDS.p4, "Baltic BESS Grid Storage",        6.3, [7.0, 5.5, 6.5, 6.0, 6.5, 6.3]),
  [MOCK_IDS.p5]: makeProjectScoreDetail(MOCK_IDS.p5, "Alpine Hydro Partners",           8.8, [9.0, 8.8, 8.5, 8.8, 9.0, 8.7]),
  [MOCK_IDS.p6]: makeProjectScoreDetail(MOCK_IDS.p6, "Sahara CSP Development",          4.7, [5.5, 4.0, 5.0, 4.5, 4.8, 4.5]),
  [MOCK_IDS.p7]: makeProjectScoreDetail(MOCK_IDS.p7, "Nordic Biomass Energy",           7.1, [7.5, 6.8, 8.0, 6.5, 7.0, 6.8]),
  [MOCK_IDS.p8]: makeProjectScoreDetail(MOCK_IDS.p8, "Thames Clean Energy Hub",         5.5, [6.0, 5.0, 6.0, 5.5, 5.5, 5.0]),
};

// ── Signal Score — Detail, Gaps, History ─────────────────────────────────────

function makeSignalDetail(projectId: string, score: number): SignalScoreDetail {
  const pv = score * 1.03, fp = score * 0.92, esg = score * 0.98;
  const ra = score * 0.90, ts = score * 0.97, mo = score * 1.02;
  return {
    id: `sd-${projectId}`,
    project_id: projectId,
    overall_score: score,
    dimensions: [
      {
        id: "technical", name: "Project Viability", weight: 0.25,
        score: Math.min(10, pv), completeness_score: 85, quality_score: 88,
        criteria: [
          { id: "tm", name: "Technology Maturity", max_points: 10, score: Math.min(10, pv * 0.9), has_document: true, ai_assessment: null },
          { id: "sc", name: "Site Control",        max_points: 8,  score: Math.min(8,  pv * 0.7), has_document: true, ai_assessment: null },
        ],
      },
      {
        id: "financial", name: "Financial Planning", weight: 0.20,
        score: Math.min(10, fp), completeness_score: 78, quality_score: 82,
        criteria: [
          { id: "fm", name: "Financial Model",     max_points: 10, score: Math.min(10, fp * 0.9), has_document: fp > 6, ai_assessment: null },
          { id: "pp", name: "Pricing / PPA",       max_points: 8,  score: Math.min(8,  fp * 0.8), has_document: fp > 7, ai_assessment: null },
        ],
      },
      {
        id: "esg", name: "ESG & Impact", weight: 0.20,
        score: Math.min(10, esg), completeness_score: 80, quality_score: 84,
        criteria: [
          { id: "cc", name: "Carbon Credentials",  max_points: 8, score: Math.min(8, esg * 0.9), has_document: true, ai_assessment: null },
          { id: "sd", name: "SDG Alignment",       max_points: 7, score: Math.min(7, esg * 0.8), has_document: true, ai_assessment: null },
        ],
      },
      {
        id: "regulatory", name: "Risk Assessment", weight: 0.15,
        score: Math.min(10, ra), completeness_score: 72, quality_score: 76,
        criteria: [
          { id: "rp", name: "Regulatory Permits",  max_points: 10, score: Math.min(10, ra * 0.9), has_document: ra > 6, ai_assessment: null },
        ],
      },
      {
        id: "team", name: "Team Strength", weight: 0.10,
        score: Math.min(10, ts), completeness_score: 90, quality_score: 88,
        criteria: [
          { id: "te", name: "Track Record",        max_points: 10, score: Math.min(10, ts * 0.95), has_document: true, ai_assessment: null },
        ],
      },
      {
        id: "market_opportunity", name: "Market Opportunity", weight: 0.10,
        score: Math.min(10, mo), completeness_score: 75, quality_score: 80,
        criteria: [
          { id: "ms", name: "Market Size",         max_points: 8, score: Math.min(8, mo * 0.85), has_document: true, ai_assessment: null },
        ],
      },
    ],
    improvement_guidance: {
      quick_wins: ["Upload latest audited accounts", "Add signed term sheet or LOI"],
      focus_area: score < 7 ? "Financial Planning" : null,
      high_priority_count: score < 7 ? 3 : 1,
      medium_priority_count: 2,
      estimated_max_gain: Math.round((10 - score) * 0.5 * 10) / 10,
      top_actions: [
        {
          dimension_id: "financial",
          dimension_name: "Financial Planning",
          action: "Upload 10-year financial model with sensitivity analysis",
          expected_gain: 0.8,
          effort: "medium",
          doc_types_needed: ["financial_model"],
        },
      ],
    },
    model_used: "claude-sonnet-4-6",
    version: 3,
    is_live: true,
    calculated_at: "2025-12-01T10:00:00Z",
  };
}

export const MOCK_SIGNAL_DETAILS: Record<string, SignalScoreDetail> = {
  [MOCK_IDS.p1]: makeSignalDetail(MOCK_IDS.p1, 9.2),
  [MOCK_IDS.p2]: makeSignalDetail(MOCK_IDS.p2, 7.8),
  [MOCK_IDS.p3]: makeSignalDetail(MOCK_IDS.p3, 8.5),
  [MOCK_IDS.p4]: makeSignalDetail(MOCK_IDS.p4, 6.3),
  [MOCK_IDS.p5]: makeSignalDetail(MOCK_IDS.p5, 8.8),
  [MOCK_IDS.p6]: makeSignalDetail(MOCK_IDS.p6, 4.7),
  [MOCK_IDS.p7]: makeSignalDetail(MOCK_IDS.p7, 7.1),
  [MOCK_IDS.p8]: makeSignalDetail(MOCK_IDS.p8, 5.5),
};

function makeGaps(projectId: string, score: number): GapsResponse {
  const gaps = score < 8 ? [
    {
      dimension_id: "financial",
      dimension_name: "Financial Planning",
      criterion_id: "fm",
      criterion_name: "Financial Model",
      current_score: score * 0.7,
      max_points: 10,
      priority: "high" as const,
      recommendation: "Upload a detailed 10-year financial model with IRR, DSCR, and sensitivity analysis.",
      relevant_doc_types: ["financial_model", "proforma"],
    },
    {
      dimension_id: "regulatory",
      dimension_name: "Risk Assessment",
      criterion_id: "rp",
      criterion_name: "Regulatory Permits",
      current_score: score * 0.6,
      max_points: 10,
      priority: score < 6 ? "high" as const : "medium" as const,
      recommendation: "Provide copies of all relevant environmental and planning permits.",
      relevant_doc_types: ["environmental_permit", "planning_consent"],
    },
  ] : [
    {
      dimension_id: "financial",
      dimension_name: "Financial Planning",
      criterion_id: "fm",
      criterion_name: "Financial Model Update",
      current_score: 8.5,
      max_points: 10,
      priority: "low" as const,
      recommendation: "Refresh financial model with latest cost data.",
      relevant_doc_types: ["financial_model"],
    },
  ];
  return { items: gaps, total: gaps.length };
}

export const MOCK_SIGNAL_GAPS: Record<string, GapsResponse> = {
  [MOCK_IDS.p1]: makeGaps(MOCK_IDS.p1, 9.2),
  [MOCK_IDS.p2]: makeGaps(MOCK_IDS.p2, 7.8),
  [MOCK_IDS.p3]: makeGaps(MOCK_IDS.p3, 8.5),
  [MOCK_IDS.p4]: makeGaps(MOCK_IDS.p4, 6.3),
  [MOCK_IDS.p5]: makeGaps(MOCK_IDS.p5, 8.8),
  [MOCK_IDS.p6]: makeGaps(MOCK_IDS.p6, 4.7),
  [MOCK_IDS.p7]: makeGaps(MOCK_IDS.p7, 7.1),
  [MOCK_IDS.p8]: makeGaps(MOCK_IDS.p8, 5.5),
};

function makeHistory(score: number): ScoreHistoryResponse {
  const base = Math.max(1, score - 1.2);
  return {
    items: [
      { version: 1, overall_score: base,           project_viability_score: base * 1.05, financial_planning_score: base * 0.90, esg_score: base * 0.95, risk_assessment_score: base * 0.88, team_strength_score: base * 1.0, market_opportunity_score: base * 0.98, is_live: false, calculated_at: "2025-06-01T10:00:00Z" },
      { version: 2, overall_score: base + 0.4,     project_viability_score: (base+0.4)*1.03, financial_planning_score: (base+0.4)*0.92, esg_score: (base+0.4)*0.97, risk_assessment_score: (base+0.4)*0.90, team_strength_score: (base+0.4)*1.0, market_opportunity_score: (base+0.4)*1.0, is_live: false, calculated_at: "2025-09-01T10:00:00Z" },
      { version: 3, overall_score: score - 0.3,    project_viability_score: (score-0.3)*1.02, financial_planning_score: (score-0.3)*0.93, esg_score: (score-0.3)*0.98, risk_assessment_score: (score-0.3)*0.91, team_strength_score: (score-0.3)*0.99, market_opportunity_score: (score-0.3)*1.01, is_live: false, calculated_at: "2025-11-01T10:00:00Z" },
      { version: 4, overall_score: score,          project_viability_score: score*1.03, financial_planning_score: score*0.92, esg_score: score*0.98, risk_assessment_score: score*0.90, team_strength_score: score*0.97, market_opportunity_score: score*1.02, is_live: true, calculated_at: "2025-12-01T10:00:00Z" },
    ],
  };
}

export const MOCK_SIGNAL_HISTORY: Record<string, ScoreHistoryResponse> = {
  [MOCK_IDS.p1]: makeHistory(9.2),
  [MOCK_IDS.p2]: makeHistory(7.8),
  [MOCK_IDS.p3]: makeHistory(8.5),
  [MOCK_IDS.p4]: makeHistory(6.3),
  [MOCK_IDS.p5]: makeHistory(8.8),
  [MOCK_IDS.p6]: makeHistory(4.7),
  [MOCK_IDS.p7]: makeHistory(7.1),
  [MOCK_IDS.p8]: makeHistory(5.5),
};

// ── Portfolio ─────────────────────────────────────────────────────────────────

export const MOCK_PORTFOLIO: PortfolioResponse = {
  id: MOCK_IDS.portfolio,
  name: "European Infrastructure Impact Fund",
  description: "Article 9 impact fund targeting renewable energy and sustainable infrastructure across Europe.",
  strategy: "impact_first",
  fund_type: "closed_end",
  vintage_year: 2022,
  target_aum: "750000000",
  current_aum: "412000000",
  currency: "EUR",
  sfdr_classification: "article_9",
  status: "investing",
  created_at: "2022-01-15T09:00:00Z",
  updated_at: "2025-12-01T10:00:00Z",
};

export const MOCK_PORTFOLIO_METRICS: PortfolioMetricsResponse = {
  irr_gross: "0.142",
  irr_net: "0.118",
  moic: "1.80",
  tvpi: "1.80",
  dpi: "0.40",
  rvpi: "1.40",
  total_invested: "285000000",
  total_distributions: "42000000",
  total_value: "412000000",
  carbon_reduction_tons: "185000",
  as_of_date: "2025-12-31",
};

const makeHolding = (
  id: string,
  portfolioId: string,
  projectId: string,
  name: string,
  type: "equity" | "project_finance" | "infrastructure",
  investDate: string,
  invested: string,
  current: string,
  moic: string,
  ownership: string
): HoldingResponse => ({
  id,
  portfolio_id: portfolioId,
  project_id: projectId,
  asset_name: name,
  asset_type: type,
  investment_date: investDate,
  investment_amount: invested,
  current_value: current,
  ownership_pct: ownership,
  currency: "EUR",
  status: "active",
  exit_date: null,
  exit_amount: null,
  notes: "",
  moic,
  created_at: investDate + "T09:00:00Z",
  updated_at: "2025-12-01T10:00:00Z",
});

const HOLDINGS_LIST: HoldingResponse[] = [
  makeHolding("hh-1", MOCK_IDS.portfolio, MOCK_IDS.p1, "Helios Solar Portfolio Iberia",   "equity",          "2022-03-15", "48000000",  "71040000",  "1.48", "15.4"),
  makeHolding("hh-2", MOCK_IDS.portfolio, MOCK_IDS.p2, "Nordvik Wind Farm II",            "project_finance", "2023-07-01", "32000000",  "38080000",  "1.19", "17.8"),
  makeHolding("hh-3", MOCK_IDS.portfolio, MOCK_IDS.p5, "Alpine Hydro Partners",           "equity",          "2022-09-01", "95000000",  "152000000", "1.60", "22.6"),
  makeHolding("hh-4", MOCK_IDS.portfolio, MOCK_IDS.p3, "Adriatic Infrastructure Holdings", "infrastructure",  "2023-01-20", "62000000",  "88040000",  "1.42", "25.3"),
  makeHolding("hh-5", MOCK_IDS.portfolio, MOCK_IDS.p7, "Nordic Biomass Energy",           "equity",          "2024-04-10", "18000000",  "21960000",  "1.22", "24.0"),
];

export const MOCK_HOLDINGS: { items: HoldingResponse[]; total: number; totals: HoldingTotals } = {
  items: HOLDINGS_LIST,
  total: HOLDINGS_LIST.length,
  totals: {
    total_invested: "255000000",
    total_current_value: "371120000",
    weighted_moic: "1.45",
  },
};

export const MOCK_CASH_FLOWS: { items: CashFlowEntry[] } = {
  items: [
    { date: "2022-03-15", amount: "-48000000",  type: "contribution", holding_name: "Helios Solar Portfolio Iberia" },
    { date: "2022-09-01", amount: "-95000000",  type: "contribution", holding_name: "Alpine Hydro Partners" },
    { date: "2023-01-20", amount: "-62000000",  type: "contribution", holding_name: "Adriatic Infrastructure Holdings" },
    { date: "2023-07-01", amount: "-32000000",  type: "contribution", holding_name: "Nordvik Wind Farm II" },
    { date: "2023-12-15", amount: "8500000",    type: "distribution", holding_name: "Helios Solar Portfolio Iberia" },
    { date: "2024-04-10", amount: "-18000000",  type: "contribution", holding_name: "Nordic Biomass Energy" },
    { date: "2024-06-30", amount: "12000000",   type: "distribution", holding_name: "Alpine Hydro Partners" },
    { date: "2024-12-15", amount: "14200000",   type: "distribution", holding_name: "Alpine Hydro Partners" },
    { date: "2025-06-30", amount: "7300000",    type: "distribution", holding_name: "Helios Solar Portfolio Iberia" },
  ],
};

export const MOCK_ALLOCATION: AllocationResponse = {
  by_sector: [
    { name: "Solar",          value: "48000000",  percentage: "18.8" },
    { name: "Hydropower",     value: "95000000",  percentage: "37.3" },
    { name: "Infrastructure", value: "62000000",  percentage: "24.3" },
    { name: "Wind",           value: "32000000",  percentage: "12.5" },
    { name: "Biomass",        value: "18000000",  percentage: "7.1" },
  ],
  by_geography: [
    { name: "Switzerland",    value: "95000000",  percentage: "37.3" },
    { name: "Spain",          value: "48000000",  percentage: "18.8" },
    { name: "Italy",          value: "62000000",  percentage: "24.3" },
    { name: "Norway",         value: "32000000",  percentage: "12.5" },
    { name: "Sweden",         value: "18000000",  percentage: "7.1" },
  ],
  by_stage: [
    { name: "Operational",    value: "205000000", percentage: "80.4" },
    { name: "Construction",   value: "32000000",  percentage: "12.5" },
    { name: "Development",    value: "18000000",  percentage: "7.1" },
  ],
  by_asset_type: [
    { name: "Equity",         value: "161000000", percentage: "63.1" },
    { name: "Infrastructure", value: "62000000",  percentage: "24.3" },
    { name: "Project Finance", value: "32000000", percentage: "12.6" },
  ],
};

// ── Risk ──────────────────────────────────────────────────────────────────────

export const MOCK_DOMAIN_RISK: FiveDomainRisk = {
  portfolio_id: MOCK_IDS.portfolio,
  overall_risk_score: 55,
  domains: [
    { domain: "market",     score: 28, label: "Low",           details: null, mitigation: null },
    { domain: "climate",    score: 55, label: "High",          details: null, mitigation: null },
    { domain: "regulatory", score: 32, label: "Moderate",      details: null, mitigation: null },
    { domain: "technology", score: 42, label: "Moderate-High", details: null, mitigation: null },
    { domain: "liquidity",  score: 18, label: "Low",           details: null, mitigation: null },
  ],
  monitoring_enabled: true,
  last_monitoring_check: "2025-12-07T08:00:00Z",
  active_alerts_count: 3,
  source: "stored",
};

export const MOCK_RISK_DASHBOARD: RiskDashboard = {
  portfolio_id: MOCK_IDS.portfolio,
  overall_risk_score: 45,
  heatmap: {
    cells: [
      { severity: "high",   probability: "possible",   count: 2, risk_ids: ["r1", "r2"] },
      { severity: "medium", probability: "likely",     count: 3, risk_ids: ["r3", "r4", "r5"] },
      { severity: "low",    probability: "very_likely", count: 4, risk_ids: ["r6", "r7", "r8", "r9"] },
    ],
    total_risks: 9,
  },
  top_risks: [],
  auto_identified: [
    { risk_type: "climate",    severity: "high",   probability: "possible",   description: "Physical climate risk to Iberian solar assets from extreme heat events." },
    { risk_type: "regulatory", severity: "medium", probability: "likely",     description: "SFDR regulatory updates may require additional PAI disclosures." },
    { risk_type: "market",     severity: "low",    probability: "unlikely",   description: "Energy price volatility risk partially hedged by long-term PPAs." },
  ],
  concentration: {
    portfolio_id: MOCK_IDS.portfolio,
    total_invested: 255000000,
    by_sector: [
      { label: "Hydropower", value: 95000000, pct: 37.3, is_concentrated: true },
      { label: "Solar",      value: 48000000, pct: 18.8, is_concentrated: false },
    ],
    by_geography: [
      { label: "Switzerland", value: 95000000, pct: 37.3, is_concentrated: true },
    ],
    by_counterparty: [],
    by_currency: [{ label: "USD", value: 255000000, pct: 100, is_concentrated: false }],
    concentration_flags: ["High hydro concentration (37%)", "High Switzerland exposure (37%)"],
  },
  risk_trend: [
    { date: "2025-06-01", risk_score: 52 },
    { date: "2025-09-01", risk_score: 49 },
    { date: "2025-12-01", risk_score: 45 },
  ],
};

export const MOCK_MONITORING_ALERTS: { items: MonitoringAlert[]; total: number } = {
  items: [
    {
      id: "alert-1", org_id: "org-1", portfolio_id: MOCK_IDS.portfolio, project_id: MOCK_IDS.p1,
      alert_type: "climate_event", severity: "high", domain: "climate",
      title: "Extreme Heat Warning — Iberia",
      description: "Spanish Met Office forecasts prolonged heat wave >42°C in Q1. Solar degradation risk elevated.",
      source_name: "AEMET", is_read: false, is_actioned: false, action_taken: null,
      created_at: "2025-12-06T08:00:00Z",
    },
    {
      id: "alert-2", org_id: "org-1", portfolio_id: MOCK_IDS.portfolio, project_id: null,
      alert_type: "regulatory_change", severity: "medium", domain: "regulatory",
      title: "SFDR Level 2 Update — New PAI Disclosures Required",
      description: "ESMA has published updated RTS requiring additional PAI metrics from Q1 2026.",
      source_name: "ESMA", is_read: false, is_actioned: false, action_taken: null,
      created_at: "2025-12-05T14:30:00Z",
    },
    {
      id: "alert-3", org_id: "org-1", portfolio_id: MOCK_IDS.portfolio, project_id: MOCK_IDS.p5,
      alert_type: "operational", severity: "low", domain: "technology",
      title: "Maintenance Window — Alpine Hydro",
      description: "Scheduled annual maintenance for Gorduno intake structure. Minor output reduction expected.",
      source_name: null, is_read: true, is_actioned: false, action_taken: null,
      created_at: "2025-12-03T10:00:00Z",
    },
  ],
  total: 3,
};

// ── Deal Pipeline ─────────────────────────────────────────────────────────────

const makeDealCard = (
  projectId: string,
  name: string,
  type: string,
  country: string,
  stage: string,
  eur: string,
  signal: number,
  alignment: number,
  status: string
) => ({
  project_id: projectId,
  match_id: `m-${projectId.slice(0, 8)}`,
  project_name: name,
  project_type: type,
  geography_country: country,
  stage,
  total_investment_required: eur,
  currency: "EUR",
  signal_score: signal,
  alignment_score: alignment,
  status,
  cover_image_url: null,
  updated_at: "2025-12-01T10:00:00Z",
});

export const MOCK_DEAL_PIPELINE: DealPipeline = {
  discovered: [
    makeDealCard(MOCK_IDS.p6, "Sahara CSP Development",   "solar",  "MA", "concept",     "560000000", 4.7, 62, "suggested"),
    makeDealCard(MOCK_IDS.p8, "Thames Clean Energy Hub",  "wind",   "GB", "development", "290000000", 5.5, 71, "suggested"),
    makeDealCard(MOCK_IDS.p4, "Baltic BESS Grid Storage", "storage","LT", "development", "95000000",  6.3, 68, "suggested"),
  ],
  screening: [
    makeDealCard(MOCK_IDS.p7, "Nordic Biomass Energy",           "biomass",        "SE", "development", "75000000",  7.1, 78, "viewed"),
    makeDealCard(MOCK_IDS.p3, "Adriatic Infrastructure Holdings", "infrastructure", "IT", "operational", "245000000", 8.5, 82, "viewed"),
  ],
  due_diligence: [
    makeDealCard(MOCK_IDS.p2, "Nordvik Wind Farm II", "wind", "NO", "construction", "180000000", 7.8, 85, "interested"),
  ],
  negotiation: [
    makeDealCard(MOCK_IDS.p5, "Alpine Hydro Partners", "hydro", "CH", "operational", "420000000", 8.8, 91, "intro_requested"),
  ],
  passed: [],
};

export const MOCK_DISCOVERY_DEALS: DiscoveryResponse = {
  items: MOCK_PROJECTS.slice(0, 6).map((p) => ({
    project_id: p.id,
    project_name: p.name,
    project_type: p.project_type,
    geography_country: p.geography_country,
    stage: p.stage,
    total_investment_required: p.total_investment_required,
    currency: p.currency,
    signal_score: p.latest_signal_score,
    alignment_score: 60 + Math.round((p.latest_signal_score ?? 5) * 4),
    alignment_reasons: ["Sector match", "Geography match", "Stage alignment"],
    cover_image_url: null,
    is_in_pipeline: [MOCK_IDS.p5, MOCK_IDS.p2].includes(p.id),
  })),
  total: 6,
  mandate_name: "European Renewables Fund Mandate",
};

// ── Comps ─────────────────────────────────────────────────────────────────────

export const MOCK_COMPS: CompsListResponse = {
  items: [
    { id: "c1",  deal_name: "Iberdrola Renewables Iberia Portfolio",       asset_type: "solar",          geography: "Spain",       country_code: "ES", close_year: 2023, deal_size_eur: 280000000,  capacity_mw: 155, ev_per_mw: 1.81, equity_irr: 9.8,  stage_at_close: "operational",         data_quality: "confirmed",  org_id: null },
    { id: "c2",  deal_name: "North Sea Offshore Wind JV",                  asset_type: "wind",           geography: "Norway",      country_code: "NO", close_year: 2024, deal_size_eur: 210000000,  capacity_mw: 130, ev_per_mw: 1.62, equity_irr: 11.2, stage_at_close: "construction",         data_quality: "confirmed",  org_id: null },
    { id: "c3",  deal_name: "Valpolicella Hydro Partners",                 asset_type: "hydro",          geography: "Italy",       country_code: "IT", close_year: 2022, deal_size_eur: 380000000,  capacity_mw: 290, ev_per_mw: 1.31, equity_irr: 8.5,  stage_at_close: "operational",         data_quality: "confirmed",  org_id: null },
    { id: "c4",  deal_name: "Nordic Grid Battery Storage I",               asset_type: "bess",           geography: "Sweden",      country_code: "SE", close_year: 2024, deal_size_eur: 85000000,   capacity_mw: 40,  ev_per_mw: 2.13, equity_irr: 13.5, stage_at_close: "development",          data_quality: "confirmed",  org_id: null },
    { id: "c5",  deal_name: "Alentejo Solar Farm",                         asset_type: "solar",          geography: "Portugal",    country_code: "PT", close_year: 2023, deal_size_eur: 145000000,  capacity_mw: 90,  ev_per_mw: 1.61, equity_irr: 10.1, stage_at_close: "operational",         data_quality: "confirmed",  org_id: null },
    { id: "c6",  deal_name: "Baltic Wind Energy Platform",                 asset_type: "wind",           geography: "Lithuania",   country_code: "LT", close_year: 2023, deal_size_eur: 175000000,  capacity_mw: 110, ev_per_mw: 1.59, equity_irr: 10.8, stage_at_close: "construction",         data_quality: "estimated",  org_id: null },
    { id: "c7",  deal_name: "Öresund Biomass CHP",                         asset_type: "biomass",        geography: "Denmark",     country_code: "DK", close_year: 2022, deal_size_eur: 62000000,   capacity_mw: 38,  ev_per_mw: 1.63, equity_irr: 9.2,  stage_at_close: "operational",         data_quality: "confirmed",  org_id: null },
    { id: "c8",  deal_name: "Swiss Alpine Pumped Hydro",                   asset_type: "hydro",          geography: "Switzerland", country_code: "CH", close_year: 2021, deal_size_eur: 520000000,  capacity_mw: 380, ev_per_mw: 1.37, equity_irr: 7.8,  stage_at_close: "operational",         data_quality: "confirmed",  org_id: null },
    { id: "c9",  deal_name: "UK Floating Wind Pilot",                      asset_type: "wind",           geography: "UK",          country_code: "GB", close_year: 2024, deal_size_eur: 220000000,  capacity_mw: 100, ev_per_mw: 2.20, equity_irr: 13.1, stage_at_close: "development",          data_quality: "estimated",  org_id: null },
    { id: "c10", deal_name: "Moroccan CSP Noor IV",                        asset_type: "solar",          geography: "Morocco",     country_code: "MA", close_year: 2022, deal_size_eur: 490000000,  capacity_mw: 350, ev_per_mw: 1.40, equity_irr: 8.9,  stage_at_close: "construction_ready",   data_quality: "estimated",  org_id: null },
  ],
  total: 10,
};

// ── LP Reports ────────────────────────────────────────────────────────────────

export const MOCK_LP_REPORTS: LPReport[] = [
  {
    id: "lpr-1", org_id: "org-1", portfolio_id: MOCK_IDS.portfolio,
    report_period: "Q4 2025", period_start: "2025-10-01", period_end: "2025-12-31",
    status: "approved", approved_by: "Investment Committee", approved_at: "2026-01-15T10:00:00Z",
    gross_irr: 0.142, net_irr: 0.118, tvpi: 1.80, dpi: 0.40, rvpi: 1.40, moic: 1.80,
    total_committed: 300000000, total_invested: 285000000, total_returned: 42000000, total_nav: 412000000,
    narrative: {
      executive_summary: "Q4 2025 saw strong performance across the portfolio, with Alpine Hydro delivering record generation and Helios Solar completing its expansion.",
      portfolio_commentary: "Operational assets performed above P50. Nordic Biomass Energy commenced construction on schedule.",
      market_outlook: "European energy markets remain supportive. Continued policy tailwinds from the EU Green Deal.",
      esg_highlights: "Total portfolio avoided 185,000 tCO₂e in 2025. SFDR Article 9 compliance maintained across all holdings.",
    },
    investments_data: HOLDINGS_LIST.map((h) => ({
      project_id: h.project_id ?? "",
      name: h.asset_name,
      committed: parseFloat(h.investment_amount),
      invested: parseFloat(h.investment_amount),
      nav: parseFloat(h.current_value),
      moic: parseFloat(h.moic ?? "1"),
    })),
    pdf_s3_key: null, generated_at: "2026-01-10T09:00:00Z", download_url: "#",
    created_at: "2026-01-08T10:00:00Z", updated_at: "2026-01-15T10:00:00Z",
  },
  {
    id: "lpr-2", org_id: "org-1", portfolio_id: MOCK_IDS.portfolio,
    report_period: "Q3 2025", period_start: "2025-07-01", period_end: "2025-09-30",
    status: "approved", approved_by: "Investment Committee", approved_at: "2025-10-20T10:00:00Z",
    gross_irr: 0.138, net_irr: 0.109, tvpi: 1.70, dpi: 0.30, rvpi: 1.40, moic: 1.70,
    total_committed: 300000000, total_invested: 267000000, total_returned: 28000000, total_nav: 388000000,
    narrative: null, investments_data: [],
    pdf_s3_key: null, generated_at: "2025-10-12T09:00:00Z", download_url: "#",
    created_at: "2025-10-10T10:00:00Z", updated_at: "2025-10-20T10:00:00Z",
  },
  {
    id: "lpr-3", org_id: "org-1", portfolio_id: MOCK_IDS.portfolio,
    report_period: "Q2 2025", period_start: "2025-04-01", period_end: "2025-06-30",
    status: "approved", approved_by: "Investment Committee", approved_at: "2025-07-18T10:00:00Z",
    gross_irr: 0.128, net_irr: 0.095, tvpi: 1.60, dpi: 0.20, rvpi: 1.40, moic: 1.60,
    total_committed: 300000000, total_invested: 255000000, total_returned: 14000000, total_nav: 362000000,
    narrative: null, investments_data: [],
    pdf_s3_key: null, generated_at: "2025-07-10T09:00:00Z", download_url: "#",
    created_at: "2025-07-08T10:00:00Z", updated_at: "2025-07-18T10:00:00Z",
  },
];

// ── Legal Documents ───────────────────────────────────────────────────────────

export const MOCK_LEGAL_DOCUMENTS: LegalDocumentListResponse = {
  items: [
    {
      id: "ld-1",
      title: "Alpine Hydro Partners — Investment Agreement",
      doc_type: "investment_agreement", status: "signed",
      template_id: "tpl-ia", project_id: MOCK_IDS.p5,
      content: "", s3_key: "legal/ld-1.pdf", version: 2,
      signed_date: "2026-03-01", expiry_date: null,
      questionnaire_answers: { pages: 48 }, generation_status: "completed", download_url: "#",
      created_at: "2026-02-20T09:00:00Z", updated_at: "2026-03-01T14:00:00Z",
    },
    {
      id: "ld-2",
      title: "Bavarian Biomass — Term Sheet",
      doc_type: "term_sheet", status: "draft",
      template_id: "tpl-ts", project_id: null,
      content: "", s3_key: null, version: 1,
      signed_date: null, expiry_date: null,
      questionnaire_answers: { pages: 12 }, generation_status: "completed", download_url: "#",
      created_at: "2026-03-05T10:00:00Z", updated_at: "2026-03-08T11:00:00Z",
    },
    {
      id: "ld-3",
      title: "SCR Fund I — LP Side Letter (Nordic Pension)",
      doc_type: "side_letter", status: "signed",
      template_id: null, project_id: null,
      content: "", s3_key: "legal/ld-3.pdf", version: 1,
      signed_date: "2026-01-15", expiry_date: null,
      questionnaire_answers: { pages: 8 }, generation_status: "completed", download_url: "#",
      created_at: "2026-01-10T09:00:00Z", updated_at: "2026-01-15T14:00:00Z",
    },
    {
      id: "ld-4",
      title: "Danube Hydro — NDA",
      doc_type: "nda", status: "signed",
      template_id: "tpl-nda", project_id: null,
      content: "", s3_key: "legal/ld-4.pdf", version: 1,
      signed_date: "2026-02-20", expiry_date: "2028-02-19",
      questionnaire_answers: { pages: 4 }, generation_status: "completed", download_url: "#",
      created_at: "2026-02-18T09:00:00Z", updated_at: "2026-02-20T14:00:00Z",
    },
    {
      id: "ld-5",
      title: "Aegean Wind Cluster — Due Diligence NDA",
      doc_type: "nda", status: "signed",
      template_id: "tpl-nda", project_id: null,
      content: "", s3_key: "legal/ld-5.pdf", version: 1,
      signed_date: "2026-02-15", expiry_date: "2028-02-14",
      questionnaire_answers: { pages: 4 }, generation_status: "completed", download_url: "#",
      created_at: "2026-02-12T09:00:00Z", updated_at: "2026-02-15T11:00:00Z",
    },
    {
      id: "ld-6",
      title: "Porto Solar Park — Initial Term Sheet",
      doc_type: "term_sheet", status: "draft",
      template_id: "tpl-ts", project_id: null,
      content: "", s3_key: null, version: 1,
      signed_date: null, expiry_date: null,
      questionnaire_answers: { pages: 6 }, generation_status: "pending", download_url: null,
      created_at: "2026-03-10T09:00:00Z", updated_at: "2026-03-10T09:00:00Z",
    },
  ],
  total: 6,
};

// ── Reports ───────────────────────────────────────────────────────────────────

export const MOCK_REPORTS: GeneratedReportListResponse = {
  items: [
    {
      id: "rpt-1", org_id: "org-1", template_id: "tpl-perf",
      title: "Portfolio Performance Report — Q4 2025",
      status: "ready", parameters: { output_format: "pdf", period: "Q4 2025", pages: 24 }, result_data: null,
      s3_key: "reports/rpt-1.pdf", error_message: null, generated_by: "Erik Lindström",
      completed_at: "2026-01-15T09:30:00Z", download_url: "#",
      template_name: "Quarterly Performance", created_at: "2026-01-15T09:00:00Z", updated_at: "2026-01-15T09:30:00Z",
    },
    {
      id: "rpt-2", org_id: "org-1", template_id: "tpl-esg",
      title: "ESG & Impact Report — H2 2025",
      status: "ready", parameters: { output_format: "pdf", period: "H2 2025", pages: 18 }, result_data: null,
      s3_key: "reports/rpt-2.pdf", error_message: null, generated_by: "Lars Petersen",
      completed_at: "2026-02-05T11:00:00Z", download_url: "#",
      template_name: "ESG Impact Report", created_at: "2026-02-05T10:00:00Z", updated_at: "2026-02-05T11:00:00Z",
    },
    {
      id: "rpt-3", org_id: "org-1", template_id: "tpl-risk",
      title: "Risk Assessment Summary — Q4 2025",
      status: "ready", parameters: { output_format: "pdf", period: "Q4 2025", pages: 12 }, result_data: null,
      s3_key: "reports/rpt-3.pdf", error_message: null, generated_by: "Anna Johansson",
      completed_at: "2026-01-20T10:00:00Z", download_url: "#",
      template_name: "Risk Assessment", created_at: "2026-01-20T09:30:00Z", updated_at: "2026-01-20T10:00:00Z",
    },
    {
      id: "rpt-4", org_id: "org-1", template_id: "tpl-lp",
      title: "LP Quarterly Report — Q4 2025",
      status: "ready", parameters: { output_format: "pdf", period: "Q4 2025", pages: 32 }, result_data: null,
      s3_key: "reports/rpt-4.pdf", error_message: null, generated_by: "Sofia Bergman",
      completed_at: "2026-01-15T14:00:00Z", download_url: "#",
      template_name: "LP Quarterly Report", created_at: "2026-01-15T13:30:00Z", updated_at: "2026-01-15T14:00:00Z",
    },
    {
      id: "rpt-5", org_id: "org-1", template_id: "tpl-deal",
      title: "Deal Flow Summary — Jan 2026",
      status: "ready", parameters: { output_format: "pdf", period: "Jan 2026", pages: 8 }, result_data: null,
      s3_key: "reports/rpt-5.pdf", error_message: null, generated_by: "Marco Rossi",
      completed_at: "2026-02-01T10:00:00Z", download_url: "#",
      template_name: "Deal Flow Summary", created_at: "2026-02-01T09:30:00Z", updated_at: "2026-02-01T10:00:00Z",
    },
  ],
  total: 5,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

export const MOCK_REPORT_TEMPLATES: ReportTemplateListResponse = {
  items: [
    {
      id: "tpl-perf", org_id: null, name: "Quarterly Performance Report",
      category: "performance", description: "Comprehensive quarterly performance report covering NAV, IRR, MOIC and DPI across portfolio holdings.",
      template_config: { supported_formats: ["pdf", "xlsx"], audience: "internal" },
      sections: null, is_system: true, version: 1,
      created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
    },
    {
      id: "tpl-esg", org_id: null, name: "ESG & Impact Report",
      category: "esg", description: "SFDR-aligned ESG report covering carbon avoided, SDG alignment, taxonomy classification and impact KPIs.",
      template_config: { supported_formats: ["pdf", "pptx"], audience: "lp" },
      sections: null, is_system: true, version: 1,
      created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
    },
    {
      id: "tpl-risk", org_id: null, name: "Risk Assessment Summary",
      category: "performance", description: "Risk scorecard covering market, credit, liquidity, ESG and regulatory risk dimensions per holding.",
      template_config: { supported_formats: ["pdf", "xlsx"], audience: "internal" },
      sections: null, is_system: true, version: 1,
      created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
    },
    {
      id: "tpl-lp", org_id: null, name: "LP Quarterly Report",
      category: "portfolio", description: "Investor-ready LP report with portfolio summary, project updates, financial highlights and ESG scorecard.",
      template_config: { supported_formats: ["pdf", "pptx"], audience: "lp" },
      sections: null, is_system: true, version: 1,
      created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
    },
    {
      id: "tpl-deal", org_id: null, name: "Deal Flow Summary",
      category: "project", description: "Monthly summary of pipeline activity — new projects screened, stage transitions and key metrics.",
      template_config: { supported_formats: ["pdf", "xlsx"], audience: "internal" },
      sections: null, is_system: true, version: 1,
      created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
    },
    {
      id: "tpl-comp", org_id: null, name: "SFDR Compliance Report",
      category: "compliance", description: "Annual SFDR Article 9 Principal Adverse Impact indicators and sustainable investment objective disclosure.",
      template_config: { supported_formats: ["pdf"], audience: "regulatory" },
      sections: null, is_system: true, version: 1,
      created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
    },
  ],
  total: 6,
};

// ── Watchlists ────────────────────────────────────────────────────────────────

export const MOCK_WATCHLISTS: Watchlist[] = [
  {
    id: "wl-1", name: "High Priority Watch",
    watch_type: "risk_alerts",
    criteria: { risk_score_below: 70, covenant_breach: true, holdings: [MOCK_IDS.p4, MOCK_IDS.p2] },
    alert_channels: ["in_app", "email"], alert_frequency: "immediate",
    is_active: true, total_alerts_sent: 8, unread_alerts: 3,
  },
  {
    id: "wl-2", name: "Pipeline Opportunities",
    watch_type: "score_changes",
    criteria: { min_score: 65, stages: ["due_diligence", "negotiation"], projects: ["Sahara CSP", "Danube Hydro", "Aegean Wind"] },
    alert_channels: ["in_app"], alert_frequency: "daily_digest",
    is_active: true, total_alerts_sent: 4, unread_alerts: 1,
  },
  {
    id: "wl-3", name: "ESG Performance",
    watch_type: "market_events",
    criteria: { esg_drop_threshold: 5, period: "month_over_month", holdings: "all" },
    alert_channels: ["in_app", "email"], alert_frequency: "weekly",
    is_active: true, total_alerts_sent: 2, unread_alerts: 0,
  },
];

export const MOCK_WATCHLIST_ALERTS: WatchlistAlert[] = [
  {
    id: "wa-1", watchlist_id: "wl-1", watchlist_name: "High Priority Watch",
    alert_type: "risk_flag", entity_type: "project", entity_id: MOCK_IDS.p4,
    data: { title: "Baltic BESS risk score dropped to 54 (was 61)", project_name: "Baltic BESS Grid Storage", old_score: 61, new_score: 54, severity: "high" },
    is_read: false, created_at: "2026-03-08T09:00:00Z",
  },
  {
    id: "wa-2", watchlist_id: "wl-1", watchlist_name: "High Priority Watch",
    alert_type: "risk_flag", entity_type: "project", entity_id: MOCK_IDS.p2,
    data: { title: "Baltic BESS grid connection permit still pending", project_name: "Baltic BESS Grid Storage", severity: "high" },
    is_read: false, created_at: "2026-03-01T10:00:00Z",
  },
  {
    id: "wa-3", watchlist_id: "wl-1", watchlist_name: "High Priority Watch",
    alert_type: "risk_flag", entity_type: "project", entity_id: MOCK_IDS.p2,
    data: { title: "Nordvik Wind — P90 yield assessment overdue", project_name: "Nordvik Wind Farm II", severity: "medium" },
    is_read: true, created_at: "2026-03-05T14:00:00Z",
  },
  {
    id: "wa-4", watchlist_id: "wl-2", watchlist_name: "Pipeline Opportunities",
    alert_type: "score_change", entity_type: "project", entity_id: "danube-hydro-1",
    data: { title: "Danube Hydro score updated to 72 (+4)", project_name: "Danube Hydro Expansion", old_score: 68, new_score: 72, severity: "low" },
    is_read: true, created_at: "2026-02-28T15:00:00Z",
  },
];

// ── Notifications ─────────────────────────────────────────────────────────────

export const MOCK_NOTIFICATIONS: NotificationListResponse = {
  items: [
    // Risk alerts (4)
    { id: "n1",  type: "warning",         title: "Baltic BESS risk score dropped to 54",          message: "Baltic BESS Grid Storage risk score fell from 61 to 54. Grid connection permit remains outstanding.",       link: `/projects/${MOCK_IDS.p4}`, is_read: false, created_at: "2026-03-08T09:00:00Z" },
    { id: "n2",  type: "warning",         title: "Nordvik Wind — covenant warning",               message: "Debt service coverage ratio approaching covenant threshold of 1.20x. Current DSCR: 1.24x.",                  link: `/projects/${MOCK_IDS.p2}`, is_read: false, created_at: "2026-03-07T14:30:00Z" },
    { id: "n3",  type: "info",            title: "Stress test results ready",                     message: "Portfolio stress test (interest rate +200bps scenario) complete. 2 holdings show elevated sensitivity.",      link: "/risk",                    is_read: false, created_at: "2026-03-06T11:00:00Z" },
    { id: "n4",  type: "warning",         title: "Market volatility alert",                       message: "European energy wholesale prices up 18% week-on-week. Review unhedged exposure across wind holdings.",        link: "/risk",                    is_read: true,  created_at: "2026-03-05T08:00:00Z" },
    // Deal updates (5)
    { id: "n5",  type: "action_required", title: "Bavarian Biomass term sheet ready for review",  message: "Draft term sheet for Bavarian Biomass Network (€15M) is ready. Please review and mark up by Mar 15.",        link: "/legal",                   is_read: false, created_at: "2026-03-08T10:00:00Z" },
    { id: "n6",  type: "info",            title: "Porto Solar initial screen complete",            message: "Porto Solar Park (€35M, Portugal) scored 81 — above mandate threshold. Recommend progressing to DD.",         link: "/deals",                   is_read: false, created_at: "2026-03-07T16:00:00Z" },
    { id: "n7",  type: "info",            title: "Danube Hydro DD 60% complete",                  message: "Due diligence for Danube Hydro Expansion is 60% complete. Technical report expected by Mar 20.",              link: "/deals",                   is_read: true,  created_at: "2026-03-05T14:00:00Z" },
    { id: "n8",  type: "info",            title: "Aegean Wind site visit confirmed",               message: "Site visit to Aegean Wind Cluster (Greece) confirmed for Mar 18–19. Logistics shared with team.",             link: "/deals",                   is_read: true,  created_at: "2026-03-04T09:00:00Z" },
    { id: "n9",  type: "info",            title: "New deal match: Iberian Offshore Wind",         message: "New project matching your mandate identified: Iberian Offshore Wind (€120M, Spain). Score: 74.",               link: "/deals",                   is_read: true,  created_at: "2026-03-01T11:00:00Z" },
    // LP activity (3)
    { id: "n10", type: "info",            title: "Nordic Pension viewed Q4 LP report",            message: "Nordic Pension Fund opened and spent 14 minutes reviewing your Q4 2025 LP Report.",                           link: "/lp-reports",              is_read: false, created_at: "2026-03-08T07:00:00Z" },
    { id: "n11", type: "action_required", title: "EIB requested co-investment details",           message: "EIB has requested supplementary information on the Alpine Hydro co-investment opportunity. Respond by Mar 20.", link: "/deals",                  is_read: false, created_at: "2026-03-06T15:00:00Z" },
    { id: "n12", type: "info",            title: "Dutch Infrastructure signed NDA",               message: "Dutch Infrastructure Fund has countersigned the NDA. You may now share deal room documents.",                  link: "/legal",                   is_read: true,  created_at: "2026-03-03T10:00:00Z" },
    // ESG/Compliance (3)
    { id: "n13", type: "action_required", title: "SFDR Annual Disclosure due in 18 days",         message: "SFDR Annual Disclosure deadline is Mar 31, 2026. Complete the PAI indicators to meet the deadline.",          link: "/compliance",              is_read: false, created_at: "2026-03-13T09:00:00Z" },
    { id: "n14", type: "info",            title: "EU Taxonomy alignment report draft ready",      message: "The EU Taxonomy Alignment Report draft for FY2025 is ready for review before submission Apr 30.",             link: "/reports",                 is_read: true,  created_at: "2026-03-10T14:00:00Z" },
    { id: "n15", type: "warning",         title: "ESG KPI tracking overdue",                     message: "Fund Level ESG KPI Tracking was due Mar 15. Please submit the monthly KPI data as soon as possible.",         link: "/compliance",              is_read: false, created_at: "2026-03-15T08:00:00Z" },
    // System (3)
    { id: "n16", type: "system",          title: "Signal scores refreshed for all holdings",      message: "Weekly signal score refresh complete. 7 holdings updated; Alpine Hydro remains highest at 91.",               link: `/projects/${MOCK_IDS.p5}`, is_read: true,  created_at: "2026-03-10T06:00:00Z" },
    { id: "n17", type: "system",          title: "Weekly digest sent to 5 LPs",                  message: "Weekly digest email dispatched to 5 LP contacts including Nordic Pension, EIB, and Dutch Infrastructure.",     link: null,                       is_read: true,  created_at: "2026-03-07T07:30:00Z" },
    { id: "n18", type: "system",          title: "New regulatory update available",               message: "ESMA published updated SFDR Q&A guidance (Mar 2026). Review the changes relevant to Article 9 funds.",        link: "/compliance",              is_read: true,  created_at: "2026-03-04T12:00:00Z" },
  ],
  total: 18,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

// ── Compliance ────────────────────────────────────────────────────────────────

export const MOCK_COMPLIANCE_DEADLINES: ComplianceResponse = {
  items: [
    {
      id: "cd-1", category: "sfdr", title: "SFDR Annual Disclosure",
      description: "Annual SFDR Article 9 Principal Adverse Impact indicators disclosure. Submit to ESMA by Mar 31.",
      jurisdiction: "EU", regulatory_body: "ESMA",
      due_date: "2026-03-31", recurrence: "annually", status: "in_progress", priority: "high",
      days_until_due: 18, is_overdue: false,
    },
    {
      id: "cd-2", category: "reporting", title: "Q1 2026 LP Report",
      description: "Quarterly LP report covering portfolio performance, NAV movements and project updates for Q1 2026.",
      jurisdiction: "EU", regulatory_body: null,
      due_date: "2026-04-15", recurrence: "quarterly", status: "upcoming", priority: "high",
      days_until_due: 33, is_overdue: false,
    },
    {
      id: "cd-3", category: "environmental", title: "EU Taxonomy Alignment Report",
      description: "Annual EU Taxonomy alignment assessment covering all 7 portfolio holdings against DNSH criteria.",
      jurisdiction: "EU", regulatory_body: "ESMA",
      due_date: "2026-04-30", recurrence: "annually", status: "upcoming", priority: "high",
      days_until_due: 48, is_overdue: false,
    },
    {
      id: "cd-4", category: "regulatory_filing", title: "AML/KYC Annual Review — Nordic Pension",
      description: "Annual KYC/AML review for Nordic Pension Fund LP. Update beneficial ownership and sanctions screening.",
      jurisdiction: "EU", regulatory_body: "Internal",
      due_date: "2026-03-20", recurrence: "annually", status: "in_progress", priority: "medium",
      days_until_due: 7, is_overdue: false,
    },
    {
      id: "cd-5", category: "reporting", title: "Helios Solar — ESG Monitoring Report",
      description: "Semi-annual ESG monitoring report for Helios Solar Portfolio Iberia per investment agreement covenants.",
      jurisdiction: "EU", regulatory_body: null,
      due_date: "2026-04-10", recurrence: "quarterly", status: "upcoming", priority: "medium",
      days_until_due: 28, is_overdue: false,
    },
    {
      id: "cd-6", category: "regulatory_filing", title: "AIFMD Reporting — BaFin",
      description: "Annual AIFMD transparency report submission to BaFin for German-domiciled investors.",
      jurisdiction: "DE", regulatory_body: "BaFin",
      due_date: "2027-01-31", recurrence: "annually", status: "upcoming", priority: "high",
      days_until_due: 324, is_overdue: false,
    },
    {
      id: "cd-7", category: "reporting", title: "Baltic BESS — Covenant Compliance Cert.",
      description: "Quarterly covenant compliance certificate required under senior debt facility for Baltic BESS Grid Storage.",
      jurisdiction: "LT", regulatory_body: "Lender",
      due_date: "2026-03-31", recurrence: "quarterly", status: "in_progress", priority: "medium",
      days_until_due: 18, is_overdue: false,
    },
    {
      id: "cd-8", category: "reporting", title: "Annual Audit Preparation",
      description: "Preparation of fund accounts and supporting documentation for statutory annual audit by PwC.",
      jurisdiction: "LU", regulatory_body: "PwC",
      due_date: "2026-05-31", recurrence: "annually", status: "upcoming", priority: "high",
      days_until_due: 79, is_overdue: false,
    },
    {
      id: "cd-9", category: "permit", title: "Nordvik Wind — Grid Connection Renewal",
      description: "Biennial grid connection agreement renewal with Statnett for Nordvik Wind Farm II 120MW capacity.",
      jurisdiction: "NO", regulatory_body: "Statnett",
      due_date: "2026-06-30", recurrence: "annually", status: "upcoming", priority: "medium",
      days_until_due: 109, is_overdue: false,
    },
    {
      id: "cd-10", category: "reporting", title: "Fund Level ESG KPI Tracking",
      description: "Monthly fund-level ESG KPI data collection covering all 7 holdings — energy production, CO2, jobs.",
      jurisdiction: "EU", regulatory_body: null,
      due_date: "2026-03-15", recurrence: "monthly", status: "overdue", priority: "low",
      days_until_due: -2, is_overdue: true,
    },
  ],
  overdue_count: 1,
  due_this_week: 2,
  due_this_month: 5,
};

// ── ESG Portfolio Summary ─────────────────────────────────────────────────────

export const MOCK_ESG_SUMMARY: ESGPortfolioSummaryResponse = {
  totals: {
    total_projects: 8,
    total_carbon_avoided_tco2e: 185000,
    total_renewable_energy_mwh: 2850000,
    total_jobs_created: 1240,
    taxonomy_aligned_count: 6,
    taxonomy_aligned_pct: 75,
  },
  sfdr_distribution: {
    article_6: 0,
    article_8: 2,
    article_9: 6,
    unclassified: 0,
  },
  taxonomy_alignment_pct: 75,
  top_sdgs: [
    { sdg_id: 7,  name: "Affordable and Clean Energy", project_count: 8 },
    { sdg_id: 13, name: "Climate Action",              project_count: 7 },
    { sdg_id: 9,  name: "Industry, Innovation and Infrastructure", project_count: 3 },
    { sdg_id: 8,  name: "Decent Work and Economic Growth",        project_count: 5 },
  ],
  carbon_trend: [
    { period: "2023", total_carbon_avoided_tco2e: 120000, total_carbon_footprint_tco2e: 4800 },
    { period: "2024", total_carbon_avoided_tco2e: 158000, total_carbon_footprint_tco2e: 5200 },
    { period: "2025", total_carbon_avoided_tco2e: 185000, total_carbon_footprint_tco2e: 5800 },
  ],
  project_rows: [],
};

// ── Investor Signal Score ─────────────────────────────────────────────────────

const makeDimScore = (score: number, weight: number, gaps: string[], recs: string[]) => ({
  score,
  weight,
  details: null,
  gaps,
  recommendations: recs,
});

export const MOCK_INVESTOR_SCORE: InvestorSignalScore = {
  id: "iss-1",
  org_id: "org-1",
  overall_score: 79,
  financial_capacity:    makeDimScore(82, 0.25, [], ["Consider increasing target AUM to strengthen deal flow"]),
  risk_management:       makeDimScore(75, 0.20, ["Risk framework documentation incomplete"], ["Formalise portfolio-level stress testing process"]),
  investment_strategy:   makeDimScore(85, 0.20, [], ["Mandate documentation is comprehensive"]),
  team_experience:       makeDimScore(80, 0.15, [], ["Strong team track record in European renewables"]),
  esg_commitment:        makeDimScore(88, 0.10, [], ["Article 9 classification demonstrates high ESG commitment"]),
  platform_readiness:    makeDimScore(62, 0.10, ["Profile not fully completed", "Missing benchmark data"], ["Complete all sections of your investor profile"]),
  score_change: 4,
  previous_score: 75,
  calculated_at: "2025-12-01T10:00:00Z",
};

export const MOCK_INVESTOR_BENCHMARK: BenchmarkData = {
  your_score: 79,
  platform_average: 68,
  top_quartile: 88,
  percentile: 72,
};

export const MOCK_INVESTOR_TOP_MATCHES: TopMatchItem[] = [
  { project_id: MOCK_IDS.p1, project_name: "Helios Solar Portfolio Iberia",    alignment_score: 91, recommendation: "strong_fit",   project_type: "solar",          geography_country: "ES" },
  { project_id: MOCK_IDS.p5, project_name: "Alpine Hydro Partners",            alignment_score: 88, recommendation: "strong_fit",   project_type: "hydro",          geography_country: "CH" },
  { project_id: MOCK_IDS.p3, project_name: "Adriatic Infrastructure Holdings", alignment_score: 82, recommendation: "good_fit",     project_type: "infrastructure", geography_country: "IT" },
  { project_id: MOCK_IDS.p2, project_name: "Nordvik Wind Farm II",             alignment_score: 78, recommendation: "good_fit",     project_type: "wind",           geography_country: "NO" },
  { project_id: MOCK_IDS.p7, project_name: "Nordic Biomass Energy",            alignment_score: 72, recommendation: "good_fit",     project_type: "biomass",        geography_country: "SE" },
];

export const MOCK_INVESTOR_IMPROVEMENT: ImprovementAction[] = [
  { title: "Complete Investor Profile",         description: "Fill in all missing sections of your platform profile to improve discoverability.", estimated_impact: 8,  effort_level: "low",    category: "platform_readiness", link_to: "/settings/profile" },
  { title: "Upload Risk Framework Document",   description: "Share your investment risk framework document to strengthen your risk management score.", estimated_impact: 6, effort_level: "medium", category: "risk_management",    link_to: null },
  { title: "Add Portfolio Track Record",        description: "Provide historical performance data to validate your investment track record.", estimated_impact: 5, effort_level: "medium", category: "financial_capacity",  link_to: null },
];

export const MOCK_INVESTOR_FACTORS: ScoreFactorItem[] = [
  { label: "Article 9 Classification",      impact: "positive", value: "+8 pts",   dimension: "esg_commitment" },
  { label: "European renewables mandate",   impact: "positive", value: "+6 pts",   dimension: "investment_strategy" },
  { label: "Experienced investment team",   impact: "positive", value: "+5 pts",   dimension: "team_experience" },
  { label: "Incomplete platform profile",   impact: "negative", value: "−4 pts",   dimension: "platform_readiness" },
  { label: "Risk docs not uploaded",        impact: "negative", value: "−3 pts",   dimension: "risk_management" },
];

// ── Investor Recommendations ──────────────────────────────────────────────────

export const MOCK_INVESTOR_RECOMMENDATIONS: InvestorRecommendations = {
  items: MOCK_PROJECTS.map((p) => ({
    match_id: null,
    project_id: p.id,
    project_name: p.name,
    project_type: p.project_type,
    geography_country: p.geography_country,
    stage: p.stage,
    total_investment_required: p.total_investment_required,
    currency: p.currency,
    cover_image_url: null,
    signal_score: p.latest_signal_score,
    alignment: {
      overall: 60 + Math.round((p.latest_signal_score ?? 5) * 4),
      sector: 18, geography: 15, ticket_size: 16, stage: 10, risk_return: 8, esg: 8,
      breakdown: {},
    },
    status: "suggested",
    mandate_id: "mandate-1",
    mandate_name: "European Renewables Mandate",
    updated_at: p.updated_at,
  })),
  total: 8,
};

// ── Alley Analytics ───────────────────────────────────────────────────────────

export const MOCK_ALLEY_OVERVIEW: PipelineOverview = {
  total_projects: 8,
  total_mw: 1415,
  total_value: 2177000000,
  currency: "EUR",
  scored_projects: 8,
  avg_score: 7.24,
  stage_counts: { concept: 1, development: 3, construction: 1, operational: 3 },
};

export const MOCK_STAGE_DISTRIBUTION: StageDistributionItem[] = [
  { stage: "concept",      count: 1, total_mw: 400,  total_value: 560000000 },
  { stage: "development",  count: 3, total_mw: 245,  total_value: 460000000 },
  { stage: "construction", count: 1, total_mw: 120,  total_value: 180000000 },
  { stage: "operational",  count: 3, total_mw: 650,  total_value: 977000000 },
];

export const MOCK_SCORE_DISTRIBUTION: ScoreDistributionItem[] = [
  { bucket: "0–2",  count: 0 },
  { bucket: "2–4",  count: 0 },
  { bucket: "4–6",  count: 3 },
  { bucket: "6–8",  count: 3 },
  { bucket: "8–10", count: 2 },
];

export const MOCK_DOC_COMPLETENESS: DocumentCompletenessItem[] = [
  { project_id: MOCK_IDS.p1, project_name: "Helios Solar Portfolio Iberia",   uploaded_count: 14, expected_count: 15, completeness_pct: 93, missing_types: ["insurance_certificate"] },
  { project_id: MOCK_IDS.p2, project_name: "Nordvik Wind Farm II",            uploaded_count: 11, expected_count: 15, completeness_pct: 73, missing_types: ["environmental_permit", "grid_connection", "financial_model"] },
  { project_id: MOCK_IDS.p3, project_name: "Adriatic Infrastructure Holdings", uploaded_count: 13, expected_count: 15, completeness_pct: 87, missing_types: ["insurance_certificate", "tax_opinion"] },
  { project_id: MOCK_IDS.p4, project_name: "Baltic BESS Grid Storage",        uploaded_count: 9,  expected_count: 15, completeness_pct: 60, missing_types: ["financial_model", "environmental_permit", "grid_connection", "technical_study", "offtake_agreement"] },
  { project_id: MOCK_IDS.p5, project_name: "Alpine Hydro Partners",           uploaded_count: 15, expected_count: 15, completeness_pct: 100, missing_types: [] },
  { project_id: MOCK_IDS.p6, project_name: "Sahara CSP Development",          uploaded_count: 5,  expected_count: 15, completeness_pct: 33, missing_types: ["financial_model", "environmental_permit", "grid_connection", "technical_study", "offtake_agreement", "water_rights", "land_agreement", "legal_opinion", "tax_opinion", "insurance_certificate"] },
  { project_id: MOCK_IDS.p7, project_name: "Nordic Biomass Energy",           uploaded_count: 10, expected_count: 15, completeness_pct: 67, missing_types: ["financial_model", "environmental_permit", "offtake_agreement", "grid_connection", "insurance_certificate"] },
  { project_id: MOCK_IDS.p8, project_name: "Thames Clean Energy Hub",         uploaded_count: 8,  expected_count: 15, completeness_pct: 53, missing_types: ["financial_model", "environmental_permit", "grid_connection", "technical_study", "offtake_agreement", "planning_consent", "marine_licence"] },
];

// ── Screener Saved Searches ───────────────────────────────────────────────────

export const MOCK_SCREENER_SEARCHES: SavedSearch[] = [
  {
    id: "ss-1",
    name: "European Operational Renewables",
    query: "operational solar or wind projects in Europe with score above 7",
    filters: { project_types: ["solar", "wind"], geographies: ["ES", "NO", "DE", "FR", "IT"], stages: ["operational"], min_signal_score: 7 },
    notify_new_matches: true,
    last_used: "2025-12-06T10:00:00Z",
  },
  {
    id: "ss-2",
    name: "BESS & Storage Development",
    query: "battery storage projects in development stage",
    filters: { project_types: ["storage"], stages: ["development", "permitting", "financing"] },
    notify_new_matches: false,
    last_used: "2025-11-20T14:00:00Z",
  },
  {
    id: "ss-3",
    name: "High Impact Infrastructure",
    query: "infrastructure projects with strong ESG",
    filters: { project_types: ["infrastructure"], min_signal_score: 8 },
    notify_new_matches: true,
    last_used: "2025-11-05T09:00:00Z",
  },
];

// ── Blockchain Audit Trail ───────────────────────────────────────────────────

export const MOCK_AUDIT_REPORT: AuditReport = {
  total: 12,
  anchored: 12,
  pending: 0,
  items: [
    {
      id: "ba-1", event_type: "deal_transition", entity_type: "project", entity_id: MOCK_IDS.p5,
      data_hash: "0x8a3f2e1b9c4d7e6a5f0b3c2d1e8a9b7c4d5e6f0a1b2c3d4e5f6a7b8c9d0e1f2a",
      merkle_root: "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
      chain: "Polygon", tx_hash: "0x7f3a9b2c4d5e6f1a8b3c2d1e0f9a8b7c", block_number: 54321098,
      status: "anchored", anchored_at: "2026-03-01T14:32:00Z",
    },
    {
      id: "ba-2", event_type: "signal_score", entity_type: "project", entity_id: MOCK_IDS.p2,
      data_hash: "0x2e9b4c3d5f1a7e6b0c2d4e5f8a9b1c3d4e5f7a8b9c0d1e2f4a5b6c7d8e9f0a1b",
      merkle_root: "0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c",
      chain: "Polygon", tx_hash: "0x2e9b5c4d6f2a8e7b1c3d5e6f9a0b2c4d", block_number: 54320987,
      status: "anchored", anchored_at: "2026-02-28T10:15:00Z",
    },
    {
      id: "ba-3", event_type: "lp_report_approval", entity_type: "report", entity_id: MOCK_IDS.p1,
      data_hash: "0x8c4d5e6f7a9b1c2d3e4f0a5b6c7d8e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      merkle_root: "0x3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d",
      chain: "Polygon", tx_hash: "0x8c4d6e7f8a0b2c3d4e5f6a7b9c1d2e3f", block_number: 54319876,
      status: "anchored", anchored_at: "2026-02-15T09:00:00Z",
    },
    {
      id: "ba-4", event_type: "document_upload", entity_type: "document", entity_id: "doc-lp-cc3",
      data_hash: "0x5f1e2a3b4c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
      merkle_root: "0x4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
      chain: "Polygon", tx_hash: "0x5f1e3a4b5c7d8e9f0a1b2c3d4e5f6a7b", block_number: 54318765,
      status: "anchored", anchored_at: "2026-01-20T14:45:00Z",
    },
    {
      id: "ba-5", event_type: "signal_score", entity_type: "project", entity_id: MOCK_IDS.p4,
      data_hash: "0x3a7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c",
      merkle_root: "0x5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
      chain: "Polygon", tx_hash: "0x3a7c9d0e1f2a3b4c5d6e7f8a9b0c1d2e", block_number: 54317654,
      status: "anchored", anchored_at: "2026-03-05T08:30:00Z",
    },
    {
      id: "ba-6", event_type: "document_upload", entity_type: "document", entity_id: "doc-board-res",
      data_hash: "0x9d2f3a4b5c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f",
      merkle_root: "0x6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a",
      chain: "Polygon", tx_hash: "0x9d2f4a5b6c8d9e0f1a2b3c4d5e6f7a8b", block_number: 54316543,
      status: "anchored", anchored_at: "2026-02-10T11:20:00Z",
    },
    {
      id: "ba-7", event_type: "document_upload", entity_type: "document", entity_id: "doc-offtake-amend",
      data_hash: "0x1b8e2a3b4c5d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
      merkle_root: "0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
      chain: "Polygon", tx_hash: "0x1b8e3a4b5c6d8e9f0a1b2c3d4e5f6a7b", block_number: 54315432,
      status: "anchored", anchored_at: "2026-01-28T16:00:00Z",
    },
    {
      id: "ba-8", event_type: "document_upload", entity_type: "document", entity_id: "doc-insurance",
      data_hash: "0x6c5a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a",
      merkle_root: "0x8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c",
      chain: "Polygon", tx_hash: "0x6c5a8b9c0d1e2f3a4b5c6d7e8f9a0b1c", block_number: 54314321,
      status: "anchored", anchored_at: "2026-01-15T10:00:00Z",
    },
    {
      id: "ba-9", event_type: "certification", entity_type: "report", entity_id: "doc-audited-acc",
      data_hash: "0x4e3d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
      merkle_root: "0x9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d",
      chain: "Polygon", tx_hash: "0x4e3d6f7a8b9c0d1e2f3a4b5c6d7e8f9a", block_number: 54313210,
      status: "anchored", anchored_at: "2026-01-10T09:00:00Z",
    },
    {
      id: "ba-10", event_type: "deal_transition", entity_type: "project", entity_id: "proj-eib",
      data_hash: "0xa2f7b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
      merkle_root: "0x0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e",
      chain: "Polygon", tx_hash: "0xa2f7c4d5e6f7a8b9c0d1e2f3a4b5c6d7", block_number: 54301234,
      status: "anchored", anchored_at: "2025-12-20T13:15:00Z",
    },
    {
      id: "ba-11", event_type: "document_upload", entity_type: "document", entity_id: "doc-tech-report",
      data_hash: "0x7b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c",
      merkle_root: "0x1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
      chain: "Polygon", tx_hash: "0x7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e", block_number: 54299876,
      status: "anchored", anchored_at: "2025-12-15T11:30:00Z",
    },
    {
      id: "ba-12", event_type: "lp_report_approval", entity_type: "report", entity_id: "rpt-q3-lp",
      data_hash: "0x3d6e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e",
      merkle_root: "0x2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a",
      chain: "Polygon", tx_hash: "0x3d6e5f6a7b8c9d0e1f2a3b4c5d6e7f8a", block_number: 54256789,
      status: "anchored", anchored_at: "2025-10-15T10:00:00Z",
    },
  ],
};

// ── Marketplace ───────────────────────────────────────────────────────────────

export const MOCK_MARKETPLACE_LISTINGS: ListingListResponse = {
  items: [
    {
      id: "lst-1", org_id: "org-ext-1", project_id: null,
      title: "Expert Financial Modeler — Renewable Energy",
      description: "Senior financial modeler with 15+ years in renewable energy project finance. Available for financial model builds, reviews and investor presentations.",
      listing_type: "co_investment", status: "active", visibility: "qualified_only",
      asking_price: "3500", minimum_investment: null, currency: "EUR",
      details: { service_type: "financial_modeling", rate_type: "per_day", provider: "Sofia Chen", rating: 4.9 },
      expires_at: null,
      project_name: null, project_type: null, geography_country: null, signal_score: null, rfq_count: 3,
      created_at: "2026-02-01T09:00:00Z", updated_at: "2026-03-01T09:00:00Z",
    },
    {
      id: "lst-2", org_id: "org-ext-2", project_id: null,
      title: "ESG Impact Assessment — Infrastructure",
      description: "Comprehensive ESG impact assessment for infrastructure and renewables. Covers SFDR Article 9 alignment, EU Taxonomy, and UN SDG mapping.",
      listing_type: "co_investment", status: "active", visibility: "qualified_only",
      asking_price: "8200", minimum_investment: null, currency: "EUR",
      details: { service_type: "esg_assessment", rate_type: "fixed", provider: "GreenMetrics Ltd", rating: 4.7 },
      expires_at: null,
      project_name: null, project_type: null, geography_country: null, signal_score: null, rfq_count: 5,
      created_at: "2026-01-15T09:00:00Z", updated_at: "2026-02-28T09:00:00Z",
    },
    {
      id: "lst-3", org_id: "org-ext-3", project_id: null,
      title: "Technical Due Diligence — Solar/Wind",
      description: "Full technical due diligence service for solar PV and onshore wind projects up to 300MW. Includes site visits, yield assessments and EPC review.",
      listing_type: "co_investment", status: "active", visibility: "public",
      asking_price: "12000", minimum_investment: null, currency: "EUR",
      details: { service_type: "technical_dd", rate_type: "fixed", provider: "Arup Advisory", rating: 4.8 },
      expires_at: null,
      project_name: "Alpine Hydro Partners", project_type: "hydro", geography_country: "CH", signal_score: 91, rfq_count: 7,
      created_at: "2026-01-10T09:00:00Z", updated_at: "2026-03-05T09:00:00Z",
    },
    {
      id: "lst-4", org_id: "org-1", project_id: MOCK_IDS.p5,
      title: "LP Co-Investment Opportunity — Alpine Hydro",
      description: "Co-investment opportunity in Alpine Hydro Partners, a 240MW run-of-river hydro project in Switzerland. IRR target 9.2%, 20-year PPA with Swiss federal utility.",
      listing_type: "co_investment", status: "active", visibility: "qualified_only",
      asking_price: "10000000", minimum_investment: "10000000", currency: "EUR",
      details: { irr_target: "9.2%", tenor_years: 20, ppa_counterparty: "Swiss Federal Utility" },
      expires_at: "2026-06-30T00:00:00Z",
      project_name: "Alpine Hydro Partners", project_type: "hydro", geography_country: "CH", signal_score: 91, rfq_count: 4,
      created_at: "2026-02-15T09:00:00Z", updated_at: "2026-03-10T09:00:00Z",
    },
    {
      id: "lst-5", org_id: "org-ext-4", project_id: null,
      title: "Legal Review — Energy Sector M&A",
      description: "Specialist legal review for energy sector M&A transactions, joint ventures and project finance. Partners with 20+ years experience in European energy law.",
      listing_type: "co_investment", status: "active", visibility: "qualified_only",
      asking_price: "450", minimum_investment: null, currency: "EUR",
      details: { service_type: "legal_review", rate_type: "per_hour", provider: "Linklaters LLP", rating: 4.6 },
      expires_at: null,
      project_name: null, project_type: null, geography_country: null, signal_score: null, rfq_count: 2,
      created_at: "2026-01-20T09:00:00Z", updated_at: "2026-02-20T09:00:00Z",
    },
  ],
  total: 5,
};

export const MOCK_MARKETPLACE_SENT_RFQS: RFQListResponse = {
  items: [
    {
      id: "rfq-s1", listing_id: "lst-2", buyer_org_id: "org-1",
      proposed_price: "8200", currency: "EUR", status: "submitted",
      message: "We would like an ESG assessment for our 7-asset portfolio covering SFDR Article 9, EU Taxonomy and SDG alignment. Timeline: 6 weeks.",
      counter_price: null, counter_terms: null,
      submitted_by: "Sofia Bergman",
      listing_title: "ESG Impact Assessment — Infrastructure",
      created_at: "2026-03-05T10:00:00Z", updated_at: "2026-03-05T10:00:00Z",
    },
    {
      id: "rfq-s2", listing_id: "lst-3", buyer_org_id: "org-1",
      proposed_price: "12000", currency: "EUR", status: "under_review",
      message: "Requesting technical DD for Danube Hydro Expansion (28MW, Romania). Site visit week of Mar 18.",
      counter_price: null, counter_terms: null,
      submitted_by: "Marco Rossi",
      listing_title: "Technical Due Diligence — Solar/Wind",
      created_at: "2026-03-01T09:00:00Z", updated_at: "2026-03-03T11:00:00Z",
    },
  ],
  total: 2,
};

export const MOCK_MARKETPLACE_TRANSACTIONS: TransactionListResponse = {
  items: [
    {
      id: "tx-1", listing_id: "lst-legal-danube", buyer_org_id: "org-1", seller_org_id: "org-ext-4",
      rfq_id: "rfq-old-1",
      amount: "18500", currency: "EUR",
      status: "completed",
      terms: { scope: "Legal review for Danube Hydro Expansion — investment agreement and NDA", jurisdiction: "RO/EN" },
      settlement_details: { invoice_ref: "LNK-2026-0214", payment_date: "2026-02-28" },
      completed_at: "2026-02-28T16:00:00Z",
      listing_title: "Legal Review — Energy Sector M&A",
      created_at: "2026-02-05T10:00:00Z", updated_at: "2026-02-28T16:00:00Z",
    },
  ],
  total: 1,
};

// ── Impact Measurement ────────────────────────────────────────────────────────

const makeSdgGoal = (number: number, label: string, color: string, level: "primary" | "secondary" | "co-benefit"): SDGGoal => ({
  number, label, color, contribution_level: level, description: `SDG ${number}: ${label}`,
});

export const MOCK_PORTFOLIO_IMPACT: PortfolioImpactResponse = {
  total_projects: 7,
  total_capacity_mw: 892,
  total_co2_reduction_tco2e: 287000,
  total_jobs_created: 1840,
  total_households_served: 340000,
  total_carbon_credit_tons: 124000,
  sdg_coverage: [6, 7, 9, 11, 13],
  projects: [
    {
      project_id: MOCK_IDS.p1, project_name: "Helios Solar Portfolio Iberia",
      project_type: "solar", geography_country: "ES",
      kpis: [
        { key: "capacity_mw", label: "Capacity", value: 180, unit: "MW", category: "energy" },
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 89000, unit: "tCO₂e/yr", category: "environment" },
        { key: "households_served", label: "Households Powered", value: 95000, unit: "", category: "social" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 320, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(7, "Affordable Energy", "#fcc30b", "primary"),
        makeSdgGoal(13, "Climate Action", "#3f7e44", "primary"),
      ],
      additionality_score: 84,
      additionality_breakdown: {},
    },
    {
      project_id: MOCK_IDS.p2, project_name: "Nordvik Wind Farm II",
      project_type: "wind", geography_country: "NO",
      kpis: [
        { key: "capacity_mw", label: "Capacity", value: 120, unit: "MW", category: "energy" },
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 54000, unit: "tCO₂e/yr", category: "environment" },
        { key: "households_served", label: "Households Powered", value: 56000, unit: "", category: "social" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 180, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(7, "Affordable Energy", "#fcc30b", "primary"),
        makeSdgGoal(13, "Climate Action", "#3f7e44", "primary"),
      ],
      additionality_score: 72,
      additionality_breakdown: {},
    },
    {
      project_id: MOCK_IDS.p3, project_name: "Adriatic Infrastructure Holdings",
      project_type: "infrastructure", geography_country: "IT",
      kpis: [
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 12000, unit: "tCO₂e/yr", category: "environment" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 420, unit: "", category: "social" },
        { key: "households_served", label: "People Served", value: 28000, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(9, "Industry & Innovation", "#fd6925", "primary"),
        makeSdgGoal(11, "Sustainable Cities", "#fd9d24", "secondary"),
      ],
      additionality_score: 65,
      additionality_breakdown: {},
    },
    {
      project_id: MOCK_IDS.p4, project_name: "Baltic BESS Grid Storage",
      project_type: "storage", geography_country: "LT",
      kpis: [
        { key: "capacity_mw", label: "Capacity", value: 80, unit: "MW", category: "energy" },
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 8000, unit: "tCO₂e/yr", category: "environment" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 85, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(7, "Affordable Energy", "#fcc30b", "primary"),
        makeSdgGoal(9, "Industry & Innovation", "#fd6925", "secondary"),
      ],
      additionality_score: 71,
      additionality_breakdown: {},
    },
    {
      project_id: MOCK_IDS.p5, project_name: "Alpine Hydro Partners",
      project_type: "hydro", geography_country: "CH",
      kpis: [
        { key: "capacity_mw", label: "Capacity", value: 240, unit: "MW", category: "energy" },
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 98000, unit: "tCO₂e/yr", category: "environment" },
        { key: "households_served", label: "Households Powered", value: 120000, unit: "", category: "social" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 540, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(7, "Affordable Energy", "#fcc30b", "primary"),
        makeSdgGoal(13, "Climate Action", "#3f7e44", "primary"),
        makeSdgGoal(6, "Clean Water", "#26bde2", "co-benefit"),
      ],
      additionality_score: 91,
      additionality_breakdown: {},
    },
    {
      project_id: MOCK_IDS.p7, project_name: "Nordic Biomass Energy",
      project_type: "biomass", geography_country: "SE",
      kpis: [
        { key: "capacity_mw", label: "Capacity", value: 48, unit: "MW", category: "energy" },
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 18000, unit: "tCO₂e/yr", category: "environment" },
        { key: "households_served", label: "Households Powered", value: 22000, unit: "", category: "social" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 145, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(7, "Affordable Energy", "#fcc30b", "primary"),
        makeSdgGoal(13, "Climate Action", "#3f7e44", "secondary"),
      ],
      additionality_score: 68,
      additionality_breakdown: {},
    },
    {
      project_id: MOCK_IDS.p8, project_name: "Thames Clean Energy Hub",
      project_type: "wind", geography_country: "GB",
      kpis: [
        { key: "capacity_mw", label: "Capacity", value: 224, unit: "MW", category: "energy" },
        { key: "co2_reduction_tco2e", label: "CO₂ Avoided", value: 8000, unit: "tCO₂e/yr", category: "environment" },
        { key: "households_served", label: "Households Powered", value: 19000, unit: "", category: "social" },
        { key: "jobs_created_direct", label: "Jobs Created", value: 150, unit: "", category: "social" },
      ],
      sdg_goals: [
        makeSdgGoal(7, "Affordable Energy", "#fcc30b", "primary"),
        makeSdgGoal(13, "Climate Action", "#3f7e44", "primary"),
      ],
      additionality_score: 76,
      additionality_breakdown: {},
    },
  ],
};

export const MOCK_CARBON_CREDITS: CarbonCreditListResponse = {
  items: [
    {
      id: "cc-1", project_id: MOCK_IDS.p1, org_id: "org-1",
      registry: "Gold Standard", methodology: "GS-VER Solar Power Generation",
      vintage_year: 2024, quantity_tons: "42000",
      price_per_ton: "18.50", currency: "EUR",
      serial_number: "GS-2024-ES-042000-001",
      verification_status: "verified", verification_body: "TÜV SÜD",
      issuance_date: "2025-06-15", retirement_date: null,
      created_at: "2025-06-10T09:00:00Z",
    },
    {
      id: "cc-2", project_id: MOCK_IDS.p5, org_id: "org-1",
      registry: "Verra VCS", methodology: "VM0038 Methodology for Renewable Energy Generation",
      vintage_year: 2024, quantity_tons: "54000",
      price_per_ton: "21.00", currency: "EUR",
      serial_number: "VCS-2024-CH-054000-001",
      verification_status: "issued", verification_body: "Bureau Veritas",
      issuance_date: "2025-09-01", retirement_date: null,
      created_at: "2025-09-01T09:00:00Z",
    },
    {
      id: "cc-3", project_id: MOCK_IDS.p2, org_id: "org-1",
      registry: "Gold Standard", methodology: "GS-VER Wind Power Generation",
      vintage_year: 2023, quantity_tons: "28000",
      price_per_ton: "16.00", currency: "EUR",
      serial_number: "GS-2023-NO-028000-001",
      verification_status: "retired", verification_body: "TÜV SÜD",
      issuance_date: "2024-05-01", retirement_date: "2025-01-15",
      created_at: "2024-05-01T09:00:00Z",
    },
  ],
  total: 3,
  total_estimated: 0,
  total_verified: 42000,
  total_issued: 54000,
  total_retired: 28000,
};
