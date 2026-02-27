/**
 * Risk Analysis & Compliance types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface RiskAssessmentCreate {
  entity_type: string;
  entity_id: string;
  risk_type: string;
  severity: string;
  probability: string;
  description: string;
  mitigation?: string;
  status?: string;
}

export interface RiskAssessmentResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  risk_type: string;
  severity: string;
  probability: string;
  description: string;
  mitigation: string | null;
  status: string;
  assessed_by: string;
  created_at: string;
  updated_at: string;
}

export interface HeatmapCell {
  severity: string;
  probability: string;
  count: number;
  risk_ids: string[];
}

export interface RiskHeatmap {
  cells: HeatmapCell[];
  total_risks: number;
}

export interface ConcentrationItem {
  label: string;
  value: number;
  pct: number;
  is_concentrated: boolean;
}

export interface ConcentrationAnalysis {
  portfolio_id: string;
  total_invested: number;
  by_sector: ConcentrationItem[];
  by_geography: ConcentrationItem[];
  by_counterparty: ConcentrationItem[];
  by_currency: ConcentrationItem[];
  concentration_flags: string[];
}

export interface AutoRiskItem {
  risk_type: string;
  severity: string;
  probability: string;
  description: string;
}

export interface RiskTrendPoint {
  date: string;
  risk_score: number;
}

export interface RiskDashboard {
  portfolio_id: string;
  overall_risk_score: number;
  heatmap: RiskHeatmap;
  top_risks: RiskAssessmentResponse[];
  auto_identified: AutoRiskItem[];
  concentration: ConcentrationAnalysis;
  risk_trend: RiskTrendPoint[];
}

export interface ScenarioRequest {
  scenario_type: string;
  parameters: Record<string, unknown>;
}

export interface HoldingImpact {
  holding_id: string;
  asset_name: string;
  current_value: number;
  stressed_value: number;
  delta_value: number;
  delta_pct: number;
}

export interface WaterfallEntry {
  label: string;
  value: number;
}

export interface ScenarioResult {
  scenario_type: string;
  parameters: Record<string, unknown>;
  nav_before: number;
  irr_before: number | null;
  nav_after: number;
  irr_after: number | null;
  nav_delta: number;
  nav_delta_pct: number;
  holding_impacts: HoldingImpact[];
  waterfall: WaterfallEntry[];
  narrative: string;
}

export interface PAIIndicator {
  id: number;
  name: string;
  category: string;
  value: string | null;
  unit: string;
  status: string;
}

export interface DNSHCheck {
  objective: string;
  status: string;
  notes: string;
}

export interface TaxonomyResult {
  holding_id: string;
  asset_name: string;
  eligible: boolean;
  aligned: boolean;
  eligible_pct: number;
  aligned_pct: number;
  economic_activity: string;
  dnsh_checks: DNSHCheck[];
}

export interface ComplianceStatus {
  portfolio_id: string;
  sfdr_classification: string;
  sustainable_investment_pct: number;
  taxonomy_eligible_pct: number;
  taxonomy_aligned_pct: number;
  pai_indicators: PAIIndicator[];
  taxonomy_results: TaxonomyResult[];
  overall_status: string;
  last_assessed: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
}

export interface AuditTrail {
  items: AuditEntry[];
  total: number;
}

// ── 5-Domain Risk Framework ────────────────────────────────────────────────

export interface RiskDomainScore {
  domain: string;
  score: number | null;
  label: string;
  details: Record<string, unknown> | null;
  mitigation: Record<string, unknown> | null;
}

export interface FiveDomainRisk {
  portfolio_id: string;
  overall_risk_score: number | null;
  domains: RiskDomainScore[];
  monitoring_enabled: boolean;
  last_monitoring_check: string | null;
  active_alerts_count: number;
  source: "stored" | "computed";
}

export interface MonitoringAlert {
  id: string;
  org_id: string;
  portfolio_id: string | null;
  project_id: string | null;
  alert_type: string;
  severity: string;
  domain: string;
  title: string;
  description: string;
  source_name: string | null;
  is_read: boolean;
  is_actioned: boolean;
  action_taken: string | null;
  created_at: string;
}

export interface MonitoringAlertList {
  items: MonitoringAlert[];
  total: number;
}

export interface MitigationResponse {
  domain: string;
  mitigation_text: string;
  key_actions: string[];
  model_used: string;
}

// ── Query Keys ─────────────────────────────────────────────────────────────

export const riskKeys = {
  all: ["risk"] as const,
  dashboard: (portfolioId: string) =>
    [...riskKeys.all, "dashboard", portfolioId] as const,
  assessments: (entityType?: string, entityId?: string) =>
    [...riskKeys.all, "assessments", entityType ?? "", entityId ?? ""] as const,
  scenarios: (portfolioId: string) =>
    [...riskKeys.all, "scenarios", portfolioId] as const,
  concentration: (portfolioId: string) =>
    [...riskKeys.all, "concentration", portfolioId] as const,
  compliance: (portfolioId: string) =>
    [...riskKeys.all, "compliance", portfolioId] as const,
  auditTrail: (entityType?: string, entityId?: string) =>
    [...riskKeys.all, "audit", entityType ?? "", entityId ?? ""] as const,
  domains: (portfolioId: string) =>
    [...riskKeys.all, "domains", portfolioId] as const,
  alerts: (portfolioId?: string) =>
    [...riskKeys.all, "alerts", portfolioId ?? ""] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useRiskDashboard(portfolioId: string | undefined) {
  return useQuery({
    queryKey: riskKeys.dashboard(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<RiskDashboard>(`/risk/dashboard/${portfolioId}`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

export function useRiskAssessments(
  entityType?: string,
  entityId?: string
) {
  const params = new URLSearchParams();
  if (entityType) params.set("entity_type", entityType);
  if (entityId) params.set("entity_id", entityId);
  const qs = params.toString();

  return useQuery({
    queryKey: riskKeys.assessments(entityType, entityId),
    queryFn: () =>
      api
        .get<RiskAssessmentResponse[]>(`/risk/assessments${qs ? `?${qs}` : ""}`)
        .then((r) => r.data),
  });
}

export function useCreateRiskAssessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskAssessmentCreate) =>
      api.post<RiskAssessmentResponse>("/risk/assess", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: riskKeys.all });
    },
  });
}

export function useRunScenario(portfolioId: string | undefined) {
  return useMutation({
    mutationFn: (req: ScenarioRequest) =>
      api
        .post<ScenarioResult>(`/risk/scenarios/${portfolioId}`, req)
        .then((r) => r.data),
  });
}

export function useConcentration(portfolioId: string | undefined) {
  return useQuery({
    queryKey: riskKeys.concentration(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<ConcentrationAnalysis>(`/risk/concentration/${portfolioId}`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

export function useComplianceStatus(portfolioId: string | undefined) {
  return useQuery({
    queryKey: riskKeys.compliance(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<ComplianceStatus>(`/risk/compliance/${portfolioId}`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

export function useAuditTrail(
  entityType?: string,
  entityId?: string,
  page = 1
) {
  const params = new URLSearchParams({ page: String(page) });
  if (entityType) params.set("entity_type", entityType);
  if (entityId) params.set("entity_id", entityId);

  return useQuery({
    queryKey: [...riskKeys.auditTrail(entityType, entityId), page],
    queryFn: () =>
      api
        .get<AuditTrail>(`/risk/audit-trail?${params}`)
        .then((r) => r.data),
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export const SEVERITY_ORDER = ["low", "medium", "high", "critical"] as const;
export const PROBABILITY_ORDER = [
  "unlikely",
  "possible",
  "likely",
  "very_likely",
] as const;

export function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "bg-red-600 text-white";
    case "high":     return "bg-red-400 text-white";
    case "medium":   return "bg-amber-400 text-white";
    default:         return "bg-green-300 text-white";
  }
}

export function severityBadge(severity: string): "error" | "warning" | "neutral" | "success" {
  switch (severity) {
    case "critical": return "error";
    case "high":     return "error";
    case "medium":   return "warning";
    default:         return "success";
  }
}

export function probabilityLabel(p: string): string {
  return p.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function sfdrLabel(cls: string): string {
  const map: Record<string, string> = {
    article_6: "Article 6",
    article_8: "Article 8 — Light Green",
    article_9: "Article 9 — Dark Green",
    not_applicable: "Not Applicable",
  };
  return map[cls] ?? cls;
}

export function sfdrColor(cls: string): string {
  switch (cls) {
    case "article_9": return "text-green-700 bg-green-50 border-green-200";
    case "article_8": return "text-emerald-700 bg-emerald-50 border-emerald-200";
    case "article_6": return "text-neutral-700 bg-neutral-50 border-neutral-200";
    default:          return "text-neutral-500 bg-neutral-50 border-neutral-200";
  }
}

export function complianceStatusColor(status: string): string {
  switch (status) {
    case "compliant":       return "text-green-700";
    case "needs_attention": return "text-amber-600";
    default:                return "text-red-600";
  }
}

export function paiStatusColor(status: string): string {
  switch (status) {
    case "met":             return "text-green-600";
    case "not_met":         return "text-red-600";
    case "not_applicable":  return "text-neutral-400";
    default:                return "text-amber-600";
  }
}

export const SCENARIO_TYPES = [
  {
    value: "interest_rate_shock",
    label: "Interest Rate Shock",
    description: "Simulate a change in interest rates",
    params: [
      { key: "basis_points", label: "Basis Points", min: -500, max: 500, default: 200 },
      { key: "duration_years", label: "Asset Duration (years)", min: 1, max: 30, default: 10 },
    ],
  },
  {
    value: "carbon_price_change",
    label: "Carbon Price Change",
    description: "Impact of carbon price movement on holdings",
    params: [
      { key: "pct_change", label: "Price Change (%)", min: -80, max: 200, default: -30 },
      { key: "carbon_revenue_pct", label: "Carbon Revenue Exposure (%)", min: 0, max: 100, default: 15 },
    ],
  },
  {
    value: "technology_disruption",
    label: "Technology Disruption",
    description: "Sector-specific technology risk haircut",
    params: [
      { key: "haircut_pct", label: "NAV Haircut (%)", min: 0, max: 50, default: 15 },
    ],
  },
  {
    value: "regulatory_change",
    label: "Regulatory Change",
    description: "New compliance requirements cost impact",
    params: [
      { key: "compliance_cost_pct", label: "Compliance Cost (% of NAV)", min: 0, max: 20, default: 5 },
    ],
  },
  {
    value: "climate_event",
    label: "Physical Climate Event",
    description: "Direct asset damage from a climate event",
    params: [
      { key: "damage_pct", label: "Asset Damage (%)", min: 0, max: 100, default: 20 },
      { key: "portfolio_affected_pct", label: "Portfolio Affected (%)", min: 0, max: 100, default: 30 },
    ],
  },
  {
    value: "custom",
    label: "Custom Scenario",
    description: "User-defined portfolio NAV change",
    params: [
      { key: "nav_change_pct", label: "NAV Change (%)", min: -100, max: 100, default: -10 },
    ],
  },
] as const;

export type ScenarioType = (typeof SCENARIO_TYPES)[number];

// ── 5-Domain hooks ─────────────────────────────────────────────────────────

export function useDomainScores(portfolioId: string | undefined) {
  return useQuery({
    queryKey: riskKeys.domains(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<FiveDomainRisk>(`/risk/domains/${portfolioId}`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

export function useMonitoringAlerts(portfolioId?: string, unreadOnly = false) {
  const params = new URLSearchParams();
  if (portfolioId) params.set("portfolio_id", portfolioId);
  if (unreadOnly) params.set("unread_only", "true");
  const qs = params.toString();

  return useQuery({
    queryKey: riskKeys.alerts(portfolioId),
    queryFn: () =>
      api
        .get<MonitoringAlertList>(`/risk/alerts${qs ? `?${qs}` : ""}`)
        .then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function useResolveAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, actionTaken }: { alertId: string; actionTaken: string }) =>
      api
        .put<MonitoringAlert>(`/risk/alerts/${alertId}/resolve`, { action_taken: actionTaken })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: riskKeys.alerts() });
    },
  });
}

export function useTriggerMonitoringCheck(portfolioId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api
        .post(`/risk/alerts/check/${portfolioId}`)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: riskKeys.alerts(portfolioId) });
      qc.invalidateQueries({ queryKey: riskKeys.domains(portfolioId ?? "") });
    },
  });
}

export function useGenerateMitigation(portfolioId: string | undefined) {
  return useMutation({
    mutationFn: (domain: string) =>
      api
        .post<MitigationResponse>(`/risk/domains/${portfolioId}/mitigation`, { domain })
        .then((r) => r.data),
  });
}

// ── Domain helpers ──────────────────────────────────────────────────────────

export const DOMAIN_LABELS: Record<string, string> = {
  market:     "Market Risk",
  climate:    "Climate Risk",
  regulatory: "Regulatory Risk",
  technology: "Technology Risk",
  liquidity:  "Liquidity Risk",
};

export const DOMAIN_COLORS: Record<string, string> = {
  market:     "#3b82f6",
  climate:    "#10b981",
  regulatory: "#f59e0b",
  technology: "#8b5cf6",
  liquidity:  "#ef4444",
};

export function domainRiskLabel(score: number | null): string {
  if (score === null) return "Unknown";
  if (score >= 75) return "Critical";
  if (score >= 50) return "High";
  if (score >= 25) return "Medium";
  return "Low";
}

export function domainRiskColor(score: number | null): string {
  if (score === null) return "text-neutral-400";
  if (score >= 75) return "text-red-600";
  if (score >= 50) return "text-orange-500";
  if (score >= 25) return "text-amber-500";
  return "text-green-600";
}

export function alertSeverityBadge(severity: string): "error" | "warning" | "neutral" | "success" {
  switch (severity) {
    case "critical": return "error";
    case "high":     return "error";
    case "medium":   return "warning";
    default:         return "neutral";
  }
}
