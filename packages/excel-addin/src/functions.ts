/**
 * SCR Platform Excel Custom Functions.
 *
 * Each function is registered under the "SCR" namespace so the formula
 * bar shows  =SCR.SIGNAL_SCORE(...)  etc.
 *
 * Build this file with webpack (see package.json) and host the output at
 * the URL declared in manifest.xml under CustomFunctions.Script.Url.
 */

import { fetchExcelEndpoint } from "./api-client";

/* global CustomFunctions */

// ── Signal Score ──────────────────────────────────────────────────────────────

/**
 * Gets the Signal Score for a project.
 * @customfunction SCR_SIGNAL_SCORE
 * @param projectId The project UUID
 * @param [dimension] Optional dimension: financial_planning, project_viability,
 *   team_strength, risk_assessment, esg, market_opportunity
 * @returns Signal Score (0–100)
 */
async function scrSignalScore(
  projectId: string,
  dimension?: string
): Promise<number> {
  const path = dimension
    ? `/excel/signal-score/${projectId}?dimension=${encodeURIComponent(dimension)}`
    : `/excel/signal-score/${projectId}`;
  const data = await fetchExcelEndpoint(path);
  if (data.value === null) {
    throw new CustomFunctions.Error(
      CustomFunctions.ErrorCode.notAvailable,
      data.error || "Score not available"
    );
  }
  return data.value as number;
}

// ── Valuation ─────────────────────────────────────────────────────────────────

/**
 * Gets a valuation metric for a project.
 * @customfunction SCR_VALUATION
 * @param projectId The project UUID
 * @param metric Metric: enterprise_value, equity_value, irr, moic, npv, ev_per_mw
 * @returns Metric value
 */
async function scrValuation(projectId: string, metric: string): Promise<number> {
  const data = await fetchExcelEndpoint(
    `/excel/valuation/${projectId}/${encodeURIComponent(metric)}`
  );
  if (data.value === null) {
    throw new CustomFunctions.Error(
      CustomFunctions.ErrorCode.notAvailable,
      data.error || "Valuation not available"
    );
  }
  return data.value as number;
}

// ── Benchmark ─────────────────────────────────────────────────────────────────

/**
 * Gets benchmark data for an asset class.
 * @customfunction SCR_BENCHMARK
 * @param assetClass Asset class: solar, wind, real_estate, infrastructure
 * @param metric Metric name: irr, moic, ev_per_mw
 * @param [geography] Country / region filter
 * @param [percentile] Percentile: p10, p25, p50, p75, p90 (default: p50)
 * @returns Benchmark value
 */
async function scrBenchmark(
  assetClass: string,
  metric: string,
  geography?: string,
  percentile?: string
): Promise<number> {
  let path = `/excel/benchmark/${encodeURIComponent(assetClass)}/${encodeURIComponent(metric)}`;
  const params = new URLSearchParams();
  if (geography) params.set("geography", geography);
  if (percentile) params.set("percentile", percentile);
  if (params.toString()) path += `?${params.toString()}`;

  const data = await fetchExcelEndpoint(path);
  if (data.value === null) {
    throw new CustomFunctions.Error(
      CustomFunctions.ErrorCode.notAvailable,
      data.error || "Benchmark not available"
    );
  }
  return data.value as number;
}

// ── FX Rate ───────────────────────────────────────────────────────────────────

/**
 * Gets the current FX rate.
 * @customfunction SCR_FX
 * @param base Base currency (e.g. EUR)
 * @param quote Quote currency (e.g. USD)
 * @returns Exchange rate
 */
async function scrFx(base: string, quote: string): Promise<number> {
  const data = await fetchExcelEndpoint(
    `/excel/fx/${encodeURIComponent(base)}/${encodeURIComponent(quote)}`
  );
  if (data.value === null) {
    throw new CustomFunctions.Error(
      CustomFunctions.ErrorCode.notAvailable,
      "FX rate not available"
    );
  }
  return data.value as number;
}

// ── Project KPI ───────────────────────────────────────────────────────────────

/**
 * Gets a project KPI value.
 * @customfunction SCR_KPI
 * @param projectId The project UUID
 * @param kpiName KPI name: revenue, ebitda, dscr, ltv, occupancy, capacity_factor
 * @param [period] Period filter: "2026-Q1", "2026-01"
 * @returns KPI value
 */
async function scrKpi(
  projectId: string,
  kpiName: string,
  period?: string
): Promise<number> {
  let path = `/excel/project-kpi/${projectId}/${encodeURIComponent(kpiName)}`;
  if (period) path += `?period=${encodeURIComponent(period)}`;

  const data = await fetchExcelEndpoint(path);
  if (data.value === null) {
    throw new CustomFunctions.Error(
      CustomFunctions.ErrorCode.notAvailable,
      "KPI not available"
    );
  }
  return data.value as number;
}

// ── Portfolio ─────────────────────────────────────────────────────────────────

/**
 * Gets a portfolio metric.
 * @customfunction SCR_PORTFOLIO
 * @param portfolioId The portfolio UUID
 * @param metric Metric: nav, irr, moic, tvpi, dpi
 * @returns Metric value
 */
async function scrPortfolio(portfolioId: string, metric: string): Promise<number> {
  const data = await fetchExcelEndpoint(
    `/excel/portfolio/${portfolioId}/${encodeURIComponent(metric)}`
  );
  if (data.value === null) {
    throw new CustomFunctions.Error(
      CustomFunctions.ErrorCode.notAvailable,
      "Portfolio metric not available"
    );
  }
  return data.value as number;
}

// ── Registration ──────────────────────────────────────────────────────────────

CustomFunctions.associate("SCR_SIGNAL_SCORE", scrSignalScore);
CustomFunctions.associate("SCR_VALUATION", scrValuation);
CustomFunctions.associate("SCR_BENCHMARK", scrBenchmark);
CustomFunctions.associate("SCR_FX", scrFx);
CustomFunctions.associate("SCR_KPI", scrKpi);
CustomFunctions.associate("SCR_PORTFOLIO", scrPortfolio);
