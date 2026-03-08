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
import type { GeneratedReportListResponse } from "@/lib/reports";
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
    currency: "EUR",
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
    currency: "EUR",
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
    currency: "EUR",
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
    currency: "EUR",
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
    currency: "EUR",
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
    currency: "EUR",
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
    currency: "EUR",
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
    currency: "EUR",
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
    by_currency: [{ label: "EUR", value: 255000000, pct: 100, is_concentrated: false }],
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
      id: "ld-1", title: "NDA — Nordvik Wind Farm II", doc_type: "nda", status: "signed",
      template_id: "tpl-nda", project_id: MOCK_IDS.p2,
      content: "", s3_key: "legal/ld-1.pdf", version: 2,
      signed_date: "2024-01-15", expiry_date: "2026-01-14",
      questionnaire_answers: null, generation_status: "ready", download_url: "#",
      created_at: "2024-01-10T09:00:00Z", updated_at: "2024-01-15T14:00:00Z",
    },
    {
      id: "ld-2", title: "NDA — Sahara CSP Development", doc_type: "nda", status: "draft",
      template_id: "tpl-nda", project_id: MOCK_IDS.p6,
      content: "", s3_key: null, version: 1,
      signed_date: null, expiry_date: null,
      questionnaire_answers: null, generation_status: null, download_url: null,
      created_at: "2025-11-20T10:00:00Z", updated_at: "2025-11-20T10:00:00Z",
    },
    {
      id: "ld-3", title: "Letter of Intent — Alpine Hydro Partners", doc_type: "term_sheet", status: "review",
      template_id: "tpl-loi", project_id: MOCK_IDS.p5,
      content: "", s3_key: "legal/ld-3.pdf", version: 1,
      signed_date: null, expiry_date: null,
      questionnaire_answers: null, generation_status: "ready", download_url: "#",
      created_at: "2025-10-01T09:00:00Z", updated_at: "2025-10-15T10:00:00Z",
    },
    {
      id: "ld-4", title: "Term Sheet — Nordvik Wind Farm II", doc_type: "term_sheet", status: "signed",
      template_id: "tpl-ts", project_id: MOCK_IDS.p2,
      content: "", s3_key: "legal/ld-4.pdf", version: 3,
      signed_date: "2025-08-20", expiry_date: null,
      questionnaire_answers: null, generation_status: "ready", download_url: "#",
      created_at: "2025-07-01T09:00:00Z", updated_at: "2025-08-20T14:00:00Z",
    },
    {
      id: "ld-5", title: "KYC/AML Package — European Infrastructure Fund", doc_type: "subscription_agreement", status: "signed",
      template_id: null, project_id: null,
      content: "", s3_key: "legal/ld-5.pdf", version: 1,
      signed_date: "2022-02-15", expiry_date: null,
      questionnaire_answers: null, generation_status: "ready", download_url: "#",
      created_at: "2022-01-20T09:00:00Z", updated_at: "2022-02-15T10:00:00Z",
    },
    {
      id: "ld-6", title: "Investment Agreement — Adriatic Infrastructure Holdings", doc_type: "subscription_agreement", status: "draft",
      template_id: "tpl-ia", project_id: MOCK_IDS.p3,
      content: "", s3_key: null, version: 2,
      signed_date: null, expiry_date: null,
      questionnaire_answers: null, generation_status: null, download_url: null,
      created_at: "2025-11-01T09:00:00Z", updated_at: "2025-11-28T15:00:00Z",
    },
  ],
  total: 6,
};

// ── Reports ───────────────────────────────────────────────────────────────────

