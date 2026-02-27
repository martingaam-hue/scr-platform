/**
 * Portfolio types and React Query hooks.
 *
 * Types mirror the FastAPI Pydantic schemas. Hooks wrap axios calls
 * with React Query for caching, optimistic updates, and pagination.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Enums ──────────────────────────────────────────────────────────────────

export type PortfolioStrategy =
  | "growth"
  | "balanced"
  | "income"
  | "opportunistic"
  | "impact_first"
  | "blended_finance";

export type FundType =
  | "open_end"
  | "closed_end"
  | "evergreen"
  | "spv"
  | "fund_of_funds"
  | "co_investment";

export type PortfolioStatus =
  | "fundraising"
  | "investing"
  | "fully_invested"
  | "harvesting"
  | "liquidating"
  | "closed";

export type AssetType =
  | "equity"
  | "debt"
  | "mezzanine"
  | "convertible"
  | "project_finance"
  | "infrastructure"
  | "real_asset"
  | "fund";

export type HoldingStatus =
  | "active"
  | "exited"
  | "written_off"
  | "on_hold";

export type SFDRClassification =
  | "article_6"
  | "article_8"
  | "article_9"
  | "not_applicable";

// ── Types ──────────────────────────────────────────────────────────────────

export interface PortfolioResponse {
  id: string;
  name: string;
  description: string;
  strategy: PortfolioStrategy;
  fund_type: FundType;
  vintage_year: number | null;
  target_aum: string;
  current_aum: string;
  currency: string;
  sfdr_classification: SFDRClassification;
  status: PortfolioStatus;
  created_at: string;
  updated_at: string;
}

export interface PortfolioMetricsResponse {
  irr_gross: string | null;
  irr_net: string | null;
  moic: string | null;
  tvpi: string | null;
  dpi: string | null;
  rvpi: string | null;
  total_invested: string;
  total_distributions: string;
  total_value: string;
  carbon_reduction_tons: string | null;
  as_of_date: string;
}

export interface PortfolioDetailResponse extends PortfolioResponse {
  latest_metrics: PortfolioMetricsResponse | null;
  holding_count: number;
}

export interface PortfolioListResponse {
  items: PortfolioResponse[];
  total: number;
}

export interface HoldingResponse {
  id: string;
  portfolio_id: string;
  project_id: string | null;
  asset_name: string;
  asset_type: AssetType;
  investment_date: string;
  investment_amount: string;
  current_value: string;
  ownership_pct: string | null;
  currency: string;
  status: HoldingStatus;
  exit_date: string | null;
  exit_amount: string | null;
  notes: string;
  moic: string | null;
  created_at: string;
  updated_at: string;
}

export interface HoldingTotals {
  total_invested: string;
  total_current_value: string;
  weighted_moic: string | null;
}

export interface HoldingListResponse {
  items: HoldingResponse[];
  total: number;
  totals: HoldingTotals;
}

export interface CashFlowEntry {
  date: string;
  amount: string;
  type: "contribution" | "distribution";
  holding_name: string | null;
}

export interface CashFlowResponse {
  items: CashFlowEntry[];
}

export interface AllocationBreakdown {
  name: string;
  value: string;
  percentage: string;
}

export interface AllocationResponse {
  by_sector: AllocationBreakdown[];
  by_geography: AllocationBreakdown[];
  by_stage: AllocationBreakdown[];
  by_asset_type: AllocationBreakdown[];
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const portfolioKeys = {
  all: ["portfolio"] as const,
  list: () => [...portfolioKeys.all, "list"] as const,
  detail: (id: string) => [...portfolioKeys.all, "detail", id] as const,
  metrics: (id: string) => [...portfolioKeys.all, "metrics", id] as const,
  holdings: (id: string, params?: { status?: HoldingStatus }) =>
    [...portfolioKeys.all, "holdings", id, params] as const,
  cashFlows: (id: string) =>
    [...portfolioKeys.all, "cash-flows", id] as const,
  allocation: (id: string) =>
    [...portfolioKeys.all, "allocation", id] as const,
};

// ── Portfolio hooks ────────────────────────────────────────────────────────

export function usePortfolios() {
  return useQuery({
    queryKey: portfolioKeys.list(),
    queryFn: () =>
      api
        .get<PortfolioListResponse>("/portfolio")
        .then((r) => r.data),
  });
}

export function usePortfolio(id: string | undefined) {
  return useQuery({
    queryKey: portfolioKeys.detail(id ?? ""),
    queryFn: () =>
      api
        .get<PortfolioDetailResponse>(`/portfolio/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      description?: string;
      strategy: PortfolioStrategy;
      fund_type: FundType;
      vintage_year?: number;
      target_aum: string;
      current_aum?: string;
      currency?: string;
      sfdr_classification?: SFDRClassification;
    }) =>
      api
        .post<PortfolioResponse>("/portfolio", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: portfolioKeys.all });
    },
  });
}

export function useUpdatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      portfolioId,
      ...body
    }: {
      portfolioId: string;
      name?: string;
      description?: string;
      strategy?: PortfolioStrategy;
      fund_type?: FundType;
      vintage_year?: number;
      target_aum?: string;
      current_aum?: string;
      currency?: string;
      sfdr_classification?: SFDRClassification;
      status?: PortfolioStatus;
    }) =>
      api
        .put<PortfolioResponse>(`/portfolio/${portfolioId}`, body)
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: portfolioKeys.detail(vars.portfolioId),
      });
      qc.invalidateQueries({ queryKey: portfolioKeys.list() });
    },
  });
}

// ── Metrics hooks ──────────────────────────────────────────────────────────

export function usePortfolioMetrics(id: string | undefined) {
  return useQuery({
    queryKey: portfolioKeys.metrics(id ?? ""),
    queryFn: () =>
      api
        .get<PortfolioMetricsResponse>(`/portfolio/${id}/metrics`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

// ── Holdings hooks ─────────────────────────────────────────────────────────

export function useHoldings(
  portfolioId: string | undefined,
  params?: { status?: HoldingStatus }
) {
  return useQuery({
    queryKey: portfolioKeys.holdings(portfolioId ?? "", params),
    queryFn: () =>
      api
        .get<HoldingListResponse>(`/portfolio/${portfolioId}/holdings`, {
          params,
        })
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

export function useAddHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      portfolioId,
      ...body
    }: {
      portfolioId: string;
      asset_name: string;
      asset_type: AssetType;
      investment_date: string;
      investment_amount: string;
      current_value: string;
      ownership_pct?: string;
      currency?: string;
      project_id?: string;
      notes?: string;
    }) =>
      api
        .post<HoldingResponse>(
          `/portfolio/${portfolioId}/holdings`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: [...portfolioKeys.all, "holdings", vars.portfolioId],
      });
      qc.invalidateQueries({
        queryKey: portfolioKeys.detail(vars.portfolioId),
      });
      qc.invalidateQueries({
        queryKey: portfolioKeys.metrics(vars.portfolioId),
      });
    },
  });
}

export function useUpdateHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      portfolioId,
      holdingId,
      ...body
    }: {
      portfolioId: string;
      holdingId: string;
      asset_name?: string;
      asset_type?: AssetType;
      investment_date?: string;
      investment_amount?: string;
      current_value?: string;
      ownership_pct?: string;
      currency?: string;
      status?: HoldingStatus;
      exit_date?: string;
      exit_amount?: string;
      notes?: string;
    }) =>
      api
        .put<HoldingResponse>(
          `/portfolio/${portfolioId}/holdings/${holdingId}`,
          body
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: [...portfolioKeys.all, "holdings", vars.portfolioId],
      });
      qc.invalidateQueries({
        queryKey: portfolioKeys.metrics(vars.portfolioId),
      });
    },
  });
}

// ── Cash flow hooks ────────────────────────────────────────────────────────

export function useCashFlows(portfolioId: string | undefined) {
  return useQuery({
    queryKey: portfolioKeys.cashFlows(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<CashFlowResponse>(`/portfolio/${portfolioId}/cash-flows`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

// ── Allocation hooks ───────────────────────────────────────────────────────

export function useAllocation(portfolioId: string | undefined) {
  return useQuery({
    queryKey: portfolioKeys.allocation(portfolioId ?? ""),
    queryFn: () =>
      api
        .get<AllocationResponse>(`/portfolio/${portfolioId}/allocation`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function formatCurrency(
  amount: string | number,
  currency = "USD"
): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatPercent(value: string | number, decimals = 1): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return `${(num * 100).toFixed(decimals)}%`;
}

export function formatMultiple(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return `${num.toFixed(2)}x`;
}

const STRATEGY_LABELS: Record<PortfolioStrategy, string> = {
  growth: "Growth",
  balanced: "Balanced",
  income: "Income",
  opportunistic: "Opportunistic",
  impact_first: "Impact First",
  blended_finance: "Blended Finance",
};

export function strategyLabel(strategy: PortfolioStrategy): string {
  return STRATEGY_LABELS[strategy] ?? strategy;
}

const FUND_TYPE_LABELS: Record<FundType, string> = {
  open_end: "Open-End",
  closed_end: "Closed-End",
  evergreen: "Evergreen",
  spv: "SPV",
  fund_of_funds: "Fund of Funds",
  co_investment: "Co-Investment",
};

export function fundTypeLabel(fundType: FundType): string {
  return FUND_TYPE_LABELS[fundType] ?? fundType;
}

const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  equity: "Equity",
  debt: "Debt",
  mezzanine: "Mezzanine",
  convertible: "Convertible",
  project_finance: "Project Finance",
  infrastructure: "Infrastructure",
  real_asset: "Real Asset",
  fund: "Fund",
};

export function assetTypeLabel(assetType: AssetType): string {
  return ASSET_TYPE_LABELS[assetType] ?? assetType;
}

const SFDR_LABELS: Record<SFDRClassification, string> = {
  article_6: "Article 6",
  article_8: "Article 8",
  article_9: "Article 9",
  not_applicable: "N/A",
};

export function sfdrLabel(classification: SFDRClassification): string {
  return SFDR_LABELS[classification] ?? classification;
}

export function holdingStatusColor(
  status: HoldingStatus
): "neutral" | "success" | "warning" | "error" {
  switch (status) {
    case "active":
      return "success";
    case "exited":
      return "neutral";
    case "written_off":
      return "error";
    case "on_hold":
      return "warning";
  }
}

export function portfolioStatusColor(
  status: PortfolioStatus
): "neutral" | "success" | "warning" | "error" | "info" {
  switch (status) {
    case "fundraising":
      return "info";
    case "investing":
    case "fully_invested":
      return "success";
    case "harvesting":
      return "warning";
    case "liquidating":
      return "error";
    case "closed":
      return "neutral";
  }
}
