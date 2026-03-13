"use client";

import { useState } from "react";
import { Download, Leaf, Users, Zap, TrendingUp } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  LineChart,
} from "@scr/ui";
import { usePortfolios } from "@/lib/portfolio";
import {
  useESGPortfolioSummary,
  formatNumber,
  buildExportUrl,
  SDG_COLORS,
  SDG_NAMES,
  SFDR_COLORS,
} from "@/lib/esg";
import { InfoBanner } from "@/components/info-banner";

// ── Mock Data ─────────────────────────────────────────────────────────────────

const MOCK_ESG_DATA = {
  totals: {
    total_carbon_avoided_tco2e: 287000,
    total_renewable_energy_mwh: 612000,
    total_jobs_created: 1847,
    taxonomy_aligned_count: 5,
    taxonomy_aligned_pct: 78,
    total_projects: 7,
  },
  taxonomy_alignment_pct: 78,
  sfdr_distribution: {
    article_6: 1,
    article_8: 2,
    article_9: 4,
    unclassified: 0,
  },
  carbon_trend: [
    { period: "2024-Q2", total_carbon_avoided_tco2e: 48200, total_carbon_footprint_tco2e: 4100 },
    { period: "2024-Q3", total_carbon_avoided_tco2e: 71500, total_carbon_footprint_tco2e: 4800 },
    { period: "2024-Q4", total_carbon_avoided_tco2e: 82300, total_carbon_footprint_tco2e: 4900 },
    { period: "2025-Q1", total_carbon_avoided_tco2e: 89400, total_carbon_footprint_tco2e: 4600 },
    { period: "2025-Q2", total_carbon_avoided_tco2e: 95600, total_carbon_footprint_tco2e: 4800 },
    { period: "2025-Q3", total_carbon_avoided_tco2e: 98700, total_carbon_footprint_tco2e: 4700 },
    { period: "2025-Q4", total_carbon_avoided_tco2e: 104200, total_carbon_footprint_tco2e: 4900 },
    { period: "2026-Q1", total_carbon_avoided_tco2e: 112000, total_carbon_footprint_tco2e: 5100 },
  ],
  top_sdgs: [
    { sdg_id: 7, name: "Affordable and Clean Energy", project_count: 7 },
    { sdg_id: 13, name: "Climate Action", project_count: 6 },
    { sdg_id: 11, name: "Sustainable Cities", project_count: 4 },
    { sdg_id: 9, name: "Industry, Innovation and Infrastructure", project_count: 3 },
    { sdg_id: 15, name: "Life on Land", project_count: 2 },
  ],
  project_rows: [
    { id: "esg-h1", project_id: "Helios Solar Portfolio Iberia", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 2100, carbon_avoided_tco2e: 89000, renewable_energy_mwh: 187000, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 312, jobs_supported: 480, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 0, board_independence_pct: null, audit_completed: true, esg_reporting_standard: "GRI", taxonomy_eligible: true, taxonomy_aligned: true, taxonomy_activity: "Solar power generation", sfdr_article: 9, sdg_contributions: { 7: { contribution_level: "high" }, 13: { contribution_level: "high" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
    { id: "esg-h2", project_id: "Nordvik Wind Farm II", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 1800, carbon_avoided_tco2e: 54000, renewable_energy_mwh: 124000, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 148, jobs_supported: 220, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 0, board_independence_pct: null, audit_completed: true, esg_reporting_standard: "SFDR", taxonomy_eligible: true, taxonomy_aligned: true, taxonomy_activity: "Wind power generation", sfdr_article: 9, sdg_contributions: { 7: { contribution_level: "high" }, 13: { contribution_level: "medium" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
    { id: "esg-h3", project_id: "Adriatic Infrastructure Holdings", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 4200, carbon_avoided_tco2e: 12000, renewable_energy_mwh: 28000, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 421, jobs_supported: 680, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 1, board_independence_pct: null, audit_completed: true, esg_reporting_standard: "GRI", taxonomy_eligible: true, taxonomy_aligned: false, taxonomy_activity: "Infrastructure", sfdr_article: 8, sdg_contributions: { 9: { contribution_level: "high" }, 11: { contribution_level: "medium" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
    { id: "esg-h4", project_id: "Baltic BESS Grid Storage", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 980, carbon_avoided_tco2e: 8000, renewable_energy_mwh: 18400, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 84, jobs_supported: 120, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 0, board_independence_pct: null, audit_completed: false, esg_reporting_standard: null, taxonomy_eligible: true, taxonomy_aligned: true, taxonomy_activity: "Battery storage", sfdr_article: 9, sdg_contributions: { 7: { contribution_level: "medium" }, 13: { contribution_level: "medium" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
    { id: "esg-h5", project_id: "Alpine Hydro Partners", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 1400, carbon_avoided_tco2e: 98000, renewable_energy_mwh: 182000, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 268, jobs_supported: 410, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 0, board_independence_pct: null, audit_completed: true, esg_reporting_standard: "GRI", taxonomy_eligible: true, taxonomy_aligned: true, taxonomy_activity: "Hydropower generation", sfdr_article: 9, sdg_contributions: { 7: { contribution_level: "high" }, 13: { contribution_level: "high" }, 15: { contribution_level: "medium" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
    { id: "esg-h6", project_id: "Nordic Biomass Energy", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 3600, carbon_avoided_tco2e: 18000, renewable_energy_mwh: 41000, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 312, jobs_supported: 480, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 0, board_independence_pct: null, audit_completed: true, esg_reporting_standard: "SFDR", taxonomy_eligible: true, taxonomy_aligned: false, taxonomy_activity: "Biomass energy", sfdr_article: 8, sdg_contributions: { 7: { contribution_level: "medium" }, 15: { contribution_level: "high" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
    { id: "esg-h7", project_id: "Thames Clean Energy Hub", org_id: "org1", period: "2025-Q4", carbon_footprint_tco2e: 2320, carbon_avoided_tco2e: 8000, renewable_energy_mwh: 32000, water_usage_cubic_m: null, waste_diverted_tonnes: null, biodiversity_score: null, jobs_created: 302, jobs_supported: 460, local_procurement_pct: null, community_investment_eur: null, gender_diversity_pct: null, health_safety_incidents: 0, board_independence_pct: null, audit_completed: false, esg_reporting_standard: null, taxonomy_eligible: false, taxonomy_aligned: false, taxonomy_activity: null, sfdr_article: 6, sdg_contributions: { 7: { contribution_level: "medium" }, 11: { contribution_level: "high" } }, esg_narrative: null, created_at: "2026-01-10T00:00:00Z", updated_at: "2026-03-01T00:00:00Z" },
  ],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

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
      <option value="">All portfolios</option>
      {data?.items.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}

function SFDRPill({ article }: { article: number | null }) {
  if (!article) return <Badge variant="neutral">Unclassified</Badge>;
  const map: Record<number, string> = { 6: "Art. 6", 8: "Art. 8", 9: "Art. 9" };
  const colorMap: Record<number, "neutral" | "info" | "success"> = {
    6: "neutral",
    8: "info",
    9: "success",
  };
  return (
    <Badge variant={colorMap[article] ?? "neutral"}>
      {map[article] ?? `Art. ${article}`}
    </Badge>
  );
}

function SDGBadges({
  contributions,
}: {
  contributions: ESGMetricsResponse["sdg_contributions"];
}) {
  if (!contributions) return null;
  const sdgs = Object.entries(contributions)
    .filter(([, v]) => v.contribution_level !== "none")
    .slice(0, 5);
  if (!sdgs.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {sdgs.map(([sdgId]) => {
        const num = parseInt(sdgId);
        const color = SDG_COLORS[num] ?? "#6b7280";
        return (
          <span
            key={sdgId}
            className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold text-white"
            style={{ backgroundColor: color }}
            title={SDG_NAMES[num]}
          >
            SDG {sdgId}
          </span>
        );
      })}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ESGDashboardPage() {
  const [portfolioId, setPortfolioId] = useState("");
  const [period, setPeriod] = useState("");

  const { data: apiData, isLoading } = useESGPortfolioSummary(
    portfolioId || undefined,
    period || undefined
  );

  const data = apiData ?? MOCK_ESG_DATA;

  const sfdr = data?.sfdr_distribution;
  const totals = data?.totals;

  const sfdrChartData = sfdr
    ? [
        { label: "Art. 6", value: sfdr.article_6, color: SFDR_COLORS.article_6 },
        { label: "Art. 8", value: sfdr.article_8, color: SFDR_COLORS.article_8 },
        { label: "Art. 9", value: sfdr.article_9, color: SFDR_COLORS.article_9 },
        { label: "Unclassified", value: sfdr.unclassified, color: SFDR_COLORS.unclassified },
      ].filter((d) => d.value > 0)
    : [];

  const carbonTrendData = (data?.carbon_trend ?? []).map((p) => ({
    period: p.period,
    "Carbon Avoided": p.total_carbon_avoided_tco2e,
    "Carbon Footprint": p.total_carbon_footprint_tco2e,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Leaf className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              ESG Impact Dashboard
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Environmental, social and governance metrics across your portfolio
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="text-sm border border-neutral-200 rounded px-3 py-1.5 bg-white"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="">All periods</option>
            <option value="2024-Q4">2024 Q4</option>
            <option value="2024-Q3">2024 Q3</option>
            <option value="2024-Q2">2024 Q2</option>
            <option value="2024-Q1">2024 Q1</option>
            <option value="2023-Q4">2023 Q4</option>
          </select>
          <PortfolioSelector value={portfolioId} onChange={setPortfolioId} />
          <a
            href={buildExportUrl(period || undefined)}
            className="flex items-center gap-1.5 text-sm border border-neutral-200 rounded px-3 py-1.5 bg-white hover:bg-neutral-50 transition-colors"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </a>
        </div>
      </div>

      <InfoBanner>
        The <strong>ESG Dashboard</strong> tracks your portfolio&apos;s environmental, social, and governance impact across every project. Monitor carbon reduction metrics, taxonomy alignment, SDG mapping, and generate AI-powered ESG narrative sections ready for LP reporting.
      </InfoBanner>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-primary-100 rounded-lg flex-shrink-0">
                  <Leaf className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Carbon Avoided</p>
                  <p className="text-xl font-bold text-green-700">
                    {formatNumber(totals?.total_carbon_avoided_tco2e, "tCO₂e")}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-yellow-100 rounded-lg flex-shrink-0">
                  <Zap className="h-5 w-5 text-yellow-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Renewable Energy</p>
                  <p className="text-xl font-bold text-yellow-700">
                    {formatNumber(totals?.total_renewable_energy_mwh, "MWh")}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg flex-shrink-0">
                  <Users className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Jobs Created</p>
                  <p className="text-xl font-bold text-blue-700">
                    {formatNumber(totals?.total_jobs_created)}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center gap-3">
                <div className="p-2 bg-emerald-100 rounded-lg flex-shrink-0">
                  <TrendingUp className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">EU Taxonomy Aligned</p>
                  <p className="text-xl font-bold text-emerald-700">
                    {totals?.taxonomy_aligned_count ?? 0}
                    <span className="text-sm font-normal text-neutral-400 ml-1">
                      / {totals?.total_projects ?? 0} projects
                    </span>
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Carbon trend */}
            {carbonTrendData.length > 0 && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="text-sm">Carbon Trend (tCO₂e)</CardTitle>
                </CardHeader>
                <CardContent>
                  <LineChart
                    data={carbonTrendData}
                    xKey="period"
                    yKeys={["Carbon Avoided", "Carbon Footprint"]}
                    height={200}
                  />
                </CardContent>
              </Card>
            )}

            {/* SFDR distribution */}
            {sfdrChartData.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">SFDR Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {sfdrChartData.map((d) => {
                      const total = sfdrChartData.reduce((s, x) => s + x.value, 0);
                      const pct = total > 0 ? Math.round((d.value / total) * 100) : 0;
                      return (
                        <div key={d.label}>
                          <div className="flex justify-between text-xs text-neutral-600 mb-1">
                            <span>{d.label}</span>
                            <span className="font-semibold">
                              {d.value} ({pct}%)
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
                            <div
                              className="h-2 rounded-full"
                              style={{
                                width: `${pct}%`,
                                backgroundColor: d.color,
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Top SDGs */}
          {data.top_sdgs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Top SDG Contributions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-3">
                  {data.top_sdgs.map((sdg) => {
                    const color = SDG_COLORS[sdg.sdg_id] ?? "#6b7280";
                    return (
                      <div
                        key={sdg.sdg_id}
                        className="flex items-center gap-2 rounded-lg border p-3 min-w-[140px]"
                      >
                        <div
                          className="h-8 w-8 rounded flex-shrink-0 flex items-center justify-center text-xs font-bold text-white"
                          style={{ backgroundColor: color }}
                        >
                          {sdg.sdg_id}
                        </div>
                        <div>
                          <p className="text-xs font-medium text-neutral-800">
                            {sdg.name || SDG_NAMES[sdg.sdg_id]}
                          </p>
                          <p className="text-xs text-neutral-400">
                            {sdg.project_count} project
                            {sdg.project_count !== 1 ? "s" : ""}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Project rows table */}
          {data.project_rows.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Project ESG Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-neutral-50">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Project
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Carbon Avoided
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Renewable MWh
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Jobs
                        </th>
                        <th className="px-4 py-3 text-center text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          SFDR
                        </th>
                        <th className="px-4 py-3 text-center text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          Taxonomy
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                          SDGs
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.project_rows.map((row) => (
                        <tr key={row.id} className="hover:bg-neutral-50">
                          <td className="px-4 py-3">
                            <p className="font-medium text-neutral-900 text-xs">
                              {row.project_id}
                            </p>
                            <p className="text-xs text-neutral-400">{row.period}</p>
                          </td>
                          <td className="px-4 py-3 text-right text-xs text-neutral-700">
                            {formatNumber(row.carbon_avoided_tco2e, "t")}
                          </td>
                          <td className="px-4 py-3 text-right text-xs text-neutral-700">
                            {formatNumber(row.renewable_energy_mwh)}
                          </td>
                          <td className="px-4 py-3 text-right text-xs text-neutral-700">
                            {formatNumber(row.jobs_created)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <SFDRPill article={row.sfdr_article} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            {row.taxonomy_aligned ? (
                              <Badge variant="success">Aligned</Badge>
                            ) : row.taxonomy_eligible ? (
                              <Badge variant="neutral">Eligible</Badge>
                            ) : (
                              <Badge variant="neutral">—</Badge>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <SDGBadges contributions={row.sdg_contributions} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