export const MOCK_REPORTS: GeneratedReportListResponse = {
  items: [
    {
      id: "rpt-1", org_id: "org-1", template_id: "tpl-perf", title: "Q4 2025 Performance Report",
      status: "ready", parameters: { period: "Q4 2025" }, result_data: null,
      s3_key: "reports/rpt-1.pdf", error_message: null, generated_by: "system",
      completed_at: "2026-01-10T09:30:00Z", download_url: "#",
      template_name: "Quarterly Performance", created_at: "2026-01-10T09:00:00Z", updated_at: "2026-01-10T09:30:00Z",
    },
    {
      id: "rpt-2", org_id: "org-1", template_id: "tpl-esg", title: "Annual ESG & Impact Report 2025",
      status: "ready", parameters: { year: 2025 }, result_data: null,
      s3_key: "reports/rpt-2.pdf", error_message: null, generated_by: "system",
      completed_at: "2025-12-20T11:00:00Z", download_url: "#",
      template_name: "ESG Impact Report", created_at: "2025-12-20T10:00:00Z", updated_at: "2025-12-20T11:00:00Z",
    },
    {
      id: "rpt-3", org_id: "org-1", template_id: "tpl-comp", title: "SFDR Compliance Report Q4 2025",
      status: "ready", parameters: { period: "Q4 2025" }, result_data: null,
      s3_key: "reports/rpt-3.pdf", error_message: null, generated_by: "system",
      completed_at: "2026-01-12T10:00:00Z", download_url: "#",
      template_name: "SFDR Compliance", created_at: "2026-01-12T09:30:00Z", updated_at: "2026-01-12T10:00:00Z",
    },
  ],
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

// ── Watchlists ────────────────────────────────────────────────────────────────

export const MOCK_WATCHLISTS: Watchlist[] = [
  {
    id: "wl-1", name: "Nordic Renewables Tracker",
    watch_type: "project_type",
    criteria: { project_types: ["wind", "hydro"], geographies: ["NO", "SE", "FI", "DK"] },
    alert_channels: ["in_app", "email"], alert_frequency: "daily",
    is_active: true, total_alerts_sent: 12, unread_alerts: 2,
  },
  {
    id: "wl-2", name: "High Score Solar Pipeline",
    watch_type: "score_threshold",
    criteria: { project_types: ["solar"], min_signal_score: 7 },
    alert_channels: ["in_app"], alert_frequency: "weekly",
    is_active: true, total_alerts_sent: 5, unread_alerts: 0,
  },
  {
    id: "wl-3", name: "Infrastructure Opportunities",
    watch_type: "project_type",
    criteria: { project_types: ["infrastructure"] },
    alert_channels: ["in_app", "email"], alert_frequency: "weekly",
    is_active: true, total_alerts_sent: 3, unread_alerts: 1,
  },
];

export const MOCK_WATCHLIST_ALERTS: WatchlistAlert[] = [
  {
    id: "wa-1", watchlist_id: "wl-1", watchlist_name: "Nordic Renewables Tracker",
    alert_type: "new_project", entity_type: "project", entity_id: MOCK_IDS.p2,
    data: { project_name: "Nordvik Wind Farm II", score: 7.8 },
    is_read: false, created_at: "2025-12-06T10:00:00Z",
  },
  {
    id: "wa-2", watchlist_id: "wl-1", watchlist_name: "Nordic Renewables Tracker",
    alert_type: "score_change", entity_type: "project", entity_id: MOCK_IDS.p7,
    data: { project_name: "Nordic Biomass Energy", old_score: 6.8, new_score: 7.1 },
    is_read: false, created_at: "2025-12-05T14:00:00Z",
  },
  {
    id: "wa-3", watchlist_id: "wl-3", watchlist_name: "Infrastructure Opportunities",
    alert_type: "new_project", entity_type: "project", entity_id: MOCK_IDS.p3,
    data: { project_name: "Adriatic Infrastructure Holdings", score: 8.5 },
    is_read: false, created_at: "2025-12-04T09:00:00Z",
  },
];

// ── Notifications ─────────────────────────────────────────────────────────────

export const MOCK_NOTIFICATIONS: NotificationListResponse = {
  items: [
    { id: "n1",  type: "action_required", title: "Score Calculation Complete",         message: "Nordvik Wind Farm II signal score updated to 7.8. Review recommended.",             link: `/projects/${MOCK_IDS.p2}`, is_read: false, created_at: "2025-12-07T09:00:00Z" },
    { id: "n2",  type: "action_required", title: "Document Signature Required",         message: "Investment Agreement for Adriatic Infrastructure Holdings awaits your signature.", link: "/legal",                   is_read: false, created_at: "2025-12-06T14:30:00Z" },
    { id: "n3",  type: "warning",         title: "Compliance Deadline Approaching",     message: "SFDR Q4 PAI indicators due in 10 days. Review and submit before Jan 15.",          link: "/compliance",              is_read: false, created_at: "2025-12-06T10:00:00Z" },
    { id: "n4",  type: "info",            title: "New Match — Thames Clean Energy Hub", message: "A new project matching your mandate criteria has been identified.",                  link: "/deals",                   is_read: false, created_at: "2025-12-05T16:00:00Z" },
    { id: "n5",  type: "info",            title: "LP Report Available",                 message: "Q4 2025 LP Report is ready for review and distribution.",                           link: "/lp-reports",              is_read: true,  created_at: "2025-12-05T11:00:00Z" },
    { id: "n6",  type: "warning",         title: "AML Review Required",                 message: "Annual KYC/AML review is due for 2 counterparties by end of month.",               link: "/compliance",              is_read: true,  created_at: "2025-12-04T09:00:00Z" },
    { id: "n7",  type: "info",            title: "Score Improvement — Helios Solar",    message: "Helios Solar Portfolio Iberia maintained Excellent rating (9.2/10).",              link: `/projects/${MOCK_IDS.p1}`, is_read: true,  created_at: "2025-12-03T14:00:00Z" },
    { id: "n8",  type: "action_required", title: "Intro Request — Alpine Hydro",        message: "Alpine Hydro Partners developer has requested an introduction call.",              link: "/deals",                   is_read: false, created_at: "2025-12-03T10:00:00Z" },
    { id: "n9",  type: "info",            title: "Portfolio Milestone — €400M NAV",     message: "European Infrastructure Impact Fund has surpassed €400M NAV.",                     link: "/portfolio",               is_read: true,  created_at: "2025-12-02T09:00:00Z" },
    { id: "n10", type: "warning",         title: "Climate Alert — Iberian Heat Wave",   message: "AEMET issues heat warning for Q1 2026. Monitor Helios Solar production.",          link: "/risk",                    is_read: false, created_at: "2025-12-01T08:00:00Z" },
    { id: "n11", type: "info",            title: "Baltic BESS Score Updated",           message: "Baltic BESS Grid Storage score improved from 5.8 to 6.3 after document upload.",  link: `/projects/${MOCK_IDS.p4}`, is_read: true,  created_at: "2025-11-28T15:00:00Z" },
    { id: "n12", type: "system",          title: "System Maintenance",                  message: "Scheduled maintenance window Jan 12, 02:00–04:00 UTC. Platform unavailable.",     link: null,                       is_read: true,  created_at: "2025-11-25T12:00:00Z" },
  ],
  total: 12,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

// ── Compliance ────────────────────────────────────────────────────────────────

export const MOCK_COMPLIANCE_DEADLINES: ComplianceResponse = {
  items: [
    {
      id: "cd-1", category: "sfdr", title: "SFDR PAI Indicators — Q4 2025",
      description: "Submit Principal Adverse Impact indicators for Q4 reporting period.",
      jurisdiction: "EU", regulatory_body: "ESMA",
      due_date: "2026-01-15", recurrence: "quarterly", status: "upcoming", priority: "critical",
      days_until_due: 8, is_overdue: false,
    },
    {
      id: "cd-2", category: "reporting", title: "AIFMD Transparency Report 2025",
      description: "Annual Alternative Investment Fund Managers Directive transparency report.",
      jurisdiction: "EU", regulatory_body: "National CA",
      due_date: "2026-02-28", recurrence: "annually", status: "in_progress", priority: "high",
      days_until_due: 52, is_overdue: false,
    },
    {
      id: "cd-3", category: "regulatory_filing", title: "AML/KYC Annual Review",
      description: "Annual review of KYC documentation for all portfolio company counterparties.",
      jurisdiction: "EU", regulatory_body: "Internal",
      due_date: "2025-12-31", recurrence: "annually", status: "in_progress", priority: "high",
      days_until_due: 24, is_overdue: false,
    },
    {
      id: "cd-4", category: "sfdr", title: "SFDR Article 9 Annual Disclosure",
      description: "Publish annual Article 9 sustainable investment objective report on website.",
      jurisdiction: "EU", regulatory_body: "ESMA",
      due_date: "2026-03-31", recurrence: "annually", status: "upcoming", priority: "medium",
      days_until_due: 83, is_overdue: false,
    },
    {
      id: "cd-5", category: "reporting", title: "ESG Impact Report 2025",
      description: "Annual ESG data collection and impact report for LPs.",
      jurisdiction: "EU", regulatory_body: null,
      due_date: "2026-03-15", recurrence: "annually", status: "in_progress", priority: "medium",
      days_until_due: 67, is_overdue: false,
    },
    {
      id: "cd-6", category: "tax", title: "FATCA/CRS Reporting — 2025",
      description: "US FATCA and OECD CRS annual tax transparency reporting.",
      jurisdiction: "Global", regulatory_body: "Tax Authority",
      due_date: "2025-11-30", recurrence: "annually", status: "completed", priority: "high",
      days_until_due: -8, is_overdue: false,
    },
  ],
  overdue_count: 0,
  due_this_week: 1,
  due_this_month: 2,
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
